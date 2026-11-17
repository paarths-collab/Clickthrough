# User-flow QA skill pack

Skill files and small helpers that make an AI agent check a product the way
a user uses it, instead of reviewing code. The agent maps what a user can
touch, lists every user flow (including every route to the same goal),
tests each flow against the real running app, and reports per flow with
evidence. Every run is recorded so it can be studied later.

## Contents

| Path | What it is |
|---|---|
| `skills/` | `uf-run` (full evaluation, entry point) and its five phases: `uf-preflight`, `uf-discover`, `uf-flows`, `uf-test`, `uf-evaluate`. `uf-patterns`: what breaks for users between frontend, backend, database, jobs, email and MCP, and how to see each one. `uf-ready-check`: the short check the building session runs before it says "done". |
| `templates/` | Shared rules (`guide.md`), the flow registry (`flows.yaml`), report, decision log, tool-gaps log, CLAUDE.md/AGENTS.md rules. |
| `scripts/` | `new-run.sh` (start a recorded run), `collect-run.sh` (copy the Claude Code or Codex session log), `uf-check.py` (registry validator and verdict). |
| `install.sh` | `./install.sh claude|codex|both <project>` |
| `experiment/` | Before/after protocol, scorecard, answer key for the sample app. |
| `sample-app/` | Tasklet, a small app with ten planted user-flow bugs. Its unit tests pass. Good for a first smoke run. |
| `sample-app-hard/` | Helpline, a support inbox with three roles, a web app, a background worker, an MCP server and 25 planted bugs in four tiers of difficulty. Its tests pass. Use this one for before/after comparisons. |

## Install

**Claude Code plugin** (CLI, desktop or web). In a Claude Code session:

```
/plugin install user-flow-qa --marketplace paarths-collab/user
```

On older Claude Code, two steps: `/plugin marketplace add paarths-collab/user`,
then `/plugin install user-flow-qa@user-flow-qa`. Then, in each project, say
"Set up user-flow QA" (the `uf-setup` skill creates `.userflow/` and the
rules, and can enable the plugin for everyone on the repo, cloud sessions
included).

**Into a project's repo** (Codex, or Claude Code without the plugin):

```bash
./install.sh both /path/to/project
```

Modes: `claude`, `codex`, `both` copy the skills into the repo; `plugin`
only adds `.claude/settings.json` entries that make Claude Code load the
plugin. Commit the result so cloud sessions get it.

Three ways to use it:

| When | Skill | Ask |
|---|---|---|
| While building, before saying "done" | `uf-ready-check` | Installed rules make the builder run it. Or: "Check this with uf-ready-check." |
| Release check | `uf-run` | In a **new** session (not the one that built it): "Is this project ready for real users? Use uf-run." Add `auto` to run without stopping for review. |
| Any time you look for bugs | `uf-patterns` | "Find what is broken for users. Use uf-patterns." |

Requirements: Node 22.13+ for the sample app, Python 3 with PyYAML for
`uf-check.py`, and Playwright (or the project's own end-to-end tool) for the
agent to drive a browser.

See `experiment/protocol.md` for the before/after test.
