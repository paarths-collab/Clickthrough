---
name: uf-fix
description: Fix what a user-flow or security audit found, one finding at a time - reproduce it with the flow's test, make the smallest fix, prove the flow now works for real, check nothing else broke, and record it. Use after uf-run when asked to fix, resolve or repair the findings, or when given a report.md or flows.yaml with failures.
---

# Fix what the audit found

Input: `.userflow/flows.yaml` (flows with `fail` or `likely_broken`) and
the run's `report.md`. Output: fixes, each proven by a real run, and an
updated registry. Read `.userflow/guide.md` first.

## Before you start

- **Ask the human which findings to fix**, unless they said "all". Show the
  list worst first: Critical/High security, then P0, then the rest.
- **Branch.** Work on a branch, never directly on the default branch.
- **No production.** Same rule as the audit: local or test data only.
- Anything that changes access rules, data deletion, billing, or a
  migration on shared data: describe the change and get a yes first.

## For each finding, in order

1. **Reproduce.** Run the flow's test (or walk it) and watch it fail. For a
   `likely_broken` flow with no test, write the test first from the flow's
   steps. If it does not fail, the finding may be wrong: mark it
   `pass` with evidence, or note why it cannot be reproduced, and move on.
2. **Find the break.** Follow the hop where it breaks (guide, Trace mode):
   both sides of the boundary, not just the side that threw.
3. **Smallest fix at the cause.** Fix the mismatch where it is, not the
   symptom downstream. Match the project's conventions. Do not weaken a
   check, skip a test, catch-and-ignore an error, or widen permissions to
   make a flow pass.
4. **Prove it.** Rerun the flow's test: it must now pass for real, and
   check the result, not the message (saved data, other user's view,
   email, audit row). Then run the other routes to the same goal and the
   flows that share the files you changed.
5. **Keep the test.** The flow test stays in `userflow-tests/` so the bug
   cannot come back silently. Add a unit test too if the project has the
   pattern.
6. **Record it.** In the registry: `status: pass`, new `last_run` evidence,
   and `fixed_in: <commit>`. In `decisions.md`: what was wrong, what you
   changed, how you proved it.
7. **Commit one fix per finding**, with the flow id in the message.

Stop and report instead of guessing when a fix needs a product decision
(what should happen is not in the intent) or access you do not have.

## When done

- Run the project's own checks (lint, typecheck, tests).
- Run every P0 flow test again. Fixes break other things.
- Report three lists: **fixed and proven** (flow, what changed, evidence),
  **not fixed** (why), **newly broken** (anything that failed after a fix).
- Say plainly: "Fixed by this session. A fresh session should run
  `uf-run recheck` before calling it ready." The fixer does not give the
  release verdict.
