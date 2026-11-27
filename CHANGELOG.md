# Changes

## 2.0.0 (unreleased)

Readiness is now an evidence-backed gate. Open critical/high findings, unexecuted
flows, incomplete quality checks, missing case observations, and stale evidence
prevent READY. `--require-ready` provides a CI exit code; `--json` provides a
machine-readable summary.

New local runner commands provide diagnosis, progress, continuation, recheck
planning, command execution with assertions, report comparisons and sanitized
exports. Receipts bind product content, flow expectations, test file, run,
environment, command, observations and evidence hashes. Binary evidence stays
private. Independent verification is still needed to judge assertion quality.

Installation validates markers, backs up managed paths, and restores them on
installer errors. Run creation uses serialized JSON and unique IDs and supports
all documented modes. Discovery adds missed Astro/SvelteKit/Next.js/Python/cron
cases, local runtime-schema merging and explicit scan limitations.

Service doubles support required fields, route overrides, response sequences,
delays, disconnections and recursive credential redaction. CI includes Linux and
macOS lifecycle/regression coverage. Optional behavioral evaluations use separate
runner/grader adapters with declared caps; benchmark summaries reject unmatched
or single-run comparisons.

### Migration

Reinstall, convert P0 case cards to structured YAML, fill coverage.yaml, regenerate
and reconcile inventory, and execute fresh receipts. Historical records are
preserved but cannot establish current readiness. See docs/runner.md. Previously
tracked recordings are not automatically removed from Git or published history.

### Limits

Inventory remains heuristic. Evidence hashes do not establish the truth of an
assertion. Provider sandbox declarations and exclusion reasons require review.
Target checks do not isolate network access. Automated redaction is not a guarantee
of anonymity. Changed-product rechecks conservatively rerun all flows; selective
reuse of old receipts is intentionally not a full release verdict. Live model
evaluations require explicitly configured adapters and credentials.
