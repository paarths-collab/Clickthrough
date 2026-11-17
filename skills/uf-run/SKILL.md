---
name: uf-run
description: Check whether a product actually works for the people who use it. Use when asked if a project is ready, done, working, shippable or safe to release; when asked to evaluate, QA, review or find what is broken; or after an agent claims a build is complete. Runs the product for real and tests every user flow end to end (frontend, backend, database, MCP), instead of reviewing code.
---

# uf-run: is this product usable?

You are about to answer "can a real person use this?". A code review cannot
answer that. You answer it by starting the product, acting as each kind of
user, and recording what happens on every flow.

Read `.userflow/guide.md` now. Its rules apply to everything below.

## Before you start

1. **Are you the builder?** If this session wrote or changed the product's
   code, you carry the builder's assumptions and will test what you meant to
   build, not what a user meets. Say so to the human and recommend a fresh
   session. If they want you to continue anyway, continue and record
   `"evaluator_independent": false` in `run.json` and in the report.
2. **Pick the mode** from the request:
   - `review` (default): stop for the human after discovery and after the
     flow list.
   - `auto`: the request says "auto", "unattended" or "don't stop". Do not
     stop for review. Record that the map and flows were not human-checked.
   - `recheck`: fixes were made after an earlier report. Go straight to
     `uf-evaluate` in recheck mode.
   - `update`: the product changed since the registry was written. Run
     `uf-discover` in update mode, then carry on from there.
3. **Start the run:** `.userflow/bin/new-run.sh --harness <claude|codex> --model <your model id> --mode <mode>`.
   Keep the printed folder; everything from this session goes there.
4. **Read `.userflow/flows.yaml`.** If it already has content, continue from
   what is not done. Do not start again from nothing.

## The five phases, in order

Each phase is its own skill. Load and follow it fully before moving on. Do
not merge phases or skip one because it looks unnecessary.

| # | Skill | Question it answers | Moves on when |
|---|---|---|---|
| 1 | `uf-preflight` | Does the software even run? | The real product is up with seed data. If not: stop, report the blocker. |
| 2 | `uf-discover` | What can a user touch? | `uf-check.py --stage discover` has no errors. In review mode, the human has seen the map. |
| 3 | `uf-flows` | What will a user try to do? | `uf-check.py --stage flows` has no errors. In review mode, the human has seen the flows. |
| 4 | `uf-test` | How do we check each flow for real? | Every flow has a test file, or is marked blocked with a reason. |
| 5 | `uf-evaluate` | What happens when a user does it? | The report is written and `uf-check.py --stage evaluate` has no errors. |

For a large product, do phases 2 to 5 one area at a time, P0 flows first.

## Finishing

1. Run `.userflow/bin/collect-run.sh`.
2. Tell the human, in this order: the verdict; the worst things a user will
   hit, in plain words; what you could not verify and why; where the report
   is. Do not soften it and do not pad it.
3. Do not fix anything. If the human asks for fixes, that is a builder's
   job, done in another session, followed by `uf-run recheck`.

## The words you may use

- **READY**: every P0 flow passed with evidence on this commit.
- **NOT READY**: at least one P0 flow failed.
- **CANNOT TELL**: the product would not run, or P0 flows are unverified.

"It should work", "the code looks correct" and "tests pass" are none of
these. If you did not see it work, you do not know that it works.
