---
name: ct-run
description: Check whether a product actually works for the people who use it. Use when asked if a project is ready, done, working, shippable or safe to release; when asked to evaluate, QA, review or find what is broken; or after an agent claims a build is complete. Runs the product for real and tests every user flow end to end (frontend, backend, database, MCP), instead of reviewing code.
---

# ct-run: is this product usable?

You are about to answer "can a real person use this?". A code review cannot
answer that. You answer it by starting the product, acting as each kind of
user, and recording what happens on every flow.

Read `.clickthrough/guide.md` now. Its rules apply to everything below.

## Before you start

1. **Are you the builder?** If this session wrote or changed the product's
   code, you carry the builder's assumptions and will test what you meant to
   build, not what a user meets. Say so to the human and recommend a fresh
   session. If they want you to continue anyway, continue and start the run
   with `--independent no`. If you did not build it, use `--independent yes`.
   Say which in the report.
2. **Pick the mode** from the request:
   - `review` (default): stop for the human after discovery and after the
     flow list.
   - `auto`: the request says "auto", "unattended" or "don't stop". Do not
     stop for review. Record that the map and flows were not human-checked.
   - `recheck`: fixes were made after an earlier report. Go straight to
     `ct-evaluate` in recheck mode.
   - `fix`: the request says "fix", "resolve" or "repair". Run the audit
     first if there is no report for this commit, then follow `ct-fix`.
     Fixing is builder work: say that a fresh session should run
     `ct-run recheck` before anyone calls it ready.
   - `update`: the product changed since the registry was written. Run
     `ct-discover` in update mode, then carry on from there.
   - `discover`: the request says "discover", "map" or "list first". Run
     phases 1 to 3 (preflight, discover, catalog with every workflow
     card), save the registry, the code map and the cards, and stop.
     Do not start testing in this mode, not even a few flows: the human
     decides when testing starts.
     Report: entry points, surfaces, workflows, flows by priority, and
     the tester kit. The human looks at the full list; a later session
     tests it with `continue`.
   - `continue`: an earlier session left `.clickthrough/next.md` (or ran in
     `discover` mode). Read it and `batches.md`, then, before the next
     batches:
     1. **Retry what was blocked.** The skills and tools may be newer than
        the run that wrote the registry. Re-read `ct-env` and
        `ct-preflight` step 9, and for every `blocked` flow try again with
        what is available now: a local version of the service, the staging
        target or sandbox keys the human has since provided, or a service
        double (`ct-double.py`). Keep a flow `blocked` only after all three
        fail, and write why in its finding.
     2. **Do the depth work that is missing** (`ct-cases` files for P0
        components and workflows); it is part of the batches, not optional.
     3. Then carry on testing the next batches (`ct-parallel`).
   If `.clickthrough/bin/new-run.sh` does not exist, the project is not set
   up yet: load `ct-setup` and follow it first.
3. **Start the run:** `.clickthrough/bin/new-run.sh --harness <claude|codex|cursor|other> --model <your model id> --mode <mode> --independent <yes|no>`.
   Keep the printed folder; everything from this session goes there.
