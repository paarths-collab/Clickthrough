# User-flow QA: shared rules

Every `uf-*` skill follows this file. Read it once at the start of a session.

## The stance

You are checking this product as a person who uses it, not as the developer
who wrote it. A developer asks "is this code correct?". A user asks "can I
get my thing done?". Most of what breaks a product for users is invisible in
any single file: the page sends one field name and the server expects
another, the save works but the list never refreshes, the feature exists but
no menu leads to it. Reading code will not show you these. Using the product
will.

So the unit of work is a **flow**: one user, one goal, from where they start
to the result they can see and that is still there when they come back.

## Hard rules

1. **Use the real running product.** Start it, then act on it through the
   door a user uses: the browser for a web app, HTTP for a public API, an MCP
   client for an MCP server, the command line for a CLI, the installed
   package for a library, the app's UI for a desktop or mobile app, the
   device or an emulator for firmware. These skills use web words (page,
   click, menu, refresh); `uf-patterns` has a table that translates them
   for any kind of product. Choose your own tools for that door.
2. **No mocks of this product.** Never replace our own frontend, backend,
   database or MCP server with a fake. A third-party service (payments,
   email, SMS) may be stubbed at the network edge, and every stub is listed
   in the report.
3. **Start where the user starts.** A flow begins at the entry point (login
   page, home page, first command) and reaches each screen by clicking what
   a user would click. Do not type a deep URL to skip steps and do not call
   the API to do a step the user does in the UI. Setting up *preconditions*
   (a seeded account, existing data) by script is fine. One exception: when
   typing the address *is* what is being tested (a `not_allowed` flow where
   a user changes an id in the address, or a page with `reach: none` checked
   on its own), type it, and say so in a comment at the top of the test.
4. **Do not judge by reading source.** Source code tells you where to look
   and helps explain a failure after you have seen it. It never decides
   whether something works. If reading code makes you suspect a bug, do not
   report it from the code: write a flow a real user could plausibly do
   that would hit it, and let the run decide.
5. **Evidence or it did not happen.** A flow is `pass` only with evidence
   from a real run. Without evidence the status is `unverified`.
6. **Never bend a test to make it pass.** If a test fails, either the
   product is broken or the test is wrong. Say which. Do not loosen the
   check, add retries to hide it, or skip it.
7. **Do not change the product.** In these skills you report. You do not
   edit application code, migrations or config to make a flow pass. Adding
   a test tool the project lacks (for example Playwright as a dev
   dependency, with its config inside `userflow-tests/`) is not a product
   change; list what you added in the report.
8. **If the product cannot start, stop.** Report the blocker. Do not carry
   on with imagined results.
9. **Never touch production or shared data.** Before any flow writes data,
   find out where the database, storage, email and payment settings
   point. Run only against a local or test instance. Never reset, seed,
   migrate or write test data on a remote database unless the human said
   it is a disposable test instance. If you cannot tell, stop and report
   that as the blocker (verdict CANNOT TELL).

## Files

| Path | What it is |
|---|---|
| `.userflow/flows.yaml` | The registry: product, how to run it, personas, surfaces, goals, flows, status. Single source of truth. Committed. |
| `.userflow/guide.md` | This file. |
| `.userflow/tool-gaps.md` | Things you wanted to do and could not. Committed. |
| `.userflow/bin/` | Helper scripts: `new-run.sh`, `collect-run.sh`, `uf-check.py`. |
| `.userflow/runs/<run-id>/` | One folder per run: `run.json`, `decisions.md`, `report.md`, `evidence/`, `raw/`. Never committed. |
| `userflow-tests/` | One test file per flow. Committed. |

## Recording a run

Recording is part of the job, not paperwork. These records are studied later
to work out which steps a cheaper model can follow.

1. At the start of a session run `.userflow/bin/new-run.sh` once. It creates
   the run folder and prints its path. Pass what you know:
   `--harness claude|codex --model <id> --mode review|auto`.
   Use that one folder for the whole session.
2. Append to `decisions.md` in that folder **as you go**, one entry per
   meaningful step, written when it happens and not reconstructed at the
   end. Format:

   ```
   ## <n>. <phase> - <short title>
   - Trying to: <what you wanted to find out or do>
   - Checked: <what you looked at or ran>
   - Used: <tools and exact commands>
   - Saw: <what came back, briefly>
   - Judgment: <any choice you made and why; "none" if mechanical>
   - Could not: <anything you were unable to do, and why; "nothing" if none>
   ```

   The `Judgment` line matters most. Whenever you choose between options,
   guess, skip something, or decide something is "probably fine", write it
   down.
3. Every time you want to do something and cannot (no browser tool, no
   database access, cannot receive the email, no test account), add an entry
   to `.userflow/tool-gaps.md`. Then mark whatever depended on it
   `unverified` or `blocked`. A gap is useful information, not a failure of
   yours.
4. At the end run `.userflow/bin/collect-run.sh`. It copies the harness's
   own session log into `raw/`.

## Statuses

| Status | Meaning |
|---|---|
| `untested` | No test has been run for this flow. |
| `pass` | The flow was run against the real product and every check held. Evidence is linked. |
| `fail` | The flow was run and the user could not finish, or finished with a wrong result. Needs a `failure_class` and a one-line `finding`. |
| `unverified` | You believe it may work but have no evidence from a real run. |
| `blocked` | Could not be run. Needs `failure_class: ENV_BLOCKED` or `TOOL_GAP`. |

## Failure classes

| Class | Use it when |
|---|---|
| `FLOW_BROKEN` | The user cannot finish, or the result is wrong or does not last, and nothing crashed. |
| `SOFTWARE_BUG` | A crash, an exception, a 5xx, a console error, a page stuck loading. |
| `INTEGRATION` | Two layers disagree: field names, routes, data shapes, auth passed one way and expected another. Use this when you have seen the mismatch. |
| `MISSING_FEATURE` | The intent says the user can do it and the product has no working way to. |
| `ENV_BLOCKED` | The environment stopped you: service down, missing secret, no network. |
| `TEST_DEFECT` | The test was wrong, not the product. Fix the test and rerun. |
| `TOOL_GAP` | You had no tool to perform or check the step. |

Pick the class from what the user experienced first. Add the cause in the
finding if you found it: "Tick does not survive a refresh (page calls a
route the server does not have)".

## Evidence

Evidence lives in `.userflow/runs/<run-id>/evidence/<flow-id>/`. Good
evidence for one flow is: the test's output, a screenshot of the final state
(`final.png`) and of the failure, if any (`failure.png`), any failed network
calls or console errors, and the result of checking what was saved.

Later passes get their own folders so nothing is overwritten:
`evidence/rerun/<flow-id>/` for the solo rerun of a failure and
`evidence/walk/<flow-id>/` for the hand walk. In the registry, write
evidence paths relative to the project root; `uf-check.py` checks that they
exist.

The registry, `tool-gaps.md` and `userflow-tests/` are meant to be
committed, but committing is the human's call. Leave them in the working
tree and list what you added or changed.

Check what was saved in the strongest way you have:
1. Read the database directly (read-only).
2. If you cannot, leave the product and come back: log out, start a fresh
   browser session, log in, and look. Note that this is weaker and log a
   tool gap.

## Large products

Do not try to hold the whole product in one session. Split it into **areas**
(billing, onboarding, admin, and so on), list them under `areas:` in the
registry, and finish one area at a time. The registry is your memory: before
doing anything, read it and continue from what is not done. Say in the
report which areas were covered and which were not.
