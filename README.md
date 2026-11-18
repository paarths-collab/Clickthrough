# User-flow QA skill pack

Skill files and small helpers that make an AI agent check a product the way
a user uses it, instead of reviewing code. The agent maps what a user can
touch, lists every user flow (including every route to the same goal),
tests each flow against the real running app, and reports per flow with
evidence. Every run is recorded so it can be studied later.

Works for any language (Python, TypeScript, Rust, Go, Java, C, C++, ...)
and any kind of product: web app, API, CLI, library, desktop or mobile app,
firmware, data pipeline.

## Start here (3 steps, works in any agent, local or cloud)

**1. Install into your project.** Paste this to the agent in a session on
your project (Claude Code, Codex, any cloud session):

> Run this from the project root and show me the output:
> `git clone --depth 1 https://github.com/paarths-collab/user.git /tmp/ufqa && bash /tmp/ufqa/install.sh both .`
> Then commit the files it lists under "git add" and push.

`both` covers Claude Code, Codex and Cursor (Cursor reads `.agents/skills/` and `AGENTS.md`). Use `claude`, `codex` or `cursor` if you only use one. On
your own machine you can run the same two commands yourself.

**2. Get it onto your default branch.** Merge the commit or PR into `main`.
Sessions only see the skills on the branch they start from.

**3. Start a new session** (skills load when a session starts), one that did
not build the product, and ask:

```
Is this project ready for real users? Use uf-run. auto
```

For a big product add: `one area at a time, P0 first`.

What the installer changes in your repo: adds the skills
(`.claude/skills/`, `.agents/skills/`), a `.userflow/` folder (registry,
guide, helper scripts), a rules block at the end of `CLAUDE.md` /
`AGENTS.md`, and `.gitignore` lines for run logs. If your `.gitignore`
hides `.claude/` or `.agents/`, it re-includes only the skills folder. It
never deletes anything and is safe to run again.

What changes in how agents work: building sessions run `uf-ready-check`
before they say "done", and nobody calls the product "ready" without a
user-flow report.

## Contents

| Path | What it is |
|---|---|
| `skills/` | `uf-run` (full audit, entry point) and its phases: `uf-preflight`, `uf-discover`, `uf-flows`, `uf-test`, `uf-evaluate`. `uf-patterns`: what breaks for users and how to see it. `uf-catalog`: list every flow in the whole product first (every page, endpoint, tool and job from the code map), so the report can say "tested X of Y". `uf-parallel`: test a long list in batches, with helper agents in parallel and separate test data, and carry on in a new session until done. `uf-cases`: go deep on one component or one whole workflow - understand it, list every case and path a user can produce, test them. `uf-security`: what another tenant, a lower role, an API key or an AI agent can do that they must not. `uf-env`: a disposable local test copy of the product, built once and reused. `uf-fix`: fix findings one at a time, each proven by a real run. `uf-score`: score an audit against known issues. `uf-ready-check`: the builder's check before saying "done". `uf-setup`: installs into a project. |
| `templates/` | Shared rules (`guide.md`), the flow registry (`flows.yaml`), report, decision log, tool-gaps log, CLAUDE.md/AGENTS.md rules. |
| `scripts/` | `uf-inventory.py` (dissects the code into pages, endpoints, CLI commands, agent tools, jobs, webhooks, outbound calls, emails, destructive writes, env vars), `uf-check.py` (registry validator and verdict), `new-run.sh`, `collect-run.sh`. |
| `install.sh` | `./install.sh claude|codex|cursor|both|plugin <project>` |
| `experiment/` | Before/after protocol, scorecard, answer keys for the sample apps, a known-issues template. |
| `evals/` | Eval cases for the skills themselves: `claude plugin eval .` runs each with and without the plugin. |
| `templates/ci-github.yml` | GitHub Actions workflow that runs the test stack and every flow test on each pull request. |
| `sample-app/` | Tasklet, a small app with ten planted user-flow bugs. Its unit tests pass. Good for a first smoke run. |
| `sample-app-hard/` | Helpline, a support inbox with three roles, a web app, a background worker, an MCP server and 25 planted bugs in four tiers of difficulty. Its tests pass. Use this one for before/after comparisons. |

## Other ways to install

**Claude Code plugin**, where your environment has plugins (some cloud
environments and organisations turn them off; then use "Start here"):

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
| Every test and edge case of a component or a whole workflow | `uf-cases` | "List and test every case for the invite dialog and the whole invite workflow. Use uf-cases." (also part of every `uf-run` for P0) |
| Continue a long audit | `uf-parallel` | New session: "Continue the user-flow audit. Use uf-run continue." |
| Security review | `uf-security` | "Security audit. Use uf-security." (also part of every `uf-run`) |
| Fix what an audit found | `uf-fix` | "Fix the findings. Use uf-fix." Then a **new** session: "Use uf-run recheck." |
| App can't be started for testing | `uf-env` | "Build a test environment. Use uf-env." (preflight also uses it when the app won't start) |
| Score an audit | `uf-score` | In a **different** session: "Score this audit against my known issues. Use uf-score." |

Requirements: bash and git to install; Python 3 with PyYAML for
`uf-check.py`. The agent picks its own tools to drive your product
(browser automation, an HTTP client, the command line, ...). Node 22.13+
only for the sample apps.

See `experiment/protocol.md` for the before/after test.
