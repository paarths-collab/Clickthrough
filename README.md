# User-flow QA skill pack

Skill files and small helpers that make an AI agent check a product the way
a user uses it, instead of reviewing code. The agent maps what a user can
touch, lists every user flow (including every route to the same goal),
tests each flow against the real running app, and reports per flow with
evidence. Every run is recorded so it can be studied later.

## Contents

| Path | What it is |
|---|---|
| `skills/` | `uf-run` (entry point) and the five phases: `uf-preflight`, `uf-discover`, `uf-flows`, `uf-test`, `uf-evaluate`. |
| `templates/` | Shared rules (`guide.md`), the flow registry (`flows.yaml`), report, decision log, tool-gaps log, CLAUDE.md/AGENTS.md rules. |
| `scripts/` | `new-run.sh` (start a recorded run), `collect-run.sh` (copy the Claude Code or Codex session log), `uf-check.py` (registry validator and verdict). |
| `install.sh` | `./install.sh claude|codex|both <project>` |
| `experiment/` | Before/after protocol, scorecard, answer key for the sample app. |
| `sample-app/` | Tasklet, a small app with ten planted user-flow bugs. Its unit tests pass. |

## Quick start

```bash
./install.sh claude /path/to/project
```

Then open a new agent session in that project (not the one that built it)
and ask: "Is this project ready for real users? Use uf-run." Add `auto` to
run without stopping for review.

Requirements: Node 22.13+ for the sample app, Python 3 with PyYAML for
`uf-check.py`, and Playwright (or the project's own end-to-end tool) for the
agent to drive a browser.

See `experiment/protocol.md` for the before/after test.
