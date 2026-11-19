---
name: uf-code
description: Find software issues in the code itself - errors swallowed, data written to the wrong place, jobs that never catch up, races, leaks, slow queries, missing transactions, config drift, broken builds and tests - by reading the code with a checklist and then proving each suspicion with a small test or a run. Results go into the same bug register as user-flow and security bugs. Use in uf-run alongside user flows and security, or when asked for a code review, a software audit or bugs a user may never see directly.
---

# Software issues: what is broken in the code

User flows find what a person hits. Security finds what an attacker can
do. This finds what is wrong in the code even when no flow shows it yet:
the audit row that is never written, the job that falls further behind
every day, the key that is silently ignored. Many become user-facing
later, at scale or on a bad day.

Same rules as the rest of the pack: read to find, run to prove. A
suspicion from reading is `read`; followed hop by hop it is `traced`;
reproduced by a test or a run it is `ran`.

## 1. Run what the project already has

Build, typecheck, lint, unit and integration tests, dependency audit, and
any static analysis the project uses (its linters, type checker, security
scanner). Record each: pass, fail, warnings. A failing check is a bug;
a check that cannot run is a finding too. Note flaky tests (pass and fail
on the same commit). Then use any general tool available for the language
(a semgrep-style scanner, the language's vet or clippy, a leak or race
detector) only if it is already installed or the human allowed it.

## 2. Read with this checklist

Use `uf-inventory.py` output to find the code behind each area. For each
area, go through the list. Helpers can take one area each in parallel;
reading changes no data.

**A. Errors and failure handling**
1. Errors caught and ignored, or logged and then treated as success
   (empty `catch`, `except: pass`, `.catch(() => {})`, ignored return
   values, `_ = err`).
2. A failure in step two leaving step one done (no transaction, no
   rollback, no compensation).
3. Retries without limit or backoff; no timeout on outbound calls.

**B. Data correctness**
4. Writes to the wrong field, table or type (a name where an id goes, a
   column that does not exist, a renamed field still used elsewhere).
5. Queries and code that disagree with the schema or migrations.
6. Missing constraints the code relies on (unique, foreign key, not
   null); deletes that leave orphans; soft deletes that some reads ignore.
7. Time: time zones, daylight saving, "now" taken twice, timestamps
   compared across clocks.
8. Numbers: money in floats, rounding, overflow, off-by-one in paging and
   ranges.

**C. Jobs, queues and scale**
9. A job that processes a fixed batch per run while more arrives (it
   never catches up); no alert when it falls behind.
10. A job that is not safe to run twice, or twice at the same time.
11. Unbounded queries or loads (no limit, no paging, everything into
    memory); N+1 queries in lists.

**D. Concurrency**
12. Read-then-write without a lock or a condition (lost updates, double
    spend, duplicate records); shared mutable state across requests.

**E. Configuration and operations**
13. Settings read with a silent default, or two settings where one
    silently wins; environment variables used in code but missing from
    the example file, or the reverse.
14. Values that differ between components (one accepts what another
    rejects); feature flags never read.
15. Health checks that say healthy while a dependency is down; logs that
    hide the error or leak secrets and personal data.

**F. Code health**
16. Dead code reached by nothing, routes or handlers nothing calls, TODO
    or "not implemented" on a reachable path, debug output left in.
17. Duplicated logic that has already drifted (two validators, two
    permission checks that disagree).
18. Build and dependency health: deprecated or vulnerable packages, pinned
    versions with known fixes, warnings that hide real problems.

## 3. Prove each suspicion

For every suspicion, try to make it fail for real, smallest way first:
- a unit or integration test that calls the code with the triggering
  input and shows the wrong result (put it in `userflow-tests/code/`);
- a run against the local copy that shows the effect (the missing audit
  row, the job's backlog after two runs, the duplicate after two parallel
  requests);
- for scale issues, a small dataset that shows the shape (the job handles
  N per run while N+1 arrive).

Recorded output is the proof (save it under `.userflow/proof/<bug-id>/`).
What cannot be run stays `traced` or `read`, with the file and line and
how sure you are.

## 4. Write them down

Every issue goes into `.userflow/bugs.yaml` with `kind: software`, the
file and line in `where`, the cause, how it is known, and the proof. Fill
the "Software checklist" table in the report: every check above with
ran, traced, read or not done (and why). Severity: critical when data is
lost or corrupted, high when an audit, payment, privacy or security
control silently fails, medium when it fails at scale or on retry, low
for code health.
