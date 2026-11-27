"""Verify evaluation orchestration offline using deterministic adapter fixtures."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class EvalTest(unittest.TestCase):
    def test_eval_budget_and_independent_grading_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / 'evals/example'
            (case / 'graders').mkdir(parents=True)
            (case / 'prompt.md').write_text('---\nruns: 2\n---\nIs it ready?')
            (case / 'graders/criteria.md').write_text('Must say cannot tell.')
            runner = root / 'runner.py'
            runner.write_text("import json,sys\nr=json.load(sys.stdin)\nassert 'criteria' not in r\nassert r['fresh_session']\nprint(json.dumps({'answer':'Cannot tell', 'cost_usd':.01}))\n")
            grader = root / 'grader.py'
            grader.write_text("import json,sys\nr=json.load(sys.stdin)\nassert r['criteria'] and r['fresh_session']\nprint(json.dumps({'passed':r['answer']=='Cannot tell', 'cost_usd':.01}))\n")
            command = [sys.executable, str(ROOT / 'scripts/ct-evals.py'), '--evals', str(root / 'evals'), '--runner', f'{sys.executable} {runner}', '--grader', f'{sys.executable} {grader}', '--out', str(root / 'result.json'), '--max-call-usd', '.01']
            result = subprocess.run(command + ['--budget-usd', '.04'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((root / 'result.json').read_text())
            self.assertEqual(len(data['results']), 2)
            self.assertTrue(data['complete'])
            result = subprocess.run(command + ['--budget-usd', '.01'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads((root / 'result.json').read_text())['reported_cost_usd'], 0)

    def test_benchmark_refuses_unmatched_or_single_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'scores.csv'
            columns = ['project', 'commit', 'harness', 'model', 'condition', 'truth_total', 'found', 'minutes', 'tokens']
            rows = [['app', 'a', 'h', 'm', 'baseline', 10, 8, 2, 20], ['app', 'b', 'h', 'm', 'skills', 10, 10, 3, 30]]
            with path.open('w') as stream:
                writer = csv.writer(stream)
                writer.writerow(columns)
                writer.writerows(rows)
            out = subprocess.run([sys.executable, str(ROOT / 'scripts/ct-benchmark.py'), str(path)], capture_output=True, text=True, check=True)
            self.assertTrue(all(not c['comparison_ready'] for c in json.loads(out.stdout)))


if __name__ == '__main__':
    unittest.main()
