#!/usr/bin/env python3
"""Local Clickthrough runner: doctor, status, resume, recheck, run and export.

Commands execute only when explicitly supplied to `run -- ...`.
"""
import argparse
import fcntl
import signal
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import yaml
from ct_core import atomic_json, digest, identity, flow_digest, local_file, redact, SECRET_TEXT, ARTIFACT_TYPES

HERE = Path(__file__).resolve().parent


def read_registry(root):
    data = yaml.safe_load((root / '.clickthrough/flows.yaml').read_text())
    if not isinstance(data, dict) or not isinstance(data.get('flows'), list):
        raise ValueError('flows.yaml must be an object containing flows')
    return data


def check(root):
    result = subprocess.run([sys.executable, str(HERE / 'ct-check.py'), '--file',
                             str(root / '.clickthrough/flows.yaml'), '--json'], capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or 'checker returned no result')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.')
    subs = parser.add_subparsers(dest='action', required=True)
    subs.add_parser('doctor')
    for name in ('status', 'resume', 'recheck'):
        sub = subs.add_parser(name)
        sub.add_argument('--compare', help='previous summary JSON for status changes')
        sub.add_argument('--save', help='project-relative private summary path under .clickthrough/runs/')
    run = subs.add_parser('run')
    run.add_argument('--flow', required=True)
    run.add_argument('--run-id', required=True)
    run.add_argument('--target', required=True, choices=('local', 'staging', 'production'))
    run.add_argument('--environment', required=True, help='non-secret environment/version description')
    run.add_argument('--timeout', type=float, default=300)
    run.add_argument('--artifact', action='append', default=[], help='additional project-relative evidence file')
    run.add_argument('--update', action='store_true', help='update the flow; failures still require triage and a bug')
    run.add_argument('command', nargs=argparse.REMAINDER)
    export = subs.add_parser('export')
    export.add_argument('source', help='project-relative JSON/text artifact; binary exports are refused')
    export.add_argument('--out', required=True, help='project-relative destination; never overwrites input')
    export.add_argument('--redact-key', action='append', default=[])
    export.add_argument('--redact-pattern', action='append', default=[])
    args = parser.parse_args()
    root = Path(args.project).resolve()
    if args.action == 'doctor':
        needed = ['.clickthrough/flows.yaml', '.clickthrough/coverage.yaml', '.clickthrough/inventory.json']
        missing = [p for p in needed if not (root / p).is_file()]
        print(json.dumps({'python': sys.version.split()[0], 'pyyaml': yaml.__version__,
                          'missing': missing, 'next_action': 'Install, generate inventory and fill coverage' if missing else 'Run status'}, indent=2))
        return 1 if missing else 0
    if args.action in ('status', 'resume', 'recheck'):
        summary = check(root)
        registry = read_registry(root)
        summary['next_flows'] = [f['id'] for f in registry['flows'] if args.action == 'recheck' or f.get('status') != 'pass']
        if args.action == 'resume' and summary.get('errors'):
            summary['next_action'] = 'Resolve validation/stale evidence errors before trusting prior passes'
        else:
            summary['next_action'] = 'Execute next_flows, then require-ready' if summary['next_flows'] else 'Review verdict and unresolved checks'
        if args.compare:
            previous = json.loads(local_file(root, args.compare).read_text())
            before = {f['id']: f['status'] for f in previous.get('flows', [])}
            summary['changes'] = [{'id': f['id'], 'before': before.get(f['id'], 'not_catalogued'), 'after': f['status']}
                                  for f in summary.get('flows', []) if before.get(f['id']) != f['status']]
            summary['removed_flows'] = sorted(set(before) - {f['id'] for f in summary.get('flows', [])})
        if args.save:
            path = safe_output(root, args.save)
            if not path.is_relative_to(root / '.clickthrough/runs'):
                raise ValueError('save summaries under .clickthrough/runs/')
            atomic_json(path, summary)
        print(json.dumps(summary, indent=2))
        return 0
    if args.action == 'export':
        source = local_file(root, args.source)
        if source.suffix.lower() not in ('.json', '.jsonl', '.txt', '.log', '.md'):
            raise ValueError('binary evidence stays private; manually review a sanitized derivative')
        destination = safe_output(root, args.out)
        if source == destination or destination.exists():
            raise ValueError('export destination must be a new file')
        original = source.read_text(encoding='utf-8')
        keys = tuple(k.lower() for k in args.redact_key)
        if source.suffix == '.json':
            output = json.dumps(redact(json.loads(original), keys, args.redact_pattern), indent=2)
        elif source.suffix == '.jsonl':
            output = '\n'.join(json.dumps(redact(json.loads(line), keys, args.redact_pattern)) for line in original.splitlines() if line.strip())
        else:
            output = redact(original, keys, args.redact_pattern)
        if SECRET_TEXT.search(output):
            raise ValueError('secret signature remains after redaction')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as stream:
            stream.write(output + '\n')
        print(json.dumps({'export': args.out, 'sha256': digest(destination),
                          'review_required': 'Inspect for personal data and unrecognized secrets before sharing. Binary originals remain private.'}))
        return 0
    registry = read_registry(root)
    registry_hash = digest(root / '.clickthrough/flows.yaml')
    flow = next((f for f in registry['flows'] if f.get('id') == args.flow), None)
    if flow is None or not args.command:
        raise ValueError('supply a registered flow and command after --')
    command = args.command[1:] if args.command[0] == '--' else args.command
    if not command or args.timeout <= 0:
        raise ValueError('command and positive timeout required')
    # A local hostname is not proof of local data: the target contract must be reviewed first.
    target = next((t for t in registry.get('targets', []) if t.get('name') == args.target), None)
    if not target or not target.get('confirmed_by') or not target.get('data'):
        raise ValueError('target needs confirmed_by and data rules in flows.yaml')
    if args.target == 'production' and (target['data'] != 'read-only' or flow.get('read_only') is not True):
        raise ValueError('production requires a read-only target and explicitly read_only flow')
    if flow.get('variant') in ('abuse', 'not_allowed') and args.target != 'local':
        raise ValueError('security/attack checks run locally only')
    source = identity(root)
    metadata = json.loads(local_file(root, f'.clickthrough/runs/{args.run_id}/run.json').read_text())
    if metadata.get('run_id') != args.run_id or any(metadata.get(k) != v for k, v in source.items()):
        raise ValueError('run identity is stale; start a new run after product changes')
    test = local_file(root, flow.get('test_file'))
    test_hash = digest(test)
    attempt = root / '.clickthrough/runs' / args.run_id / 'evidence' / uuid.uuid4().hex
    attempt.mkdir(mode=0o700)
    assertion_path = attempt / 'assertions.json'
    env = {**os.environ, 'CT_ASSERTIONS_FILE': str(assertion_path), 'CT_EVIDENCE_DIR': str(attempt), 'CT_RECORD': '1'}
    output = attempt / 'output.txt'
    with output.open('w') as stream:
        stream.write('Command: ' + json.dumps(command) + '\n')
        stream.flush()
        try:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise
        except subprocess.TimeoutExpired:
            code = 124
            stream.write('\nClickthrough: command exceeded timeout; process group stopped.\n')
    if identity(root) != source or digest(test) != test_hash:
        raise ValueError('product or test changed during execution; evidence retained, result not accepted')
    if not assertion_path.exists():
        raise ValueError('test must write observed assertions to CT_ASSERTIONS_FILE; output retained but no pass recorded')
    assertions = json.loads(assertion_path.read_text())
    if not isinstance(assertions, list) or not assertions or any(not isinstance(a, dict) or not a.get('expected') or 'observed' not in a or type(a.get('passed')) is not bool for a in assertions):
        raise ValueError('assertions require expected, observed, and boolean passed')
    status = 'pass' if code == 0 and all(a['passed'] for a in assertions) else 'fail'
    if status == 'fail' and all(a['passed'] for a in assertions):
        assertions.append({'expected': 'test command completes successfully', 'observed': f'exit {code}', 'passed': False})
    paths = {str(output.relative_to(root)), *args.artifact}
    paths.update(str(p.relative_to(root)) for p in attempt.rglob('*') if p.is_file() and p.suffix.lower() in ARTIFACT_TYPES)
    artifacts = [{'path': p, 'sha256': digest(local_file(root, p))} for p in sorted(paths)]
    receipt = {'version': 1, 'flow_id': args.flow, 'run_id': args.run_id, **source,
               'flow_sha256': flow_digest(flow), 'test_file': flow['test_file'], 'test_sha256': test_hash, 'command': command,
               'exit_code': code, 'status': status, 'recorded_at': datetime.now(timezone.utc).isoformat(),
               'environment': {'target': args.target, 'description': args.environment, 'stubs': registry.get('run', {}).get('stubs', [])},
               'assertions': assertions, 'artifacts': artifacts}
    receipt_path = attempt / 'result.json'
    atomic_json(receipt_path, receipt)
    update = {'status': status, 'last_run': {'commit': source['commit'], 'run_id': args.run_id,
              'result': str(receipt_path.relative_to(root)), 'evidence': [a['path'] for a in artifacts], 'target': args.target}}
    if args.update:
        flow.update(update)
        if status == 'fail':
            flow['finding'] = 'Execution failed; inspect the receipt, classify product versus test defect, and register the cause.'
        with (root / '.clickthrough/runs/.registry.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if digest(root / '.clickthrough/flows.yaml') != registry_hash:
                raise ValueError('registry changed during execution; receipt retained, merge its result explicitly')
            tmp = root / '.clickthrough' / ('.flows-' + uuid.uuid4().hex)
            tmp.write_text(yaml.safe_dump(registry, sort_keys=False))
            tmp.replace(root / '.clickthrough/flows.yaml')
    print(json.dumps(update, indent=2))
    return code if code else (0 if status == 'pass' else 1)


def safe_output(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError('output must be project-relative and inside the project')
    return path


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        sys.exit('Clickthrough: ' + str(exc))
