#!/usr/bin/env python3
"""Create a collision-free, private run with product identity."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import uuid
from ct_core import MODES, atomic_json, identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.')
    parser.add_argument('--harness', default='unknown')
    parser.add_argument('--model', default='unknown')
    parser.add_argument('--mode', choices=MODES, default='review')
    parser.add_argument('--condition', choices=('skills', 'baseline'), default='skills')
    parser.add_argument('--independent', choices=('yes', 'no', 'true', 'false'))
    args = parser.parse_args()
    root = Path(args.project).resolve()
    if not root.is_dir():
        parser.error('project folder does not exist')
    now = datetime.now(timezone.utc)
    source = identity(root)
    run_id = now.strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:12]
    directory = root / '.clickthrough/runs' / run_id
    directory.mkdir(parents=True, mode=0o700)
    for name in ('raw', 'evidence'):
        (directory / name).mkdir(mode=0o700)
    atomic_json(directory / 'run.json', {'version': 1, 'run_id': run_id, **source,
        'harness': args.harness, 'model': args.model, 'mode': args.mode,
        'condition': args.condition, 'evaluator_independent': None if args.independent is None else args.independent in ('yes', 'true'),
        'started_at': now.isoformat(), 'ended_at': None, 'tokens': None, 'notes': ''})
    (directory / 'decisions.md').write_text('# Decision log\n', encoding='utf-8')
    temporary = directory.parent / ('.current-' + uuid.uuid4().hex)
    temporary.write_text(run_id + '\n')
    temporary.replace(directory.parent / 'CURRENT')
    print(directory)


if __name__ == '__main__':
    main()