4. **Check what the human provided** for this audit: a staging URL, test
   accounts, an inbox, permissions (`CT_*` environment variables, the
   registry's `targets:`). What is missing is asked for in preflight
   (`ct-preflight` step 9), not guessed.
   **Usage budget.** A full audit can use a lot of a usage plan, and you
   cannot see the human's plan. Read `CT_BUDGET` (`small`, `medium`,
   `large` or `metered`). If it is not set, ask in review mode ("Which
   plan are you on, and for Team or Enterprise, which seat?") and map the
   answer with the table in `.clickthrough/guide.md` ("Usage budget"); in
   auto mode, treat it as `small`.
   - `small` or unknown: run in `discover` mode first even when asked for
     a full audit: map everything, stop, and tell the human how many
     flows and workflows there are, how many sessions testing may take,
     and how to continue. Testing starts when they say so.
   - `metered` (pay per use): ask for a spending cap before testing, and
     stop at it.
   - `medium` and `large`: carry on.
   The scope never shrinks: every flow is still tested, over as many
   sessions as it takes.
5. **Read `.clickthrough/flows.yaml`.** If it already has content, continue from
   what is not done. Do not start again from nothing.

## The phases, in order: list everything, then check everything

Each phase is its own skill. Load and follow it fully before moving on. Do
not merge phases or skip one because it looks unnecessary.

| # | Skill | Question it answers | Moves on when |
|---|---|---|---|
| 1 | `ct-preflight` | Does the software even run? | The real product is up with seed data (built with `ct-env` if needed), with an inbox if it sends email. If not: record the blocker and what a tester needs, then carry on; flows that cannot run are traced in code (guide, Trace mode). |
| 2 | `ct-discover` | What can a user touch? | `ct-check.py --stage discover` has no errors. In review mode, the human has seen the map. |
| 3 | `ct-catalog` + `ct-flows` (helpers in parallel, one area each) | What will a user try to do, all of it? | Every entry point in the code map belongs to a surface, every surface has its flows, and `ct-check.py --stage flows` shows no uncovered entry points. The total is the "Y" in "tested X of Y". In review mode, the human has seen the list. |
| 4 | `ct-parallel` with `ct-test` and `ct-cases` (helpers in parallel, each with its own data) | How do we check each flow for real? | Every flow is tested or blocked with a reason, batch by batch, or `.clickthrough/next.md` says exactly what is left. |
| 5 | `ct-evaluate` | What happens when a user does it? | The report is written, states "tested X of Y" per area, and `ct-check.py --stage evaluate` has no errors. |

After installing test tooling, regenerate/reconcile inventory and start a fresh
testing run if the product fingerprint changed since preflight. Keep the discovery
run as history. Do not reuse stale receipts.

Do not test before the list is complete, and do not stop testing because
the P0 flows are done: P0 decides the order, not the scope. If the session
cannot finish, follow `ct-parallel` section 5 (save a checkpoint, `next.md`, tell the
human to continue) instead of ending with "not covered".

Three kinds of bug, all in one bug register (`.clickthrough/bugs.yaml`):
- **user flows** (`ct-patterns`, `ct-cases`): what a person hits;
- **security** (`ct-security`): what another tenant, a lower role, a key
  or an agent can do that they must not;
- **software** (`ct-code`): what is wrong in the code even when no flow
  shows it yet (swallowed errors, wrong writes, jobs that never catch up,
  races, config drift, broken builds and tests).
Start the `ct-code` and `ct-security` reading in parallel with listing
(helpers per area; reading changes no data), and prove what they find
during testing.

## Finishing

1. Run `.clickthrough/bin/collect-run.sh`. If it finds no session log (common
   for a subagent), note that in `decisions.md` and carry on.
2. Tell the human, in this order, in plain words first (the report's "In plain words"): the verdict; the worst things a user will
   hit, in plain words; what you could not verify and why; where the report
   is; which files you added or changed. Do not soften it and do not pad
   it. Do not commit anything unless asked.
   If your harness will not let you write `report.md` (some subagents
   cannot), put the whole report in your final message and say plainly that
   the file was not written.
3. Do not fix anything. If the human asks for fixes, that is a builder's
   job, done in another session, followed by `ct-run recheck`.

## The words you may use

- **READY**: the authoritative `ct-check.py --require-ready` gate passes: fresh receipts, every flow executed, required coverage checked, and no blocking serious bugs.
- **NOT READY**: a P0 flow failed, or a confirmed critical/high bug remains unresolved.
- **CANNOT TELL**: the product would not run, P0 flows are unverified, or
  part of the list is still untested. Say how much: "tested X of Y".

"It should work", "the code looks correct" and "tests pass" are none of
these. If you did not see it work, you do not know that it works.
