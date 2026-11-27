#!/usr/bin/env python3
"""Run skill behavior evals through separately configured runner and grader commands.

Each adapter reads one JSON object on stdin and returns JSON on stdout. No adapter,
model, credentials or paid service is selected automatically. See docs/evaluations.md.
"""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
import yaml
from ct_core import atomic_json


def document(path):
    text = path.read_text()
    if text.startswith('---\n'):
        _, metadata, body = text.split('---', 2)
        return yaml.safe_load(metadata) or {}, body.strip()
    return {}, text


def invoke(command, request, timeout):
    out = subprocess.run(shlex.split(command), input=json.dumps(request), text=True,
                         capture_output=True, timeout=timeout)
    if out.returncode:
        raise ValueError('adapter failed: ' + out.stderr[-1000:])
    data = json.loads(out.stdout)
    if not isinstance(data, dict):
        raise ValueError('adapter must return a JSON object')
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evals', default=str(Path(__file__).resolve().parent.parent / 'evals'))
    p.add_argument('--runner', required=True)
    p.add_argument('--grader', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--timeout', type=float, default=300)
    p.add_argument('--budget-usd', type=float, required=True)
    p.add_argument('--max-call-usd', type=float, required=True, help='adapter-enforced maximum per invocation')
    args = p.parse_args()
    if args.max_call_usd <= 0 or args.budget_usd <= 0 or args.timeout <= 0:
        p.error('budget, per-call cap and timeout must be positive')
    results, spent = [], 0.0
    success = True
    cases = sorted(Path(args.evals).glob('*/prompt.md'))
    if not cases:
        p.error('no eval prompts found')
    for prompt in cases:
        meta, body = document(prompt)
        _, criteria = document(prompt.parent / 'graders/criteria.md')
        for repetition in range(int(meta.get('runs', 1))):
            if spent + 2 * args.max_call_usd > args.budget_usd:
                results.append({'case': prompt.parent.name, 'status': 'blocked', 'reason': 'budget cannot reserve runner and grader calls'})
                success = False
                break
            start = time.monotonic()
            record = {'case': prompt.parent.name, 'repetition': repetition + 1}
            try:
                common = {'max_cost_usd': args.max_call_usd, 'timeout_seconds': args.timeout}
                answer = invoke(args.runner, {**common, 'prompt': body, 'settings': meta, 'fresh_session': True}, args.timeout)
                cost = answer.get('cost_usd')
                if not isinstance(cost, (int, float)) or not 0 <= cost <= args.max_call_usd:
                    raise ValueError('runner did not honor/report call cost cap')
                spent += cost
                if not isinstance(answer.get('answer'), str) or not answer['answer'].strip():
                    raise ValueError('runner returned no answer')
                grade = invoke(args.grader, {**common, 'prompt': body, 'answer': answer['answer'], 'criteria': criteria, 'fresh_session': True}, args.timeout)
                cost = grade.get('cost_usd')
                if not isinstance(cost, (int, float)) or not 0 <= cost <= args.max_call_usd or type(grade.get('passed')) is not bool:
                    raise ValueError('grader must return passed and capped cost_usd')
                spent += cost
                record.update(status='pass' if grade['passed'] else 'fail', answer=answer, grade=grade)
                success &= grade['passed']
            except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                record.update(status='error', reason=str(exc))
                results.append(record)
                atomic_json(args.out, {'results': results, 'reported_cost_usd': spent, 'complete': False})
                # Unknown incurred cost or a broken adapter: never launch another paid call.
                return 1
            record['seconds'] = round(time.monotonic() - start, 3)
            results.append(record)
            atomic_json(args.out, {'results': results, 'reported_cost_usd': spent, 'complete': False})
    atomic_json(args.out, {'results': results, 'reported_cost_usd': spent, 'complete': success})
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
