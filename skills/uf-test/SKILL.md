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
   none, use Playwright for anything with a browser or HTTP, and the
   official MCP client for MCP tools. Record the choice and the command
   that runs all flow tests in `run.test_command`.
3. **Real product, real door.** The test talks to the running stack through
   the entry point the user uses. It does not import application code, call
   internal functions, or replace any part of this product with a fake.
4. **Start where the user starts and click through.** Begin at the flow's
   `start`. Reach each screen by clicking the menu items, links and buttons
   named in the steps. Do not `goto` a deep URL to skip navigation: if the
   link is missing, the test must fail. Do not call the API to perform a
   step the user performs in the UI.
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
8. **Do not touch application code.** If a flow cannot be tested without a
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
- **Side effects**: the email, notification, job or call to another system
  listed in `side_effects`.

Also listen during the whole flow and fail on what a user would suffer
from: uncaught page errors, requests to this product that return 4xx or
5xx when the flow expects success, and a page stuck on a loading state.
Print them in the test output so they become evidence.

For `wrong_input` and `not_allowed` flows, the pass condition is that the
user is stopped **and told why in words**, and that nothing wrong was
saved. A silent nothing is a failure. A 500 is a failure.

For flows whose surface is tagged `intent` (promised, not found), still
write the test from the intent. It will fail. That is how a missing feature
becomes visible instead of forgotten.

## Evidence from the test

Have each test save a screenshot of the final state, and of the page at the
moment of failure, to the folder in the `UF_EVIDENCE_DIR` environment
variable when it is set (one subfolder per flow id). Print the values it
observed, so the output alone shows what happened.

## Order of work

P0 flows first, then P1, then P2, one flow at a time. After writing each
test, run it once on its own to make sure it runs to a real result. A test
that fails because the product is broken is a finished test. A test that
fails because of its own mistake (wrong selector, bad setup) is not: fix
the test.

Do not record `pass` or `fail` in the registry in this phase. That is
`uf-evaluate`'s job, in a clean run with evidence.

When every flow has a test file or is `blocked` with a reason, run
`python3 .userflow/bin/uf-check.py --stage test` and fix every error.
