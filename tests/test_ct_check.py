"""Tests for scripts/ct-check.py: the registry validator, coverage and verdict."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

import yaml
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "scripts", "ct-check.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from ct_core import CATEGORIES, identity, digest, flow_digest, atomic_json

BASE = {
    "version": 1,
    "product": {"purpose": "test product", "intent_sources": ["README.md"]},
    "run": {"boot": "start", "base_url": "http://localhost:1"},
    "personas": [{"id": "P1", "name": "Member"}],
    "areas": [{"id": "A1", "name": "Main", "status": "tested"}],
    "surfaces": [{"id": "S1", "type": "page", "name": "Home", "location": "/home", "source": "both",
                  "personas": ["P1"], "reach": "sidebar", "cases": ".clickthrough/cases/S1.yaml"}],
    "goals": [{"id": "G1", "title": "Use home", "personas": ["P1"], "cases": ".clickthrough/cases/G1.yaml"}],
    "flows": [{"id": "F1", "goal": "G1", "persona": "P1", "priority": "P0", "variant": "normal",
               "route": "sidebar", "surfaces": ["S1"], "start": "login",
               "steps": [{"do": "open home", "see": "home"}], "test_file": "t/F1.test.js",
               "status": "pass", "last_run": {"commit": "none", "run_id": "r1", "evidence": [".clickthrough/runs/r1/evidence/F1.txt"]}}],
}


class CheckTest(unittest.TestCase):
    def run_check(self, registry, stage="evaluate", inventory=None, files=("README.md", "t/F1.test.js"), bugs=None, mutate=None, extra_args=()):
        registry = copy.deepcopy(registry)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".clickthrough").mkdir()
            for rel in files:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture content\n")
            for entity in registry.get("surfaces", []) + registry.get("goals", []):
                card = entity.get("cases", "")
                if card.startswith(".clickthrough/cases/"):
                    matching = next((f["id"] for f in registry.get("flows", []) if entity["id"] in f.get("surfaces", []) or entity["id"] == f.get("goal")), "F1")
                    path = root / card
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(yaml.safe_dump({"id": entity["id"], "cases": [{"id": entity["id"] + "-C1", "flow": matching, "expectation": "home visible"}]}))
            if bugs is None:
                bugs = []
                for f in registry.get("flows", []):
                    if f.get("status") in ("fail", "likely_broken"):
                        f.setdefault("bug", "B-" + f["id"])
                        proof = ".clickthrough/proof/" + f["id"] + ".txt"
                        (root / proof).parent.mkdir(parents=True, exist_ok=True)
                        (root / proof).write_text("Observed failure\n")
                        bugs.append({"id": f["bug"], "title": "broken", "severity": "medium", "status": "open", "how_known": "ran" if f["status"] == "fail" else "traced", "where": "app.py:1", "confidence": "high", "proof": [proof], "flows": [f["id"]]})
            (root / ".clickthrough/bugs.yaml").write_text(yaml.safe_dump({"version": 1, "bugs": bugs}))
            (root / ".clickthrough/coverage.yaml").write_text(yaml.safe_dump({"version": 1, "checks": [{"id": c, "category": c, "status": "not_applicable", "reason": "not exercised by this validator fixture"} for c in CATEGORIES]}))
            source = identity(root)
            registry.setdefault("inventory_review", {**source, "reviewer": "fixture reviewer", "notes": "All fixture entry points reconciled"})
            if inventory is not False:
                atomic_json(root / ".clickthrough/inventory.json", {**source, "items": inventory or []})
            atomic_json(root / ".clickthrough/runs/r1/run.json", {**source, "run_id": "r1"})
            for f in registry.get("flows", []):
                if f.get("status") not in ("pass", "fail"):
                    continue
                output = ".clickthrough/runs/r1/evidence/" + f["id"] + ".txt"
                (root / output).parent.mkdir(parents=True, exist_ok=True)
                (root / output).write_text("Observed home page\n")
                last = f.setdefault("last_run", {})
                last.setdefault("result", ".clickthrough/runs/r1/evidence/" + f["id"] + ".json")
                evidence = [p for p in last.get("evidence", []) if (root / p).is_file()]
                atomic_json(root / last["result"], {"version": 1, **source, "flow_id": f["id"], "flow_sha256": flow_digest(f), "status": f["status"], "run_id": "r1", "test_file": f.get("test_file"), "test_sha256": digest(root / f["test_file"]) if f.get("test_file") and (root / f["test_file"]).is_file() else "", "environment": {"target": "local"}, "recorded_at": "2026-01-01T00:00:00Z", "command": ["test"], "exit_code": 0 if f["status"] == "pass" else 1, "assertions": [{"expected": "home visible", "observed": "home", "passed": f["status"] == "pass", "case_ids": [e["id"] + "-C1" for e in registry.get("surfaces", []) + registry.get("goals", []) if e["id"] in f.get("surfaces", []) or e["id"] == f.get("goal")]}], "artifacts": [{"path": p, "sha256": digest(root / p)} for p in evidence]})
            (root / ".clickthrough/flows.yaml").write_text(yaml.safe_dump(registry))
            if mutate:
                mutate(root)
            out = subprocess.run([sys.executable, CHECK, "--stage", stage, *extra_args], cwd=tmp, capture_output=True, text=True)
            return out.returncode, out.stdout + (out.stderr if out.stderr else "")

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
        self.assertIn("CANNOT TELL", self.verdict(out))
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
        bug["proof"] = [".clickthrough/proof/B001/F1.webm"]
        code, out = self.run_check(reg, bugs=[bug], files=("README.md", "t/F1.test.js", ".clickthrough/proof/B001/F1.webm"))
        self.assertEqual(code, 0, out)
        bug["proof"] = [".clickthrough/proof/B001/F1.png"]
        code, out = self.run_check(reg, bugs=[bug], files=("README.md", "t/F1.test.js", ".clickthrough/proof/B001/F1.png"))
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

    def test_blocked_is_not_executed_or_ready(self):
        reg = copy.deepcopy(BASE)
        f = copy.deepcopy(reg['flows'][0])
        f.update(id='F2', priority='P1', status='blocked', failure_class='TOOL_GAP', finding='no inbox')
        reg['flows'].append(f)
        code, out = self.run_check(reg)
        self.assertIn('tested 1 of 2', out)
        self.assertIn('CANNOT TELL', self.verdict(out))

    def test_critical_p1_failure_blocks_release(self):
        reg = copy.deepcopy(BASE)
        f = copy.deepcopy(reg['flows'][0])
        f.update(id='F2', priority='P1', status='fail', failure_class='FLOW_BROKEN', finding='tenant leak', bug='B1')
        reg['flows'].append(f)
        bug = {'id': 'B1', 'title': 'tenant leak', 'severity': 'critical', 'status': 'open', 'how_known': 'ran', 'flows': ['F2'], 'proof': ['README.md']}
        code, out = self.run_check(reg, bugs=[bug], extra_args=['--require-ready'])
        self.assertEqual(code, 2, out)
        self.assertEqual(self.verdict(out), 'NOT READY')

    def test_missing_inventory_and_blanket_coverage_fail(self):
        self.assertEqual(self.run_check(BASE, inventory=False)[0], 1)
        reg = copy.deepcopy(BASE)
        reg['surfaces'][0]['covers'] = ['*']
        code, out = self.run_check(reg)
        self.assertEqual(code, 1)
        self.assertIn('blanket covers', out)

    def test_missing_and_empty_cards_fail(self):
        for content in (None, ''):
            def change(root):
                path = root / '.clickthrough/cases/S1.yaml'
                path.unlink() if content is None else path.write_text(content)
            code, out = self.run_check(BASE, mutate=change)
            self.assertEqual(code, 1, out)
            self.assertIn('CANNOT TELL', self.verdict(out))

    def test_stale_or_tampered_evidence_fails(self):
        mutations = [lambda r: (r / 'README.md').write_text('changed product'),
                     lambda r: (r / '.clickthrough/runs/r1/evidence/F1.txt').write_text('altered evidence'),
                     lambda r: (r / '.clickthrough/runs/r1/evidence/F1.txt').write_text(''),
                     lambda r: (r / '.clickthrough/runs/r1/run.json').unlink(),
                     lambda r: (r / 't/F1.test.js').write_text('changed test')]
        for mutation in mutations:
            code, out = self.run_check(BASE, mutate=mutation)
            self.assertEqual(code, 1, out)
            self.assertNotEqual(self.verdict(out), 'READY')

    def test_test_stage_requires_tests(self):
        reg = copy.deepcopy(BASE)
        reg['flows'][0].update(status='untested', test_file=None)
        self.assertEqual(self.run_check(reg, stage='test')[0], 1)

    def test_json_and_schema_errors(self):
        code, out = self.run_check(BASE, extra_args=['--json', '--require-ready'])
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)['coverage']['executed'], 1)
        code, out = self.run_check(BASE, mutate=lambda r: (r / '.clickthrough/flows.yaml').write_text('- wrong shape'), extra_args=['--json'])
        self.assertEqual(code, 1)
        self.assertIn('registry must', json.loads(out)['errors'][0])

    def test_coverage_cannot_claim_pass_without_execution(self):
        def change(root):
            path = root / '.clickthrough/coverage.yaml'
            data = yaml.safe_load(path.read_text())
            data['checks'][0].update(status='pass', flows=[], expected='keyboard works')
            path.write_text(yaml.safe_dump(data))
        code, out = self.run_check(BASE, mutate=change)
        self.assertEqual(code, 1, out)
        self.assertIn('executed coverage needs flows', out)

    def test_changed_flow_expectations_invalidate_receipt(self):
        def change(root):
            path = root / '.clickthrough/flows.yaml'
            data = yaml.safe_load(path.read_text())
            data['flows'][0]['steps'][0]['see'] = 'a different expected outcome'
            path.write_text(yaml.safe_dump(data))
        code, out = self.run_check(BASE, mutate=change)
        self.assertEqual(code, 1)
        self.assertIn('flow expectations changed', out)

    def test_case_id_must_have_an_observation(self):
        def change(root):
            path = root / '.clickthrough/cases/S1.yaml'
            data = yaml.safe_load(path.read_text())
            data['cases'][0]['id'] = 'S1-never-run'
            path.write_text(yaml.safe_dump(data))
        code, out = self.run_check(BASE, mutate=change)
        self.assertEqual(code, 1)
        self.assertIn('no passing observation', out)

    def test_double_does_not_establish_provider_readiness(self):
        def change(root):
            path = root / '.clickthrough/coverage.yaml'
            data = yaml.safe_load(path.read_text())
            data['checks'][-1].update(category='external_services', status='pass', flows=['F1'], expected='email delivered', verification='double')
            path.write_text(yaml.safe_dump(data))
        code, out = self.run_check(BASE, mutate=change)
        self.assertEqual(code, 1)
        self.assertIn('double is contract evidence only', out)


if __name__ == "__main__":
    unittest.main()
