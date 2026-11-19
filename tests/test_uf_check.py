"""Tests for scripts/uf-check.py: the registry validator, coverage and verdict."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "scripts", "uf-check.py")

BASE = {
    "version": 1,
    "product": {"purpose": "test product", "intent_sources": ["README.md"]},
    "run": {"boot": "start", "base_url": "http://localhost:1"},
    "personas": [{"id": "P1", "name": "Member"}],
    "areas": [{"id": "A1", "name": "Main", "status": "tested"}],
    "surfaces": [{"id": "S1", "type": "page", "name": "Home", "location": "/home", "source": "both",
                  "personas": ["P1"], "reach": "sidebar", "cases": "README.md"}],
    "goals": [{"id": "G1", "title": "Use home", "personas": ["P1"], "cases": "README.md"}],
    "flows": [{"id": "F1", "goal": "G1", "persona": "P1", "priority": "P0", "variant": "normal",
               "route": "sidebar", "surfaces": ["S1"], "start": "login",
               "steps": [{"do": "open home", "see": "home"}], "test_file": "t/F1.test.js",
               "status": "pass", "last_run": {"commit": "abc", "run_id": "r1", "evidence": ["README.md"]}}],
}


class CheckTest(unittest.TestCase):
    def run_check(self, registry, stage="evaluate", inventory=None, files=("README.md", "t/F1.test.js"), bugs=None):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".userflow"))
            for rel in files:
                path = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "w").close()
            with open(os.path.join(tmp, ".userflow", "flows.yaml"), "w") as handle:
                yaml.safe_dump(registry, handle)
            if bugs is not None:
                with open(os.path.join(tmp, ".userflow", "bugs.yaml"), "w") as handle:
                    yaml.safe_dump({"version": 1, "bugs": bugs}, handle)
            if inventory is not None:
                with open(os.path.join(tmp, ".userflow", "inventory.json"), "w") as handle:
                    json.dump({"items": inventory}, handle)
            out = subprocess.run([sys.executable, CHECK, "--stage", stage], cwd=tmp,
                                 capture_output=True, text=True)
            return out.returncode, out.stdout

    def verdict(self, output):
        for line in output.splitlines():
            if line.startswith("Verdict from the registry:"):
                return line.split(":", 1)[1].strip()
        return None

    def test_complete_registry_is_ready(self):
        code, out = self.run_check(BASE)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.verdict(out), "READY")

    def test_empty_registry_has_errors(self):
        code, out = self.run_check({"version": 1, "product": {"purpose": ""}}, stage="discover")
        self.assertEqual(code, 1)
        self.assertIn("product.purpose is empty", out)

    def test_untested_flow_is_not_an_error_but_blocks_ready(self):
        reg = copy.deepcopy(BASE)
        reg["flows"].append({"id": "F2", "goal": "G1", "persona": "P1", "priority": "P1", "variant": "wrong_input",
                             "route": "sidebar", "surfaces": ["S1"], "start": "login",
                             "steps": [{"do": "x", "see": "y"}], "status": "untested"})
        code, out = self.run_check(reg)
        self.assertEqual(code, 0, out)
        self.assertNotIn("no test_file", out)
        self.assertIn("tested 1 of 2 flows", out)
        self.assertIn("CANNOT TELL", self.verdict(out))

    def test_passing_flow_without_test_file_is_an_error(self):
        reg = copy.deepcopy(BASE)
        del reg["flows"][0]["test_file"]
        code, out = self.run_check(reg)
        self.assertEqual(code, 1)
        self.assertIn("pass but no test_file", out)

    def test_pass_with_missing_evidence_is_an_error(self):
        reg = copy.deepcopy(BASE)
        reg["flows"][0]["last_run"]["evidence"] = ["missing.png"]
        code, out = self.run_check(reg)
        self.assertEqual(code, 1)
        self.assertIn("evidence not found", out)

    def test_failed_p0_is_not_ready(self):
        reg = copy.deepcopy(BASE)
        reg["flows"][0].update(status="fail", failure_class="FLOW_BROKEN", finding="broken")
        code, out = self.run_check(reg)
        self.assertEqual(self.verdict(out), "NOT READY")

    def test_likely_broken_needs_confidence(self):
        reg = copy.deepcopy(BASE)
        reg["flows"][0].update(status="likely_broken", failure_class="INTEGRATION", finding="mismatch")
        code, out = self.run_check(reg)
        self.assertIn("likely_broken needs `confidence", out)
        reg["flows"][0]["confidence"] = "medium"
        code, out = self.run_check(reg)
        self.assertIn("likely NOT READY", self.verdict(out))

    def test_pending_area_blocks_ready(self):
        reg = copy.deepcopy(BASE)
        reg["areas"].append({"id": "A2", "name": "Other", "status": "pending"})
        code, out = self.run_check(reg)
        self.assertIn("areas not covered: A2", self.verdict(out))

    def test_p0_surface_without_cases_blocks_ready(self):
        reg = copy.deepcopy(BASE)
        del reg["surfaces"][0]["cases"]
        code, out = self.run_check(reg)
        self.assertIn("not tested in depth", self.verdict(out))
        self.assertEqual(out.count("no `cases` file"), 1, "missing cases files are summarised in one warning")

    def test_p0_goal_without_workflow_card_blocks_listing(self):
        reg = copy.deepcopy(BASE)
        del reg["goals"][0]["cases"]
        code, out = self.run_check(reg, stage="flows")
        self.assertEqual(code, 1)
        self.assertIn("P0 workflow has no workflow card", out)
        reg["goals"][0]["cases"] = "missing.md"
        code, out = self.run_check(reg, stage="flows")
        self.assertIn("workflow card does not exist", out)

    def test_failing_flow_must_name_a_registered_bug(self):
        reg = copy.deepcopy(BASE)
        reg["flows"][0].update(status="fail", failure_class="FLOW_BROKEN", finding="broken")
        code, out = self.run_check(reg, bugs=[])
        self.assertIn("names no bug", out)
        reg["flows"][0]["bug"] = "B001"
        code, out = self.run_check(reg, bugs=[])
        self.assertIn("bug B001 is not in", out)
        bug = {"id": "B001", "title": "Home is broken", "severity": "high", "status": "open", "how_known": "ran",
               "proof": ["README.md"], "flows": ["F1"]}
        code, out = self.run_check(reg, bugs=[bug])
        self.assertEqual(code, 0, out)
        self.assertIn("Bugs: 1 open (high 1)", out)
        self.assertEqual(self.verdict(out), "NOT READY")

    def test_bug_found_by_running_needs_proof_recording(self):
        reg = copy.deepcopy(BASE)
        reg["flows"][0].update(status="fail", failure_class="FLOW_BROKEN", finding="broken", bug="B001")
        bug = {"id": "B001", "title": "Home is broken", "severity": "high", "status": "open",
               "how_known": "ran", "flows": ["F1"]}
        code, out = self.run_check(reg, bugs=[bug])
        self.assertIn("has no proof file", out)
        bug["proof"] = [".userflow/proof/B001/F1.webm"]
        code, out = self.run_check(reg, bugs=[bug], files=("README.md", "t/F1.test.js", ".userflow/proof/B001/F1.webm"))
        self.assertEqual(code, 0, out)
        bug["proof"] = [".userflow/proof/B001/F1.png"]
        code, out = self.run_check(reg, bugs=[bug], files=("README.md", "t/F1.test.js", ".userflow/proof/B001/F1.png"))
        self.assertIn("no recording", out)

    def test_read_or_traced_bug_needs_location_and_confidence(self):
        bug = {"id": "B002", "title": "Audit insert error swallowed", "severity": "high", "status": "open",
               "how_known": "read", "kind": "software"}
        code, out = self.run_check(BASE, bugs=[bug])
        self.assertIn("read needs `where`", out)
        self.assertIn("needs confidence", out)
        bug.update(where="src/audit.ts:94", confidence="high")
        code, out = self.run_check(BASE, bugs=[bug])
        self.assertEqual(code, 0, out)
        bug["how_known"] = "guessed"
        code, out = self.run_check(BASE, bugs=[bug])
        self.assertIn("how_known must be ran, traced or read", out)

    def test_fixed_bug_needs_proof(self):
        bug = {"id": "B001", "title": "x", "severity": "low", "status": "fixed", "how_known": "ran", "flows": ["F1"]}
        code, out = self.run_check(BASE, bugs=[bug])
        self.assertIn("fixed needs fixed_in", out)

    def test_p0_inflation_warning(self):
        reg = copy.deepcopy(BASE)
        template = reg["flows"][0]
        reg["flows"] = []
        for n in range(20):
            f = copy.deepcopy(template)
            f["id"] = f"F{n + 1}"
            f["priority"] = "P0" if n < 10 else "P1"
            reg["flows"].append(f)
        code, out = self.run_check(reg, stage="flows")
        self.assertIn("50% of flows are P0", out)

    def test_uncovered_entry_points_are_listed_and_covers_fixes_it(self):
        inventory = [{"kind": "route", "what": "GET /api/v1/items", "where": "src/api.ts:3", "test": False},
                     {"kind": "page", "what": "/home", "where": "src/app/home/page.tsx:1", "test": False}]
        code, out = self.run_check(BASE, inventory=inventory)
        self.assertEqual(code, 1)
        self.assertIn("1 entry points in the code map belong to no surface", out)
        reg = copy.deepcopy(BASE)
        reg["surfaces"][0]["covers"] = ["* /api/v1/items*"]
        code, out = self.run_check(reg, inventory=inventory)
        self.assertNotIn("belong to no surface", out)

    def test_partly_verified_goal_is_flagged(self):
        reg = copy.deepcopy(BASE)
        reg["flows"].append({"id": "F2", "goal": "G1", "persona": "P1", "priority": "P1", "variant": "alternate",
                             "route": "email link", "surfaces": ["S1"], "start": "email",
                             "steps": [{"do": "x", "see": "y"}], "test_file": None, "status": "blocked",
                             "failure_class": "TOOL_GAP", "finding": "no inbox"})
        code, out = self.run_check(reg)
        self.assertIn("only partly verified", out)
        self.assertIn("F2 email link", out)


if __name__ == "__main__":
    unittest.main()
