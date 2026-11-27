"""Exercise installation, execution, continuation, recheck and private export."""
import concurrent.futures
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from ct_core import CATEGORIES, identity


class LifecycleTest(unittest.TestCase):
    def call(self, root, *args):
        return subprocess.run(list(args), cwd=root, text=True, capture_output=True)

    def install(self, root, mode='both'):
        return self.call(root, 'bash', str(ROOT / 'install.sh'), mode, str(root))

    def test_all_install_modes_preserve_user_content(self):
        for mode in ('claude', 'codex', 'cursor', 'both', 'plugin'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in ('CLAUDE.md', 'AGENTS.md'):
                    (root / name).write_text('Before\n<!-- clickthrough:start -->\nold\n<!-- clickthrough:end -->\nAfter\n')
                (root / '.claude').mkdir()
                (root / '.claude/settings.json').write_text('{"existing": true}')
                for _ in range(2):
                    result = self.install(root, mode)
                    self.assertEqual(result.returncode, 0, result.stderr)
                for name in ('CLAUDE.md', 'AGENTS.md'):
                    self.assertTrue((root / name).read_text().startswith('Before\n'))
                    self.assertTrue((root / name).read_text().endswith('After\n'))
                self.assertTrue(json.loads((root / '.claude/settings.json').read_text())['existing'])
                for script in ('ct.py', 'ct_core.py', 'ct-new-run.py'):
                    self.assertTrue((root / '.clickthrough/bin' / script).is_file())
                self.assertIn('.clickthrough/proof/', (root / '.gitignore').read_text())
                self.assertTrue(list((root / '.clickthrough-backups').glob('*/manifest.json')))

    def test_malformed_markers_leave_project_unchanged(self):
        for content in ('prefix\n<!-- clickthrough:start -->\nprivate instructions\n',
                        '<!-- clickthrough:end -->\n<!-- clickthrough:start -->\n',
                        '<!-- clickthrough:start -->\n<!-- user-flow-qa:end -->\n'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'CLAUDE.md').write_text(content)
                out = self.install(root)
                self.assertNotEqual(out.returncode, 0)
                self.assertEqual((root / 'CLAUDE.md').read_text(), content)
                self.assertFalse((root / '.agents').exists())

    def test_failed_install_restores_migrated_audit_and_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            pack, root = base / 'pack', base / 'project'
            (pack / 'scripts').mkdir(parents=True)
            (pack / 'templates').mkdir()
            (pack / 'skills/ct-run').mkdir(parents=True)
            root.mkdir()
            shutil.copy2(ROOT / 'install.sh', pack / 'install.sh')
            shutil.copy2(ROOT / 'scripts/ct-install.py', pack / 'scripts/ct-install.py')
            shutil.copy2(ROOT / 'templates/rules-snippet.md', pack / 'templates/rules-snippet.md')
            (pack / 'skills/ct-run/SKILL.md').write_text('new skill')
            (root / '.userflow/bin').mkdir(parents=True)
            (root / '.userflow/bin/old-tool').write_text('keep old tool')
            (root / 'CLAUDE.md').write_text('keep user instructions')
            # Missing guide forces a failure after rules, skills and migration changed.
            out = self.call(root, 'bash', str(pack / 'install.sh'), 'both', str(root))
            self.assertNotEqual(out.returncode, 0)
            self.assertEqual((root / 'CLAUDE.md').read_text(), 'keep user instructions')
            self.assertEqual((root / '.userflow/bin/old-tool').read_text(), 'keep old tool')
            self.assertFalse((root / '.agents/skills/ct-run').exists())

    def test_parallel_starts_and_mode_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def start(mode):
                out = self.call(root, 'bash', str(ROOT / 'scripts/new-run.sh'), '--project', tmp, '--mode', mode, '--model', 'model"quoted')
                self.assertEqual(out.returncode, 0, out.stderr)
                return Path(out.stdout.strip())
            with concurrent.futures.ThreadPoolExecutor() as pool:
                paths = list(pool.map(start, ['discover', 'continue', 'fix', 'recheck', 'auto']))
            self.assertEqual(len(set(paths)), 5)
            for p in paths:
                self.assertEqual(json.loads((p / 'run.json').read_text())['model'], 'model"quoted')

    def test_full_local_lifecycle_and_stale_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(self.install(root).returncode, 0)
            ct = root / '.clickthrough'
            tests = root / 'clickthrough-tests'
            test = tests / 'F1.py'
            test.write_text("import json, os\nfrom pathlib import Path\nvalue=Path('value.txt').read_text()\nPath(os.environ['CT_ASSERTIONS_FILE']).write_text(json.dumps([{'expected':'saved value is correct','observed':value,'passed':value=='correct','case_ids':['S1-C1','G1-C1']}]))\n")
            (root / 'value.txt').write_text('correct')
            registry = {'version': 2, 'product': {'purpose': 'Read a saved value', 'intent_sources': ['value.txt']},
                'run': {'boot': 'none', 'base_url': 'local-files'}, 'personas': [{'id': 'P1'}],
                'targets': [{'name': 'local', 'data': 'writable-test', 'confirmed_by': 'fixture'}],
                'surfaces': [{'id': 'S1', 'type': 'cli', 'source': 'both', 'location': 'read-value', 'cases': '.clickthrough/cases/S1.yaml'}],
                'goals': [{'id': 'G1', 'cases': '.clickthrough/cases/G1.yaml'}],
                'flows': [{'id': 'F1', 'goal': 'G1', 'persona': 'P1', 'priority': 'P0', 'variant': 'normal', 'status': 'untested', 'start': 'shell', 'surfaces': ['S1'], 'steps': [{'do': 'read saved value', 'see': 'correct'}], 'test_file': 'clickthrough-tests/F1.py'}]}
            (ct / 'cases').mkdir()
            for eid in ('S1', 'G1'):
                (ct / 'cases' / (eid + '.yaml')).write_text(yaml.safe_dump({'id': eid, 'cases': [{'id': eid + '-C1', 'flow': 'F1', 'expectation': 'saved value is correct'}]}))
            (ct / 'coverage.yaml').write_text(yaml.safe_dump({'checks': [{'id': c, 'category': c, 'status': 'not_applicable', 'reason': 'fixture only tests a local read'} for c in CATEGORIES]}))
            source = identity(root)
            registry['inventory_review'] = {**source, 'reviewer': 'fixture reviewer', 'notes': 'one CLI command, all inputs reviewed'}
            (ct / 'inventory.json').write_text(json.dumps({**source, 'items': [{'kind': 'cli', 'what': 'read-value', 'where': 'clickthrough-tests/F1.py:1'}]}))
            (ct / 'flows.yaml').write_text(yaml.safe_dump(registry))
            out = self.call(root, 'bash', str(ct / 'bin/new-run.sh'), '--project', tmp, '--mode', 'continue')
            self.assertEqual(out.returncode, 0, out.stderr)
            run_id = Path(out.stdout.strip()).name
            runner = str(ct / 'bin/ct.py')
            out = self.call(root, sys.executable, runner, 'resume')
            self.assertEqual(json.loads(out.stdout)['next_flows'], ['F1'])
            out = self.call(root, sys.executable, runner, 'run', '--flow', 'F1', '--run-id', run_id, '--target', 'local', '--environment', 'local fixture v1', '--update', '--', sys.executable, 'clickthrough-tests/F1.py')
            self.assertEqual(out.returncode, 0, out.stderr)
            out = self.call(root, sys.executable, str(ct / 'bin/ct-check.py'), '--json', '--require-ready')
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertEqual(json.loads(out.stdout)['verdict'], 'READY')
            out = self.call(root, sys.executable, runner, 'status', '--save', '.clickthrough/runs/' + run_id + '/summary.json')
            self.assertEqual(out.returncode, 0, out.stderr)
            out = self.call(root, sys.executable, runner, 'recheck')
            self.assertEqual(json.loads(out.stdout)['next_flows'], ['F1'])
            (root / 'value.txt').write_text('broken')
            out = self.call(root, sys.executable, str(ct / 'bin/ct-check.py'), '--json', '--require-ready')
            self.assertEqual(out.returncode, 1)
            self.assertTrue(any('stale' in e for e in json.loads(out.stdout)['errors']))

    def test_export_masks_nested_credentials_and_does_not_touch_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = {'password': 'fake-password', 'nested': {'api_key': 'fake-key'}, 'url': 'https://example.test/?token=fake-token', 'email': 'synthetic@example.test'}
            (root / 'input.json').write_text(json.dumps(original))
            out = self.call(root, sys.executable, str(ROOT / 'scripts/ct.py'), 'export', 'input.json', '--out', 'sanitized.json', '--redact-key', 'email')
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertNotIn('fake-', (root / 'sanitized.json').read_text())
            self.assertEqual(json.loads((root / 'input.json').read_text()), original)
            out = self.call(root, sys.executable, str(ROOT / 'scripts/ct.py'), 'export', 'input.json', '--out', '../escape.json')
            self.assertNotEqual(out.returncode, 0)


if __name__ == '__main__':
    unittest.main()
