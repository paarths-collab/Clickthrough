#!/usr/bin/env python3
"""Validate and back up managed paths before invoking the installer; roll back errors."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


def main():
    target, destination = sys.argv[1:]
    root = Path(destination).resolve()
    pack = Path(__file__).resolve().parent.parent
    if target not in ('claude', 'codex', 'cursor', 'both', 'plugin') or not root.is_dir():
        raise ValueError('usage: install.sh claude|codex|cursor|both|plugin EXISTING_PROJECT')
    paths = ['.gitignore', '.clickthrough/bin', '.clickthrough/templates', '.clickthrough/guide.md',
             '.clickthrough/flows.yaml', '.clickthrough/bugs.yaml', '.clickthrough/tool-gaps.md', '.clickthrough/coverage.yaml']
    rules = []
    for mode, directory, rule in [('claude', '.claude/skills', 'CLAUDE.md'), ('codex', '.agents/skills', 'AGENTS.md')]:
        if target == 'both' or target == mode or (target == 'cursor' and mode == 'codex'):
            rules.append(rule)
            paths.extend(str(Path(directory) / skill.name) for skill in (pack / 'skills').iterdir() if skill.is_dir())
    if target == 'plugin':
        rules.append('CLAUDE.md')
        paths.append('.claude/settings.json')
    paths.extend(rules)
    for name in paths:
        path = root / name
        if any(p.is_symlink() for p in [path, *path.parents] if p != root and p.is_relative_to(root)):
            raise ValueError(f'refusing symlink in managed path: {name}')
    for name in rules:
        path = root / name
        if not path.exists():
            continue
        markers = re.findall(r'<!-- (clickthrough|user-flow-qa):(start|end) -->', path.read_text())
        if markers and (len(markers) != 2 or markers[0][1] != 'start' or markers[1] != (markers[0][0], 'end')):
            raise ValueError(f'{name}: malformed or duplicate Clickthrough markers; no files changed')
    settings = root / '.claude/settings.json'
    if target == 'plugin' and settings.exists():
        data = json.loads(settings.read_text())
        if not isinstance(data, dict) or any(not isinstance(data.get(k, {}), dict) for k in ('extraKnownMarketplaces', 'enabledPlugins')):
            raise ValueError('plugin settings must contain JSON objects')
    migrations = []
    for old, new in [('.userflow', '.clickthrough'), ('userflow-tests', 'clickthrough-tests')]:
        if (root / old).exists() and not (root / new).exists():
            if (root / old).is_symlink():
                raise ValueError(f'refusing symlink migration: {old}')
            migrations.append((old, new))
            paths.append(old)
    lock = root / '.ct-install.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    backup = root / '.clickthrough-backups' / uuid.uuid4().hex
    existed = []
    try:
        backup.mkdir(parents=True, mode=0o700)
        for name in paths:
            src, dst = root / name, backup / name
            if src.exists():
                existed.append(name)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
        (backup / 'manifest.json').write_text(json.dumps({'paths': paths, 'existed': existed, 'migrations': migrations}, indent=2))
        result = subprocess.run(['bash', str(pack / 'install.sh'), target, str(root), '--transaction'])
        if result.returncode:
            # Undo renames first; pre-existing migrated audit data is never deleted.
            for old, new in reversed(migrations):
                if not (root / old).exists() and (root / new).exists():
                    (root / new).rename(root / old)
            for name in reversed(paths):
                dst = root / name
                if dst.is_dir():
                    shutil.rmtree(dst)
                elif dst.exists():
                    dst.unlink()
                if name in existed:
                    src = backup / name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
            raise ValueError('installation failed; managed paths restored from ' + str(backup))
        print('Backup of replaced files: ' + str(backup))
    finally:
        lock.unlink()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit('Install error: ' + str(exc))
