---
name: uf-preflight
description: Phase 1 of user-flow QA. Check the software itself is alive before testing any user flow - install, build, typecheck, existing tests, boot the whole stack with seed data, check every service responds, and check the testing tools work. Use at the start of uf-run, or on its own when asked whether a project builds, starts or runs.
---

# uf-preflight: is the software alive?

Before asking whether a user can finish a task, find out whether the
software starts at all. Broken installs, missing migrations and services
that do not come up are the first things a real user hits, and they stop
every later check.

Follow `.userflow/guide.md`. Log each step in `decisions.md`.

## Steps

Do them in order. Record the exact command and result for each.

1. **Find how it runs.** Read the README, package scripts, Makefile,
   compose files and CI config. Work out the commands for: install, build,
   typecheck or lint, existing tests, start everything, seed, reset, stop.
   If two documents disagree, try both and record which one is true.
2. **Install.** Run it. A failure here is a finding, not something to work
   around quietly.
3. **Build and typecheck**, if the project has them.
4. **Run the existing tests.** Record pass and fail counts. Remember what
   this does and does not tell you: these tests were written by the builder
   and may pass while the product is unusable.
5. **Boot the whole stack with seed data.** Every part: frontend, backend,
   database, workers, MCP servers. If there is no single command that does
   it, write down the sequence that works and put it in the registry.
6. **Check each service really responds.**
   - Frontend: the entry page loads in a real browser with no console
     errors, and is not a blank page.
   - API: a health or simple read endpoint answers.
   - Database: reachable, migrations applied, seed rows present.
   - MCP server: connects, and lists the tools it claims to have.
   - Workers and jobs: the process is up.
   Read the server logs after boot. Errors at startup are findings.
7. **Find or make a reset.** Flows change data, and a flow run on another
   flow's leftovers fails for the wrong reason. Find the command that puts
   data back to a known state (re-seed, test database, transaction
   rollback). If there is none, say so, log a tool gap, and plan for each
   test to create its own fresh user and data.
8. **Check your own tools.** Prove each one works against the running
   product, not just that it is installed:
   - a way to drive a browser (and take a screenshot),
   - a way to make HTTP calls,
   - a way to read the database without writing,
   - a way to call MCP tools, if the product has any,
   - a way to read server logs.
   Each one you lack goes in `.userflow/tool-gaps.md` with what it will stop
   you from checking.
9. **Note what users need that you may not have:** test accounts for each
   role, email or SMS you cannot receive, third-party logins, payment test
   keys. List them now so later phases can mark those flows `blocked`
   instead of guessing.

## Write down

- Fill the `run:` block in `.userflow/flows.yaml` with the commands that
  actually worked, the base URL, each service with how you checked it, and
  any stubs.
- Start `report.md` in the run folder from `.userflow/templates/report.md`
  and fill the "Is the software alive" table.

## If it will not start

Stop here. Do not continue to discovery on a product you cannot run, and do
not swap in mocks or "test what you can by reading". Spend a reasonable
effort on obvious environment causes (wrong directory, a missing documented
step, a port in use). If the cause is in the product, or needs something
only the human has, write the report with verdict **CANNOT TELL**, class
`ENV_BLOCKED` or `SOFTWARE_BUG`, the exact command and error, and what is
needed to get past it.

"The app does not start from its own instructions" is one of the most
valuable findings there is. Report it plainly.
