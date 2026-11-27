# Running an evidence-backed audit

Install with `bash install.sh both /path/to/project`. Python 3.10+ and PyYAML
are the supported runtime. Installation validates instruction markers before
changes and saves replaced files under `.clickthrough-backups/`. Those backups,
raw runs and bug recordings are private and ignored by Git.

## Start, inspect and continue

From the product root:

```bash
python3 .clickthrough/bin/ct.py doctor
bash .clickthrough/bin/new-run.sh --mode discover --independent yes
python3 .clickthrough/bin/ct.py status
python3 .clickthrough/bin/ct.py resume
python3 .clickthrough/bin/ct.py recheck
```

Keep the printed run ID: `CURRENT` is only a convenience for interactive use.
All seven modes are accepted: review, auto, discover, continue, update, fix,
recheck. Starting a run never executes tests or changes the product.
`resume` lists unfinished flows; validation errors also identify stale passes.
`recheck` lists all flows, conservatively: a changed product invalidates old
receipts. It does not silently narrow a full release verdict to changed files.

Generate inventory after preparing test tooling and before starting the test run:

```bash
python3 .clickthrough/bin/ct-inventory.py --json --out .clickthrough/inventory.json
# Optional: merge a locally exported OpenAPI document or runtime route list.
python3 .clickthrough/bin/ct-inventory.py --runtime routes.json --json --out .clickthrough/inventory.json
```

The runtime JSON is either OpenAPI `paths`, or `{ "items": [{ "kind": "route",
"what": "GET /orders", "where": "runtime:1" }] }`. No URLs are fetched.
Review scan diagnostics, mounted routes, dynamic registrations and the product's
menus/docs. Fill `inventory_review` in flows.yaml with `reviewer`, `notes` and
the inventory's `product_sha256`. This is a recorded review assertion, not an
automatically proven claim of completeness. Catch-all coverage globs are refused.

## Execute one flow

Declare a reviewed target in flows.yaml, including `name`, `data` and
`confirmed_by`. Target checks are procedural guards, not network isolation:
verify the product's database, email and storage settings before running it.
Production additionally requires `data: read-only` and `read_only: true` on the
flow. Security/attack variants are local-only.

The test must write a nonempty JSON array to `CT_ASSERTIONS_FILE`:

```json
[{"expected":"Created item survives reload","observed":"Item 42 visible after reload","passed":true,"case_ids":["S001-C01"],"check_ids":["Q01"]}]
```

Generate these observations in the test from actual assertions, never from a
prewritten success fixture. Use `CT_EVIDENCE_DIR` for screenshots, transcripts,
traces or video. The runner captures command output and hashes the artifacts.

```bash
python3 .clickthrough/bin/ct.py run --flow F001 --run-id RUN_ID \
  --target local --environment 'local stack v1, seeded tenant A' --update \
  --timeout 300 -- python3 clickthrough-tests/F001.py
```

Arguments after `--` are executed as an argument vector, without a shell. For a
shell pipeline, explicitly invoke `bash -c`. `--artifact PATH` attaches another
project-relative file. Without `--update`, the command prints the registry patch
for the lead to review. With it, the flow is updated; a failure still needs
triage, classification and a bug-register entry. A failed test is not automatically
proof of a product defect. Independent verification remains required.

Receipts bind the result to product content, Git revision, test hash, run metadata,
environment, command, observations and artifact hashes. Product/test changes
or altered artifacts invalidate the receipt. Ignored runtime data is not part of
the product fingerprint; describe the dataset, services and stubs in the environment.
These records detect drift and missing evidence; they cannot certify the truth
of assertions written by an agent. Secrets and binary recordings remain private.

## Coverage and release policy

P0 surface and goal `cases` fields now point to structured YAML cards, using
`.clickthrough/templates/case-card.yaml`. Each case needs an ID, expectation,
and a registered flow covering that surface or goal, with an observation naming
that case in `case_ids`. Passed coverage checks similarly require `check_ids`
in their flow observations. Keep narrative Markdown as
supporting notes. Enumerate chosen/skipped combinations in the card.

Fill `.clickthrough/coverage.yaml`: accessibility, devices, recovery, concurrency,
background jobs, upgrades, performance and external services. Split a category
into multiple concrete checks when needed. Passed checks must reference passing
flows. `not_applicable` needs a reason. Specify performance thresholds, dataset
size, supported browser/device versions and provider sandbox versus double in
`expected` before execution. A double-only check cannot establish provider readiness. Passed external-service
checks require `verification: sandbox` or `real`; keep double contract observations
as supporting evidence. The declaration must match the recorded environment.

```bash
python3 .clickthrough/bin/ct-check.py --json --require-ready
```

One policy applies to reports and CI:

- Invalid/missing/stale evidence, inventory, cards or coverage prevents READY.
- Confirmed open critical/high bugs block readiness regardless of flow priority.
  `wont_fix` does not waive a critical/high finding. Unconfirmed serious findings
  produce CANNOT TELL, likely NOT READY.
- P0 failures mean NOT READY. Every catalogued flow must actually run; blocked
  and traced flows are reported separately, never counted as executed.
- All required coverage checks must pass (or be explicitly not applicable).
  Lower-priority failures remain visible even if they do not block the gate.
- Exit 1: invalid audit data. Exit 2 with `--require-ready`: valid data but not
  READY. Exit 0 without the flag means validation succeeded, not release approval.

## Compare reports and share evidence

```bash
python3 .clickthrough/bin/ct.py status --save .clickthrough/runs/RUN_ID/summary.json
python3 .clickthrough/bin/ct.py status --compare .clickthrough/runs/PREVIOUS/summary.json
python3 .clickthrough/bin/ct.py export .clickthrough/runs/RUN_ID/evidence/request.json \
  --out .clickthrough/shared/request.json --redact-key email
```

Comparisons include changed statuses, removed flows and the next action. Export
redacts credential keys recursively and known credential patterns; add
`--redact-key` or `--redact-pattern` for project-specific fields. It refuses binary
exports and overwriting existing files. Review the derivative for personal data
and unknown secrets before sharing. No pattern-based scanner can guarantee all
sensitive content is removed. Never commit raw traces or session logs.

## Upgrading older audits

Reinstalling preserves existing flows, bugs and coverage. Version-1 records can
still be inspected, but an old filename/commit string is insufficient for readiness.
Convert case cards to YAML, fill the coverage matrix, regenerate/reconcile inventory,
and rerun flows through the runner. Do not manufacture receipts for historical runs.
Existing tracked proof files are not automatically untracked or removed: review
and relocate them yourself; adding an ignore rule cannot erase published history.
