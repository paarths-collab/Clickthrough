---
name: ct-evaluate
description: Phase 5 of Clickthrough. Act as the user against the real running product - run every flow test, walk the most important flows by hand, sweep the navigation, capture console, network and server errors, classify each failure, and write a per-flow report with evidence and a READY / NOT READY / CANNOT TELL verdict. Reports only; never fixes. Use after ct-test, or in recheck mode after the builder has fixed things.
---

# ct-evaluate: what happens when a user does it?

This is the phase that produces the answer. You run every flow against the
real product, collect evidence, and report what a user would experience.
You do not fix anything and you do not explain anything away.

Follow `.clickthrough/guide.md`. Log each step in `decisions.md`.

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
   the commands in the registry. If there is no stop command, stop the
   process that `run.boot` started. Note the commit. If it will not start,
   the verdict is CANNOT TELL; stop and report.
2. **Run every flow test**, with `CT_EVIDENCE_DIR` set to
   `.clickthrough/runs/<run-id>/evidence`. Save the full output to
   `evidence/test-output.txt`. Reset data between flows if the tests do not
   do it themselves.
3. **Rerun each failure once, on its own**, after a reset, with
   `CT_EVIDENCE_DIR` set to `evidence/rerun` so the first run's evidence is
   kept. Same result: real failure. Different result: record it as flaky,
   and treat flaky as a failure, because users hit it too.
4. **Walk every P0 flow by hand**, and every failed flow, through the
   user's door, in a way that lets you see what they see (a browser or
   screenshots for a UI; the real output for a CLI, API or library).
   Follow the flow's steps as written. You
   are checking what tests miss: the page looks broken, the message is
   confusing or absent, the button is there but off-screen, the user is
   left with no idea what happened. Save what you saw in `evidence/walk/`.
   If you have no way to see the screen, log a tool gap and say the walk
   was not done.
5. **Sweep the navigation.** As each persona, try every item the product
   offers in its menus (or `--help`, docs, exported API). Each one must
   lead to something real and working, and record every failed request
   (any 4xx or 5xx, network error) and console error on each page while it
   loads and settles. A page that looks fine while one of its requests
   fails is a finding (data silently missing), unless the failure is an
   expected refusal you can name. Record each result in the
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
   run it again. Do not count it against the product. If the defect was in
   a helper that other tests share, discard the run and rerun everything
   from a clean start. List test defects in the report.
8. **Update the registry.** For every flow set `status`, `failure_class`,
   `finding`, and `last_run` (commit, run id, evidence paths relative to
   the project root). The rules:
   - `pass` needs evidence from this run. No evidence: `unverified`.
   - Could not run it: trace it in code (guide, Trace mode). A break
     found: `likely_broken`, with class, finding and confidence. No break
     found: `blocked`, with `ENV_BLOCKED` or `TOOL_GAP` and
     `trace: "no break found in code"`. Every P0 flow you could not run
     gets traced; do P1 flows as time allows and say which you skipped.
   - A goal works only if every route to it works. If one route was not run
     (blocked, untested, only traced), never write that the goal works:
     name the route and mark it unverified. Example: "invite works in the
     app; the email-link route is unverified (no inbox)".
8b. **Update the bug register** (`.clickthrough/bugs.yaml`): one entry per
   cause, with every flow it breaks, severity, where it breaks, evidence,
   how it is known (`ran` or `traced`) and who verified it. Every `fail`
   and `likely_broken` flow names its bug (`bug: B007`). In recheck mode,
   mark bugs `fixed` with the commit and run that proved it; never delete
   a bug.
9. **Write `report.md`** in the run folder from the template. Findings go
   worst first, each written so a builder can act on it without asking you
   anything: what the user did, what they expected, what they got, where it
   breaks, and the evidence. If your harness refuses to write the file,
   return the whole report as text and say the file was not written.
10. **Check and conclude.** Run
    `python3 .clickthrough/bin/ct-check.py --stage evaluate`, fix every error,
    and use its verdict unless you have a stated reason not to.

## The verdict

- **READY**: `ct-check.py --require-ready` succeeds under the shared guide policy.
- **NOT READY**: any P0 flow fails or any confirmed critical/high bug remains unresolved.
- **CANNOT TELL**: the product would not run, or any P0 flow is
  `unverified`, `blocked` or `likely_broken`. If any P0 flow is
  `likely_broken`, say "CANNOT TELL, likely NOT READY" and lead with
  those flows.

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

Use the runner's receipt path as `last_run.result`; filenames alone are not proof.
Compare the last summary with `ct.py status --compare <previous-summary.json>` to
show new failures, recoveries, removed flows and remaining work. Raw evidence is
private; use `ct.py export` for reviewed sanitized derivatives. Do not commit raw
recordings. Save summaries under the current run with `ct.py status --save`.
