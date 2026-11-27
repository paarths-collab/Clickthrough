# Measuring Clickthrough

The saved scorecard contains exploratory runs, not evidence of a recall gain.
The hard demo's baseline and treatment both found 25/25 planted issues. They used
different commit IDs, and the notes record prompt/triggering limitations.

Use `experiment/protocol.md` with fresh sessions, hidden answer keys, the same
product commit, harness and model, and at least two runs per condition. Keep the
product revision separate from commits that only install the pack. Record
`audit_index` (1 for initial audit, 2+ for repeat audits), pack revision, budget,
confirmed findings, false alarms, wrong readiness, time, tokens and human help.
Do not combine initial and repeat-audit costs. Test supported harness activation
separately from explicitly loading the skill. Include a real project and API/CLI
products before generalizing from the bundled web demos.

```bash
python3 scripts/ct-benchmark.py experiment/scorecard.csv
```

The summarizer groups exact product commit/harness/model/audit-index cohorts and
reports medians. It labels cohorts with insufficient repeats instead of claiming a
comparison. Track time to reproduce, repeat-run regression recall and cost per
confirmed issue alongside first-run recall/precision.

## Behavioral eval adapters

`ct-evals.py` runs every prompt in `evals/`, respecting its repetition count,
through a runner and a **separate grader session**. Both adapters are executable
commands that read one JSON object from stdin and write JSON to stdout.

Runner input: `prompt`, `settings` (including allowed tools and turn limit),
`fresh_session`, `max_cost_usd`, `timeout_seconds`.
Runner output: `answer`, `harness`, `model`, `tokens`, `cost_usd`.
The adapter must install/load this pack and enforce the requested session/tool,
turn and spending limits. Never expose the grader criteria to the runner.

Grader input: `prompt`, `answer`, `criteria`, `fresh_session`, `max_cost_usd`,
`timeout_seconds`. Output: boolean `passed`, `reasons`, `cost_usd`.

```bash
python3 scripts/ct-evals.py --runner 'python my_runner.py' \
  --grader 'python my_grader.py' --budget-usd 2 --max-call-usd 0.05 \
  --out evals/results/run.json
```

Each runner/grader pair reserves two capped calls before dispatch. Adapter errors,
unknown cost or over-cap reports stop further calls. Provider-side cost limits
must be enforced by the adapters; this CLI cannot stop a provider billing after
an adapter is terminated. No provider or paid model is selected automatically.

The optional weekly/manual GitHub workflow runs only when repository variables
`CT_EVAL_RUNNER`, `CT_EVAL_GRADER`, `CT_EVAL_BUDGET_USD` and
`CT_EVAL_MAX_CALL_USD` are configured. The executable adapters must be present on
the runner. `CT_EVAL_API_KEY` is passed from Actions secrets if required. Results
are retained for seven days. Without adapters the workflow is skipped, not
reported as a behavioral pass. PR CI always runs deterministic regression and
lifecycle tests without model access.
