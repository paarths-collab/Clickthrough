#!/usr/bin/env python3
"""Summarize repeated, comparable baseline/treatment cohorts without mixing revisions."""
import argparse
import csv
from collections import defaultdict
import json
from statistics import median


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scorecard')
    args = parser.parse_args()
    groups = defaultdict(lambda: defaultdict(list))
    with open(args.scorecard, newline='') as stream:
        for row in csv.DictReader(stream):
            key = tuple(row.get(k, '') for k in ('project', 'commit', 'harness', 'model', 'audit_index'))
            groups[key][row['condition']].append(row)
    output = []
    for key, conditions in groups.items():
        summary = {'cohort': dict(zip(('project', 'commit', 'harness', 'model', 'audit_index'), key)), 'conditions': {}}
        for name, rows in conditions.items():
            metrics = defaultdict(list)
            for row in rows:
                for metric in ('minutes', 'tokens', 'false_alarms', 'found_with_evidence', 'human_help'):
                    if row.get(metric):
                        metrics[metric].append(float(row[metric]))
                if float(row.get('truth_total') or 0):
                    metrics['recall'].append(float(row['found']) / float(row['truth_total']))
                real = float(row.get('found') or 0) + float(row.get('extra_real') or 0)
                total = real + float(row.get('false_alarms') or 0)
                if total:
                    metrics['precision'].append(real / total)
                metrics['wrong_ready'].append(int(row.get('wrong_ready') == 'yes'))
            summary['conditions'][name] = {'runs': len(rows), 'median': {k: median(v) for k, v in metrics.items()}}
        summary['comparison_ready'] = all(len(conditions[c]) >= 2 for c in ('baseline', 'skills'))
        if not summary['comparison_ready']:
            summary['limitation'] = 'Need at least two runs per condition on the same product commit, harness, model and audit index.'
        output.append(summary)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
