---
name: uf-evaluate
description: Phase 5 of user-flow QA. Act as the user against the real running product - run every flow test, walk the most important flows by hand, sweep the navigation, capture console, network and server errors, classify each failure, and write a per-flow report with evidence and a READY / NOT READY / CANNOT TELL verdict. Reports only; never fixes. Use after uf-test, or in recheck mode after the builder has fixed things.
---

# uf-evaluate: what happens when a user does it?

This is the phase that produces the answer. You run every flow against the
real product, collect evidence, and report what a user would experience.
You do not fix anything and you do not explain anything away.

Follow `.userflow/guide.md`. Log each step in `decisions.md`.

## Mindset

- You are the user. You do not know how the code works and you do not care.
  Do not open source files to decide whether something works. Open them
  only after a failure, to say where it breaks.
- A fresh context is best. If this session built the product or wrote the
  flow tests long ago in a crowded context, say so in the report.
- Expect the product to be broken. Your job is to find out how, not to
  confirm that it is fine.

## Steps

1. **Clean start.** Stop the product, reset the data, start it again from
   the commands in the registry. Note the commit. If it will not start, the
   verdict is CANNOT TELL; stop and report.
2. **Run every flow test**, with `UF_EVIDENCE_DIR` set to
   `.userflow/runs/<run-id>/evidence`. Save the full output to
   `evidence/test-output.txt`. Reset data between flows if the tests do not
   do it themselves.
3. **Rerun each failure once, on its own**, after a reset. Same result:
   real failure. Different result: record it as flaky, and treat flaky as a
   failure, because users hit it too.
4. **Walk every P0 flow by hand**, and every failed flow. Use a browser you
   can see (a browser tool, or a script that takes a screenshot at each
   step which you then look at). Follow the flow's steps as written. You
   are checking what tests miss: the page looks broken, the message is
   confusing or absent, the button is there but off-screen, the user is
   left with no idea what happened. If you have no way to see the screen,
   log a tool gap and say the walk was not done.
5. **Sweep the navigation.** As each persona, click every item in every
   menu. Each one must open a real, working page. Record each result in the
   report's Navigation table, with dead items and pages that have no way in.
6. **Collect errors seen along the way**, including during flows that
   passed: console errors, failed requests, and errors in the server log
   during the run. A flow that "passes" while the server logs an exception
   is a finding.
7. **Classify every failure** using the classes in the guide. For each,
   find where it breaks, working inward from what the user saw: the screen,
   then the request the page sent and the response it got, then the server
   log, then the database. Now you may read the code to name the cause.
   State the cause only if you saw it; otherwise say "cause not found".
   If the test itself was wrong, class it `TEST_DEFECT`, fix the test, and
   run it again. Do not count it against the product.
8. **Update the registry.** For every flow set `status`, `failure_class`,
   `finding`, and `last_run` (commit, run id, evidence paths). The rules:
   - `pass` needs evidence from this run. No evidence: `unverified`.
   - Could not run it: `blocked`, with `ENV_BLOCKED` or `TOOL_GAP`.
   - A goal works only if every route to it works.
9. **Write `report.md`** in the run folder from the template. Findings go
   worst first, each written so a builder can act on it without asking you
   anything: what the user did, what they expected, what they got, where it
   breaks, and the evidence.
10. **Check and conclude.** Run
    `python3 .userflow/bin/uf-check.py --stage evaluate`, fix every error,
    and use its verdict unless you have a stated reason not to.

## The verdict

- **READY**: every P0 flow is `pass` with evidence on this commit.
- **NOT READY**: any P0 flow is `fail`.
- **CANNOT TELL**: the product would not run, or any P0 flow is
  `unverified` or `blocked`.

Never round up. Nine of ten P0 flows passing is NOT READY. A flow you
believe works but did not run is not a pass.

## Recheck mode

After the builder has fixed things:

1. Clean start on the new commit.
2. Rerun every flow that failed, was blocked or was unverified.
3. Rerun every flow that passed before. Fixes break other things, and that
   is exactly what a builder does not check.
4. For a large product where a full rerun is too slow, rerun all P0 flows
   plus every flow sharing a surface with a changed file, and say so.
5. Report what is now fixed, what is still broken, and what newly broke.

## What you must not do

- Fix application code, or suggest the product is fine "apart from" a P0
  failure.
- Mark something pass because the code looks right.
- Drop a flow from the report because it could not be tested. It goes under
  "Not verified" with what would be needed.
