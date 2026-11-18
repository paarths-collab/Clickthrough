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
   session. If they want you to continue anyway, continue and start the run
   with `--independent no`. If you did not build it, use `--independent yes`.
   Say which in the report.
2. **Pick the mode** from the request:
   - `review` (default): stop for the human after discovery and after the
     flow list.
   - `auto`: the request says "auto", "unattended" or "don't stop". Do not
     stop for review. Record that the map and flows were not human-checked.
   - `recheck`: fixes were made after an earlier report. Go straight to
     `uf-evaluate` in recheck mode.
   - `fix`: the request says "fix", "resolve" or "repair". Run the audit
     first if there is no report for this commit, then follow `uf-fix`.
     Fixing is builder work: say that a fresh session should run
     `uf-run recheck` before anyone calls it ready.
   - `update`: the product changed since the registry was written. Run
     `uf-discover` in update mode, then carry on from there.
   - `continue`: an earlier session left `.userflow/next.md`. Read it and
     `batches.md`, and carry on testing the next batches (`uf-parallel`).
   If `.userflow/bin/new-run.sh` does not exist, the project is not set
   up yet: load `uf-setup` and follow it first.
3. **Start the run:** `.userflow/bin/new-run.sh --harness <claude|codex|cursor|other> --model <your model id> --mode <mode> --independent <yes|no>`.
   Keep the printed folder; everything from this session goes there.
4. **Read `.userflow/flows.yaml`.** If it already has content, continue from
   what is not done. Do not start again from nothing.

## The phases, in order: list everything, then check everything

Each phase is its own skill. Load and follow it fully before moving on. Do
not merge phases or skip one because it looks unnecessary.

| # | Skill | Question it answers | Moves on when |
|---|---|---|---|
| 1 | `uf-preflight` | Does the software even run? | The real product is up with seed data (built with `uf-env` if needed), with an inbox if it sends email. If not: record the blocker and what a tester needs, then carry on; flows that cannot run are traced in code (guide, Trace mode). |
| 2 | `uf-discover` | What can a user touch? | `uf-check.py --stage discover` has no errors. In review mode, the human has seen the map. |
| 3 | `uf-catalog` + `uf-flows` (helpers in parallel, one area each) | What will a user try to do, all of it? | Every entry point in the code map belongs to a surface, every surface has its flows, and `uf-check.py --stage flows` shows no uncovered entry points. The total is the "Y" in "tested X of Y". In review mode, the human has seen the list. |
| 4 | `uf-parallel` with `uf-test` and `uf-cases` (helpers in parallel, each with its own data) | How do we check each flow for real? | Every flow is tested or blocked with a reason, batch by batch, or `.userflow/next.md` says exactly what is left. |
| 5 | `uf-evaluate` | What happens when a user does it? | The report is written, states "tested X of Y" per area, and `uf-check.py --stage evaluate` has no errors. |

Do not test before the list is complete, and do not stop testing because
the P0 flows are done: P0 decides the order, not the scope. If the session
cannot finish, follow `uf-parallel` section 5 (commit, `next.md`, tell the
human to continue) instead of ending with "not covered".

Keep `uf-patterns` (what breaks for users) and `uf-security` (what an
attacker or a key can do) at hand through every phase. It is the list of what
usually breaks between the parts of a product and how to see each one.

## Finishing

1. Run `.userflow/bin/collect-run.sh`. If it finds no session log (common
   for a subagent), note that in `decisions.md` and carry on.
2. Tell the human, in this order: the verdict; the worst things a user will
   hit, in plain words; what you could not verify and why; where the report
   is; which files you added or changed. Do not soften it and do not pad
   it. Do not commit anything unless asked.
   If your harness will not let you write `report.md` (some subagents
   cannot), put the whole report in your final message and say plainly that
   the file was not written.
3. Do not fix anything. If the human asks for fixes, that is a builder's
   job, done in another session, followed by `uf-run recheck`.

## The words you may use

- **READY**: every P0 flow passed with evidence on this commit.
- **NOT READY**: at least one P0 flow failed.
- **CANNOT TELL**: the product would not run, P0 flows are unverified, or
  part of the list is still untested. Say how much: "tested X of Y".

"It should work", "the code looks correct" and "tests pass" are none of
these. If you did not see it work, you do not know that it works.
