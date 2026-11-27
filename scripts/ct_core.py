"""Shared local artifact, identity and privacy helpers. No network calls."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

MODES = ('review', 'auto', 'recheck', 'update', 'discover', 'continue', 'fix')
CATEGORIES = ('accessibility', 'devices', 'recovery', 'concurrency', 'background',
              'upgrades', 'performance', 'external_services')
IGNORED = {'.clickthrough-backups', '.ct-install.lock', '.git', '.clickthrough', '.userflow', 'clickthrough-tests', 'userflow-tests',
           '.agents', '.claude', 'node_modules', '__pycache__', '.venv', 'venv',
           'dist', 'build', '.next', 'coverage'}
ARTIFACT_TYPES = {'.png', '.jpg', '.jpeg', '.webm', '.mp4', '.mov', '.zip',
                  '.txt', '.log', '.json', '.jsonl', '.har', '.cast'}
SECRET_KEY = re.compile(r'password|passwd|secret|token|authorization|cookie|api[-_]?key', re.I)
SECRET_TEXT = re.compile(r'(?i)(Bearer\s+)[\w.\-/+=]+|\b(?:sk-[\w-]{16,}|gh[pousr]_[\w]{20,}|AKIA[A-Z0-9]{16})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.ct-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def local_file(root, relative, nonempty=True):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('expected a project-relative file path')
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
        raise ValueError(f'file missing or outside project: {relative}')
    if nonempty and not path.stat().st_size:
        raise ValueError(f'empty file: {relative}')
    return path


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def identity(root):
    """Hash product files separately from audit artifacts; never expose contents."""
    root = Path(root).resolve()
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    result = git('ls-files', '-z', '--cached', '--others', '--exclude-standard')
    if result.returncode == 0:
        names = set(os.fsdecode(result.stdout).split('\0')) - {''}
    else:
        names = set()
        for directory, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in IGNORED]
            names.update(str((Path(directory) / f).relative_to(root)) for f in files)
    h = hashlib.sha256()
    for name in sorted(names):
        if set(Path(name).parts) & IGNORED:
            continue
        path = root / name
        value = ('symlink:' + os.readlink(path)) if path.is_symlink() else (digest(path) if path.is_file() else 'deleted')
        h.update(name.encode() + b'\0' + value.encode() + b'\0')
    head = git('rev-parse', 'HEAD')
    return {'commit': head.stdout.decode().strip() if head.returncode == 0 else 'none',
            'product_sha256': h.hexdigest()}


def redact(value, extra_keys=(), patterns=()):
    if isinstance(value, dict):
        return {k: '<redacted>' if SECRET_KEY.search(str(k)) or str(k).lower() in extra_keys
                else redact(v, extra_keys, patterns) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, extra_keys, patterns) for v in value]
    if isinstance(value, str):
        value = SECRET_TEXT.sub('<redacted>', value)
        value = re.sub(r'''(?i)((?:["']?)(?:password|passwd|secret|token|api[_-]?key)(?:["']?)\s*:\s*)(?:"[^"]*"|'[^']*'|[^,\s}]+)''', r'\1"<redacted>"', value)
        value = re.sub(r'(?i)((?:password|secret|token|api[_-]?key)=)[^&\s"<>]+', r'\1<redacted>', value)
        for pattern in patterns:
            value = re.sub(pattern, '<redacted>', value)
    return value


def flow_digest(flow):
    fields = ('id', 'goal', 'route', 'persona', 'surfaces', 'start', 'preconditions',
              'steps', 'persisted', 'side_effects', 'target', 'read_only', 'test_file')
    return hashlib.sha256(json.dumps({k: flow.get(k) for k in fields}, sort_keys=True).encode()).hexdigest()


def evidence_errors(root, flow, current):
    """Verify an execution receipt. Detects drift, not dishonest assertions."""
    errors = []
    fid = flow.get('id')
    last = flow.get('last_run') or {}
    try:
        receipt = json.loads(local_file(root, last.get('result')).read_text())
        if not isinstance(receipt, dict) or receipt.get('version') != 1:
            raise ValueError('result must be a version 1 execution receipt')
        for key, expected in (('flow_id', fid), ('status', flow['status']),
                              ('test_file', flow.get('test_file')), ('run_id', last.get('run_id')),
                              ('commit', last.get('commit'))):
            if not expected or receipt.get(key) != expected:
                errors.append(f'{fid}: result {key} does not match registry')
        if receipt.get('flow_sha256') != flow_digest(flow):
            errors.append(f'{fid}: flow expectations changed since execution')
        if any(receipt.get(k) != v for k, v in current.items()):
            errors.append(f'{fid}: stale result; product revision changed')
        run = json.loads(local_file(root, f".clickthrough/runs/{receipt.get('run_id')}/run.json").read_text())
        if any(receipt.get(k) != run.get(k) for k in ('run_id', 'commit', 'product_sha256')):
            errors.append(f'{fid}: result does not belong to recorded run')
        if not isinstance(receipt.get('environment'), dict) or not receipt['environment'].get('target'):
            errors.append(f'{fid}: result needs environment.target')
        if not receipt.get('command') or not receipt.get('recorded_at'):
            errors.append(f'{fid}: result needs command and recorded_at')
        if receipt.get('test_sha256') != digest(local_file(root, flow.get('test_file'))):
            errors.append(f'{fid}: test changed since execution')
        assertions = receipt.get('assertions')
        if not isinstance(assertions, list) or not assertions:
            raise ValueError('result needs observed assertions')
        for assertion in assertions:
            if not isinstance(assertion, dict) or not assertion.get('expected') or 'observed' not in assertion or type(assertion.get('passed')) is not bool:
                raise ValueError('assertion needs expected, observed and boolean passed')
        for assertion in assertions:
            for field in ('case_ids', 'check_ids'):
                if field in assertion and (not isinstance(assertion[field], list) or any(not isinstance(x, str) for x in assertion[field])):
                    raise ValueError(f'{field} must be a list of strings')
        if flow['status'] == 'pass' and (receipt.get('exit_code') != 0 or not all(a['passed'] for a in assertions)):
            errors.append(f'{fid}: passing result contains failed assertions or command')
        if flow['status'] == 'fail' and all(a['passed'] for a in assertions):
            errors.append(f'{fid}: failed result needs a failed assertion')
        artifacts = receipt.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError('result needs hashed artifacts')
        paths = set()
        for artifact in artifacts:
            path = local_file(root, artifact['path'])
            paths.add(artifact['path'])
            if path.suffix.lower() not in ARTIFACT_TYPES or digest(path) != artifact.get('sha256'):
                errors.append(f"{fid}: artifact type or hash invalid: {artifact['path']}")
        if not set(last.get('evidence') or []).issubset(paths):
            errors.append(f'{fid}: evidence is not bound to result')
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append(f'{fid}: invalid execution result: {exc}')
    return errors
