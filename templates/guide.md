# Clickthrough: shared rules

Every `ct-*` skill follows this file. Read it once at the start of a session.

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
   click, menu, refresh); `ct-patterns` has a table that translates them
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
4. **Running beats reading.** When you can run a flow, the run decides,
   not the code. If reading code makes you suspect a bug, write a flow a
   real user could plausibly do that would hit it, and let the run decide.
   When a flow cannot be run (the product will not start, no test account,
   no inbox), do not stop there: trace it through the code (see "Trace
   mode" below) and report what you find as `likely_broken`, marked as
   traced, not run.
5. **Evidence or it did not happen.** A flow is `pass` only with evidence
   from a real run. Without evidence the status is `unverified`. A trace
   through the code is never a pass.
6. **Never bend a test to make it pass.** If a test fails, either the
   product is broken or the test is wrong. Say which. Do not loosen the
   check, add retries to hide it, or skip it.
7. **Do not change the product.** In these skills you report. You do not
   edit application code, migrations or config to make a flow pass. Adding
   a test tool the project lacks (for example Playwright as a dev
   dependency, with its config inside `clickthrough-tests/`) is not a product
   change; list what you added in the report.
8. **If the product cannot start, do not imagine results.** Report the
   blocker and exactly what a tester would need to run it, then switch to
   trace mode for the flows you cannot run.
9. **Never touch production or shared data.** Before any flow writes data,
   find out where the database, storage, email and payment settings
   point. Each target has its own rule (see "Targets" below): local copy,
   anything goes; staging, only with the accounts and tenants the human
   named, after they said it is test data; production, read-only checks
   only, and only if the human allowed them. Never reset, seed or migrate
   a remote database. If you cannot tell which target you are on, stop
   and report that as the blocker (verdict CANNOT TELL).

## Files

| Path | What it is |
|---|---|
| `.clickthrough/flows.yaml` | The registry: product, how to run it, personas, surfaces, goals, flows, status. Single source of truth. May be committed when authorized. |
| `.clickthrough/guide.md` | This file. |
| `.clickthrough/tool-gaps.md` | Things you wanted to do and could not. May be committed when authorized. |
| `.clickthrough/bin/` | Helper scripts: `new-run.sh`, `collect-run.sh`, `ct-check.py`, `ct-inventory.py` (code dissection), `ct-double.py` (stand-in for outside services that records what the product sends). |
| `.clickthrough/runs/<run-id>/` | One folder per run: `run.json`, `decisions.md`, `report.md`, `evidence/`, `raw/`. Never committed. |
| `.clickthrough/bugs.yaml` | The bug register: every bug found, once, across all runs, with the flows it breaks and its status. May be committed when authorized. |
| `.clickthrough/proof/<bug-id>/` | Private, Git-ignored bug recordings. Share only reviewed, sanitized derivatives. |
| `.clickthrough/inventory.json` | The code map from `ct-inventory.py`: every entry point; the registry must cover all of it. May be committed when authorized. |
| `.clickthrough/batches.md`, `.clickthrough/next.md` | Batch plan and "continue here" note for long audits (`ct-parallel`). May be committed when authorized. |
| `.clickthrough/cases/<surface-id>.yaml` | Component card and every case for one component (`ct-cases`). May be committed when authorized. |
| `clickthrough-tests/` | One test file per flow, plus `<surface-id>.cases.*` table tests. May be committed when authorized. |

## Targets: code, local copy, staging, production

Test each flow where it can be tested for real and safely:

| Target | Use it for | Rule |
|---|---|---|
| Code | finding where a flow breaks; flows nothing can run | read only |
| Local copy (`ct-env`) | destructive, security and permission flows; resets | anything, test data only |
| Staging / preview | flows that need real services: sign-in, email, files, messaging, AI, integrations | only the human's test accounts and tenants; create and delete only inside them; no resets; clean up |
| Production | read-only smoke: pages load, links work, logged-out API calls are refused | only if the human allowed it; nothing created, changed or deleted; slow request rate |

Destructive and attack flows run on the local copy only, never on staging
or production. Record in each flow where it was meant to run (`target`)
and where it did run (`last_run.target`). A flow is `blocked` only when it
can run on none of them.

## Asking the human for what is missing

When something the audit needs is missing (a staging URL, a test inbox,
test accounts, sandbox services, a schema that is not in the repo,
permission to download tools), fill `.clickthrough/templates/tester-kit.md`
with only the items that apply and say which flows each unlocks. In review
mode, ask before testing the flows that need it. In auto mode, carry on
with what is possible and put the kit at the top of the report and in
`.clickthrough/next.md`. Secrets go into environment variables, never into the
chat. Never ask for production write access or real people's mailboxes.

## Shared test state

During a run, never delete or overwrite what other tests or helpers depend
on: signed-in session files, seeded accounts, the test stack's data
folders, shared result folders. Clean up only what your own flow created,
inside your own tenant. If something shared looks broken, recreate it
deliberately and rerun everything that used it.

## Usage budget

Plan names differ between platforms and change often, so the setting is a
size, `CT_BUDGET`: `small`, `medium`, `large` or `metered`. Go by the
allowance of the plan or seat, not its name: Team and Enterprise depend
on the seat type. This table was right when written; prices and names
change, so when unsure, ask the human or look at the platform's own usage
screen.

| Budget | Claude (Claude Code) | ChatGPT (Codex) | Cursor |
|---|---|---|---|
| `small` | Free, Pro, Team Standard seat, Enterprise standard seat | Free, Go, Plus, Business, Enterprise/Edu without flexible pricing | Free, Plus, Premium |
| `medium` | Max, Team Premium seat, Enterprise mid seat | Pro $100 | Super, lower Teams seats |
| `large` | Ultra, Enterprise top seat | Pro $200 and $500 | Ultra, top Teams seats |
| `metered` | API key, Enterprise usage-based | API key, Enterprise/Edu flexible credits | third-party models billed at API prices |

Other platforms: pick the row whose allowance matches, or ask.

## Every finding is an evidence record

Each finding, pass or fail, says:
- **claim:** what works or what breaks, in the user's words;
- **how known:** `ran` (seen in the running product), `traced` (followed
  through the code, not run) or `read` (spotted in code, not followed);
- **evidence:** screenshot, output, request and response, file and line;
- **covered and not covered:** which routes, roles and data it applies to;
- **unknowns:** what would change the conclusion, and what would confirm it.

Never upgrade the "how known" in a summary: a traced finding stays traced.

## Recording a run

Recording is part of the job, not paperwork. These records are studied later
to work out which steps a cheaper model can follow.

1. At the start of a session run `.clickthrough/bin/new-run.sh` once. It creates
   the run folder and prints its path. Pass what you know:
   `--harness claude|codex|cursor|other --model <id> --mode review|auto`.
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
   to `.clickthrough/tool-gaps.md`. Then mark whatever depended on it
   `unverified` or `blocked`. A gap is useful information, not a failure of
   yours.
4. At the end run `.clickthrough/bin/collect-run.sh`. It copies the harness's
   own session log into `raw/`.

## Statuses

| Status | Meaning |
|---|---|
| `untested` | No test has been run for this flow. |
| `pass` | The flow was run against the real product and every check held. Evidence is linked. |
| `fail` | The flow was run and the user could not finish, or finished with a wrong result. Needs a `failure_class` and a one-line `finding`. |
| `unverified` | You believe it may work but have no evidence from a real run. |
| `blocked` | Could not be run. Needs `failure_class: ENV_BLOCKED` or `TOOL_GAP`. After a trace that found no break, add `trace: "no break found in code"`. |
| `likely_broken` | Could not be run, and a trace through the code shows where it breaks. Needs `failure_class`, `finding` (what the user would see, and the file and line where it breaks) and `confidence: high`, `medium` or `low`. Never counts as a pass or as a confirmed fail. |

## Trace mode

For a flow you cannot run, follow it through the code the way it would
run, one hop at a time:

```
user action → request → handler → saved data → whoever reads it next → what the user sees
```

At each hop, check the patterns in `ct-patterns` that apply: names that
differ across a boundary, a route nobody calls or that does not exist, an
error swallowed, a check on write but not on read, a side effect on one
route only, a setting nothing reads, a session or token handed over in a
form the next step cannot use. Read the actual code on both sides of each
hop; do not assume a helper does what its name says.

Write each break as: what the user would do and see, the file and line
where it breaks, and how sure you are (`high`: you read both sides and the
mismatch is certain; `medium`: likely, depends on config or a library's
behaviour; `low`: suspicion). Then say what would confirm it in one real
run. P0 flows first.

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

Evidence lives in `.clickthrough/runs/<run-id>/evidence/<flow-id>/`. Good
evidence for one flow is: the test's output, a screenshot of the final state
(`final.png`) and of the failure, if any (`failure.png`), any failed network
calls or console errors, and the result of checking what was saved.

Later passes get their own folders so nothing is overwritten:
`evidence/rerun/<flow-id>/` for the solo rerun of a failure and
`evidence/walk/<flow-id>/` for the hand walk. In the registry, write
evidence paths relative to the project root; `ct-check.py` validates execution receipts, product/test identity, and artifact hashes. A filename alone is insufficient.

The registry, `tool-gaps.md` and `clickthrough-tests/` are meant to be
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

## Enforced release and evidence policy

The installed `templates/runner.md` documents the runner and migration protocol.
Use `ct.py run` for executions and `ct-check.py --require-ready --json` for the
release gate. Every pass/fail needs `last_run.result`: a receipt tied to the run,
current product content, test hash, observed assertions and hashed artifacts.
Independent review still decides whether those assertions actually test the claim.

Critical/high open or wont-fix confirmed bugs block READY regardless of priority;
unconfirmed serious findings mean CANNOT TELL, likely NOT READY. Every catalogued
flow must run. Blocked and traced flows never count as executed. P0 case cards
are structured YAML, and coverage.yaml records every applicable quality dimension.
Missing/stale evidence, unreconciled inventory or unresolved coverage prevents READY.

Do not commit or publish unless the user requested it. Checkpoint by writing files
atomically and saving next.md; a checkpoint does not imply a Git commit. A stated
spending/time cap always takes precedence over the number of remaining flows.
At the cap, preserve progress and report the remaining work without claiming full
coverage. Never infer spending permission from a plan name.
