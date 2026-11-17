# User-flow report

- Run: <run-id>
- Commit: <sha> (<clean | uncommitted changes>)
- Evaluator: <harness, model>
- Independent of the builder: <yes | no - explain>
- Mode: <review | auto | recheck>
- Areas covered: <all | list>   Areas not covered: <none | list>

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

## Not verified

| Flow or surface | Why | What would be needed |
|---|---|---|
| | | |

## Stubs and limits

<Third-party services stubbed, things this run could not judge.>
