---
name: uf-parallel
description: Test a long flow list (hundreds of flows) by splitting it into batches - helper agents in parallel where the harness has them, or several sessions one after another - each with its own test data, with one lead that merges results into the registry and keeps going until every flow is tested. Use in uf-run when the catalogue has more flows than one session can finish, or when asked to continue an audit.
---

# Check all of it: batches, helpers, and carrying on

(Listing the flows in parallel is in `uf-catalog`. This skill is for
checking them, where shared test data makes parallel work harder.)

One agent cannot write and run three hundred flows in one session. The
work has to be split and continued, without anyone stopping early or two
helpers breaking each other's data.

## Roles

- **Lead** (the session that ran `uf-run`): owns `.userflow/flows.yaml`,
  the stack, the batch plan and the report. Only the lead writes the
  registry.
- **Helpers:** each takes one batch, writes tests and runs them, and
  returns results. Helpers never write the registry, never reset shared
  data, never stop or restart the stack.

## 1. Plan the batches

Group untested flows by area into batches small enough for one helper to
finish (about 15 to 30 flows, P0 batches first). Depth work is batch work
too: add one batch per area for the `uf-cases` files of its P0 components
and P0 workflows (understand, list every case and path, test them), and
one batch for retrying `blocked` flows with service doubles or newly
provided access. A run is not done while these batches are open. Write the plan to
`.userflow/batches.md`: batch id, area, flow ids, status.

## 2. Give every helper its own data

Shared data is the main way parallel testing produces false bugs. Before a
batch starts, the lead creates for it:
- its own tenant or workspace (or its own database, if tenants do not
  exist), seeded with an account per role;
- a unique prefix for every record the helper creates.

Helpers clean up only inside their own tenant. A global reset happens only
when no helper is running.

## 3. Start helpers

Use the harness's way of running agents in parallel (Claude Code
subagents, Codex or Cursor background agents). Give each helper, in its
prompt: the batch's flows (ids, starts, steps), its tenant and accounts,
the base URL, the test folder and naming (`userflow-tests/<flow-id>-*`),
`.userflow/guide.md` and the skills `uf-test`, `uf-cases`, `uf-patterns`,
`uf-security`, and what to return: per flow, status, evidence paths, and a
one-line finding for failures, in YAML.

Without parallel agents, run the batches one after another in this
session.

## 4. Verify, then merge

Every batch gets a **tester** and a separate **verifier** (another helper,
or the lead). The verifier never trusts the tester's word:
- reruns every failure alone in a clean tenant (flaky or real?);
- reads each pass's test and evidence and checks that it really asserts
  what the flow says (a test that only takes a screenshot, or checks a
  success message, is not a pass);
- reruns a sample of passes.

Only verified results go into the registry; results the verifier changed
are noted in `decisions.md`. Keep every test file path the tester wrote.
Each failure goes into the bug register (`.userflow/bugs.yaml`): add it to
an existing bug with the same cause, or open a new one.

Then mark the batch done in `batches.md` and commit the registry, the bug
register and the tests. Commit after every batch, small enough that a
session ending without warning (time, context, or a usage limit) loses at
most one batch.

## Match the helpers to the machine

More helpers than the machine can carry produce timeouts that look like
bugs. Start with as many helpers as CPU cores minus one (at most 4 on a
small machine), watch the load and the product's response times, and run
fewer when timeouts appear. A failure that only happens under load is
rerun alone before it counts.

## 5. Carry on until the list is done

Keep starting batches until every flow is tested or blocked with a reason.
There is no sampling and no budget cut-off: the goal is every bug. A
smaller usage plan only means more sessions; the registry, the bug
register and `next.md` carry the work from one session to the next.
If this session cannot finish (time, context, cost), do not drop flows and
do not end with "not covered" alone:
- commit the registry, tests and `batches.md`;
- write `.userflow/next.md`: what is done (X of Y), the next batches, and
  anything the next session needs to know;
- tell the human to start a new session with "Continue the user-flow
  audit. Use uf-run continue."

The report always states coverage as "tested X of Y flows" per area.
