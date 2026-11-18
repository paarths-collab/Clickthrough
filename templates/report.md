# User-flow report

- Run: <run-id>
- Commit: <sha> (<clean | uncommitted changes>)
- Evaluator: <harness, model>
- Independent of the builder: <yes | no - explain>
- Mode: <review | auto | recheck>
- Areas covered: <all | list>   Areas not covered: <none | list>

## In plain words

<Five lines at most, for someone who will not read the rest: can people
use it; the worst things they will hit; how much was checked ("tested X
of Y flows"); what you need from the human to check the rest. No jargon,
no file names.>

## Verdict: <READY | NOT READY | CANNOT TELL>

<Two or three sentences in plain words: can a real user use this, and what
is the worst thing they will hit.>

READY needs every P0 flow passing with evidence. CANNOT TELL means the
product could not be run or P0 flows are unverified.

## Is the software alive

| Check | Result | Note |
|---|---|---|
| Install | | |
| Build / typecheck | | |
| Existing tests | | |
| Boot with seed data | | |
| Each service responds | | |
| Testing tools work | | |

## Goals

One row per goal, one line per route. A goal works only if every route works.

| Goal | Route | Flow | Priority | Status |
|---|---|---|---|---|
| | | | | |

Totals: P0 <pass>/<total>, P1 <pass>/<total>, P2 <pass>/<total>,
unverified <n>, blocked <n>.

## Findings

Worst first. Each one is written so the builder can act on it.

### <n>. <what the user experiences> [<CLASS>] [<P0|P1|P2>]
- Flow: <id and title>
- User did: <steps, briefly>
- Expected: <what the intent says>
- Got: <what happened>
- Breaks at: <step and layer, and the cause if you found it>
- Evidence: <paths>

## Security checklist (uf-security)

Every check, with how it was done. "Not done" needs a reason.

| # | Check | Result | How known (ran / traced / not done) | Flows or finding |
|---|---|---|---|---|
| 1 | Read without permission (ids, other tenant) | | | |
| 2 | Act above your role | | | |
| 3 | Mass assignment | | | |
| 4 | What keys and agents can do that needs a human | | | |
| 5 | Prompt injection to action | | | |
| 6 | Destructive and control-changing actions are audited | | | |
| 7 | Egress channels (webhooks, exports, integrations) | | | |
| 8 | SSRF | | | |
| 9 | Leaks through side doors (raw API, errors, emails, exports) | | | |
| 10 | Injection | | | |
| 11 | Crash on bad input | | | |
| 12 | Sessions (logout, links once, cookies, CSRF, removal) | | | |
| 13 | Brute force and rate limits | | | |
| 14 | Secrets | | | |
| 15 | Privacy export and erase complete | | | |
| 16 | Retention runs; legal pages exist | | | |
| 17 | Dependencies | | | |

## Coverage

| Area | Flows listed | Tested | Pass | Fail | Likely broken | Blocked |
|---|---|---|---|---|---|---|
| | | | | | | |

## Navigation

| Nav item | Opens | Result |
|---|---|---|
| | | |

Pages with no way in: <list or none>
Promised but not found: <list or none>

## Errors seen along the way

Console errors, failed network calls and server log errors seen during
flows, including flows that passed.

| Where | Error | Flow |
|---|---|---|
| | | |

## Seen on the walk, not counted as failures

<Things a user would find confusing or awkward that broke no flow: no
confirmation, no undo, unlabelled fields. One line each, or "none".>

## Likely broken (traced in code, not run)

Flows that could not be run, where a trace through the code shows a break.
Worst first. Not confirmed: each needs one real run.

| Flow | What the user would see | Where it breaks | Confidence | What would confirm it |
|---|---|---|---|---|
| | | | | |

## What a tester needs to run this for real

<The filled tester kit (`.userflow/templates/tester-kit.md`): only the
items this product needs, each with the flows it unlocks. Exactly enough
for the next run to test the blocked flows.>

## Where flows ran

| Target | URL or how started | Data rule | Flows run |
|---|---|---|---|
| Code | | read only | |
| Local copy | | test data | |
| Staging | | human's test accounts and tenants | |
| Production | | read only | |

## Not verified

| Flow or surface | Why | What would be needed |
|---|---|---|
| | | |

## Stubs and limits

<Third-party services stubbed, things this run could not judge.>

- Flaky flows (different result on rerun): <list or none>
- Test defects found and fixed during this run: <list or none>
- Test tooling added to the project: <packages and files, or none>
