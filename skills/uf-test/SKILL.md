---
name: uf-test
description: Phase 4 of user-flow QA. Write one end-to-end test per user flow that drives the real running product the way a user would (browser, API, MCP client, CLI) and checks what the user sees, what was saved and any side effects - no mocks. Use after uf-flows, or when asked to write user-flow, end-to-end, acceptance or journey tests from a list of flows.
---

# uf-test: turn a flow into a real check

Each flow becomes one test file that does what the user does and checks
what the user would notice. These tests are different from the builder's
tests in one way that matters: they go through the whole product, so they
fail when the pieces do not fit together.

Follow `.userflow/guide.md`. Log each step in `decisions.md`. The product
must be running.

## Rules for every test

1. **One flow, one file**, in `userflow-tests/`, named
   `<flow-id>-<short-name>` with the right extension. Put the flow id, goal
   and route in a comment at the top. Record the path in the flow's
   `test_file`.
2. **Use the project's end-to-end framework if it has one.** If it has
   none, choose one that drives the user's door for this kind of product
   (browser automation, an HTTP client, running the command, a small
   program against the installed library, UI automation, an MCP client).
   Prefer the project's own language. Record the choice and the command
   that runs all flow tests in `run.test_command`. Adding the test tool as
   a dev dependency is allowed; keep its config, helpers and scratch output
   inside `userflow-tests/` (scratch in `userflow-tests/.results/`).
3. **Real product, real door.** The test talks to the running stack through
   the entry point the user uses. It does not import application code, call
   internal functions, or replace any part of this product with a fake.
4. **Start where the user starts and click through.** Begin at the flow's
   `start`. Reach each screen by clicking the menu items, links and buttons
   named in the steps. Do not `goto` a deep URL to skip navigation: if the
   link is missing, the test must fail. Do not call the API to perform a
   step the user performs in the UI. Only a flow whose step *is* "changes
   the address" (see `uf-flows`) may type one; say so in the top comment.
5. **Find things the way a user does**: by visible text, label, role or
   placeholder. Not by internal ids or CSS classes, unless nothing else
   exists (and note that as a usability observation).
6. **Own your data.** Reset to a known state before the test, or create a
   fresh user and fresh data inside it. A test must pass when run alone and
   when run after any other test. Preconditions may be set up by script or
   API; the flow's own steps may not.
7. **Never weaken a test to get a pass.** No loosened assertions, no blind
   retries, no skips, no long sleeps to hide a race. If a test fails, the
   next phase decides whether the product or the test is wrong.
8. **Wait for what the user waits for.** After an action, wait for the
   specific thing the user would see (the text appears, the row is gone) or
   for the specific response to that action, with a normal timeout. Do not
   wait on "network idle" or a fixed pause: on an already-loaded page those
   return before the product has answered, and the check after them reads
   the old screen.
9. **Component cases are table-driven.** The cases from `uf-cases` go in
   `userflow-tests/<surface-id>.cases.<ext>`, one row per case, through
   the same door as the flows.
10. **Do not touch application code.** If a flow cannot be tested without a
   change to the product, mark it `blocked` and log a tool gap.

## What each test must check

For every step, check the `see`. Then, at the end, all four of these:

- **What the user sees**: the result is on the screen, in words a user
  would recognise. A success message alone is not the result: after "Task
  added!", the task must be in the list.
- **What was saved**: check `persisted`. Read the database directly if you
  can. Otherwise leave and come back (new browser session, log in again)
  and look. Do both when you can; they catch different bugs.
- **It lasts**: reload the page and check the result is still there. Many
  bugs look fine until a refresh.
- **Jobs and schedules**: snapshot the data the job should change, run the
  job (trigger its endpoint or command), and compare. "It answered 200" is
  not a pass; with no data check the flow is `unverified`. Also feed it one
  bad record and check the next good record is still processed.
- **Side effects**: the email, notification, job or call to another system
  listed in `side_effects`.

What to check at the end of each flow comes from `uf-patterns`: the
result after a refresh, the other user's view, the email and its links,
the saved data, and that every process is still alive.

Also listen during the whole flow and fail on what a user would suffer
from: uncaught page errors, requests to this product that return 4xx or
5xx when the flow expects success, and a page stuck on a loading state.
Print them in the test output so they become evidence.

Some refusals are the product working: the 401 for a wrong password, the
"not logged in" check on a logged-out page. List the refusals a flow
expects at the top of its test, by method, path and status. Every other
4xx or 5xx from this product fails the flow. A missing static file that no
user would notice (a favicon) is printed and reported under "Errors seen",
and does not fail the flow.

For `wrong_input` and `not_allowed` flows, the pass condition is that the
user is stopped **and told why in words**, and that nothing wrong was
shown or saved. A silent nothing is a failure. A 500 is a failure. Check
the two halves separately and print both, so the finding can say which
failed: "another user's data was shown or changed" is serious; "the data
stayed safe and the user was told nothing" is a lesser failure of the same
flow, and the finding must say the data was safe.

For flows whose surface is tagged `intent` (promised, not found), still
write the test from the intent. It will fail. That is how a missing feature
becomes visible instead of forgotten.

## Evidence from the test

Have each test save a screenshot of the final state, and of the page at the
moment of failure, to the folder in the `UF_EVIDENCE_DIR` environment
variable when it is set: `<UF_EVIDENCE_DIR>/<flow-id>/final.png` and
`failure.png`. Print the values it observed, so the output alone shows what
happened. When `UF_RECORD=1` is set (the verifier sets it), also record a
video and a step trace for screen flows, or a full request and response
transcript for API, CLI and job flows, into the same folder.

## Order of work

P0 flows first, then P1, then P2, one flow at a time. After writing each
test, run it once on its own to make sure it runs to a real result. A test
that fails because the product is broken is a finished test. A test that
fails because of its own mistake (wrong selector, bad setup) is not: fix
the test.

Do not record `pass` or `fail` in the registry in this phase. That is
`uf-evaluate`'s job, in a clean run with evidence. The one status you do
set now is `blocked`, for a flow that cannot be tested: give it a
`failure_class` (`TOOL_GAP` or `ENV_BLOCKED`), a `finding`, and
`test_file: null`.

When every flow has a test file or is `blocked` with a reason, run
`python3 .userflow/bin/uf-check.py --stage test` and fix every error.
