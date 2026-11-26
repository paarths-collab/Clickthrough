"""Tests for scripts/ct-inventory.py: the code map."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "ct-inventory.py")
spec = importlib.util.spec_from_file_location("ct_inventory", SCRIPT)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def run(path):
    out = subprocess.run([sys.executable, SCRIPT, path, "--json"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["items"]


class TestPaths(unittest.TestCase):
    def test_test_detection(self):
        cases = {
            "src/app/(main)/engineering/tests/page.tsx": False,
            "src/app/api/v1/tests/route.ts": False,
            "tests/lib.test.js": True,
            "tests/helpers.js": True,
            "src/foo/__tests__/x.ts": True,
            "src/foo/bar.spec.tsx": True,
            "pkg/server/handler_test.go": True,
            "app/tests/test_views.py": True,
            "src/main/java/FooTest.java": True,
            "src/ui/x.fixtures.ts": True,
            "e2e/login.spec.ts": True,
            "src/features/x/x.service.ts": False,
            "src/pages/settings/index.tsx": False,
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(inventory.is_test_path(path), expected)


class TestSampleApps(unittest.TestCase):
    def test_hard_sample_app(self):
        items = run(os.path.join(ROOT, "sample-app-hard"))
        kinds = lambda k: [i["what"] for i in items if i["kind"] == k]
        self.assertEqual(len(kinds("route")), 29)
        self.assertEqual(sorted(kinds("mcp_tool")),
                         sorted(["list_tickets", "get_ticket", "create_ticket", "add_reply", "set_status", "assign_ticket"]))
        self.assertEqual(len(kinds("page")), 16)
        self.assertGreater(len(kinds("email")), 5)


class TestFrameworks(unittest.TestCase):
    FILES = {
        "src/app/(group)/projects/page.tsx": "export default function P() {}\n",
        "src/app/(main)/engineering/tests/page.tsx": "export default function T() {}\n",
        "src/app/api/v1/items/route.ts": "export async function GET() {}\nexport async function POST() {}\n",
        "server/express.js": "app.get('/health', h)\nrouter.post('/api/orders', h)\n",
        "py/app.py": "@app.route('/login', methods=['POST'])\ndef login(): pass\n@router.get('/items')\ndef items(): pass\n",
        "go/main.go": 'http.HandleFunc("/ping", ping)\n',
        "cli/cli.py": "sub.add_parser('export')\n",
        "jobs/worker.ts": "cron.schedule('0 * * * *', run)\n",
        "mail/send.ts": "await resend.emails.send({to})\n",
        "src/app/x/x.test.ts": "app.get('/should-not-count', h)\n",
    }

    def test_detects_common_frameworks(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in self.FILES.items():
                path = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as handle:
                    handle.write(text)
            items = run(tmp)
            what = {(i["kind"], i["what"]) for i in items}
            for expected in [("page", "/projects"), ("page", "/engineering/tests"),
                             ("route", "GET /api/v1/items"), ("route", "POST /api/v1/items"),
                             ("route", "GET /health"), ("route", "POST /api/orders"),
                             ("route", "POST /login"), ("route", "GET /items"), ("route", "ANY /ping"),
                             ("cli", "export")]:
                with self.subTest(expected=expected):
                    self.assertIn(expected, what)
            self.assertTrue(any(i["kind"] == "job" for i in items))
            self.assertTrue(any(i["kind"] == "email" for i in items))
            self.assertNotIn(("route", "GET /should-not-count"), what)


if __name__ == "__main__":
    unittest.main()
