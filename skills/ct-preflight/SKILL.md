---
name: ct-preflight
description: Phase 1 of Clickthrough. Check the software itself is alive before testing any user flow - install, build, typecheck, existing tests, boot the whole stack with seed data, check every service responds, and check the testing tools work. Use at the start of ct-run, or on its own when asked whether a project builds, starts or runs.
---

# ct-preflight: is the software alive?

Before asking whether a user can finish a task, find out whether the
software starts at all. Broken installs, missing migrations and services
that do not come up are the first things a real user hits, and they stop
every later check.

Follow `.clickthrough/guide.md`. Log each step in `decisions.md`.

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
   database, workers, MCP servers. If `clickthrough-tests/stack/` exists, use
   its `up` and `seed`. If the product will not start and nothing like it
   exists, load `ct-env` and build one before giving up. If there is no
   single command that does it, write down the sequence that works and put
   it in the registry.
6. **Check each part really responds** through the door a user uses (see
   the table in `ct-patterns`). For example: the entry page loads in a real
   browser without errors; an endpoint answers; the CLI's `--help` and one
   real command run; the installed library imports and runs its README
   example; the app opens its first screen; the MCP server lists its tools;
   every worker process is up. Read the logs after start. Errors at
   startup are findings.
6b. **An inbox, if the product sends anything.** If the code map lists
   email, SMS or auth links, or the intent mentions an email (invites,
   sign-up confirmation, password reset, notifications), a local mail
   catcher the tests can read is required, not optional. Without it,
   invite, sign-up and reset flows cannot be checked at all. Build it
   (`ct-env`) before moving on, or record exactly why it is impossible.
7. **Check where data goes, then find or make a reset.** First read the
   environment and config: which database, storage, email and payment
   services will the flows write to? Local or a test instance: carry on.
   Production, shared, or unknown: stop and report it (guide rule 9).
   Flows change data, and a flow run on another
   flow's leftovers fails for the wrong reason. Find the command that puts
   data back to a known state (re-seed, test database, transaction
   rollback). If there is none, say so, log a tool gap, and plan for each
   test to create its own fresh user and data.
8. **Check your own tools.** You need a way to act through the user's door,
   to see what the user sees (screen, output, response), to read saved data
   without writing, and to read logs. Pick tools that fit this product and
   prove each one works against it, not just that it is installed. Prefer
   the project's own language and test runner when they can do the job.
   Each one you lack goes in `.clickthrough/tool-gaps.md` with what it will stop
   you from checking. Adding test tooling (kept inside `clickthrough-tests/`)
   is not a product change.
9. **Find the targets and ask for what is missing.** Look for a staging or
   preview deployment (README, CI and deploy config, environment variables,
   `CT_STAGING_URL`) and for anything the human already provided
   (`CT_*` environment variables). For each target, check it answers, the
   test accounts sign in, and the human has said its data is test data;
   record it under `targets:` in the registry. Then list what flows will
   need and you do not have (test accounts per role, an inbox the tests
   can read, sandbox services, schema not in the repo, permission to
   download tools) and ask for it with `.clickthrough/templates/tester-kit.md`,
   as the guide's "Asking the human" section says. Only ask for what this
   product actually needs.

## Write down

- Fill the `run:` block in `.clickthrough/flows.yaml` with the commands that
  actually worked, the base URL, each service with how you checked it, and
  any stubs.
- Start `report.md` in the run folder from `.clickthrough/templates/report.md`
  and fill the "Is the software alive" table.

## If it will not start

Do not swap in mocks. Spend a reasonable effort on obvious environment
causes (wrong directory, a missing documented step, a port in use). If the
cause is in the product, or needs something only the human has:

- Record it as a finding (class `ENV_BLOCKED` or `SOFTWARE_BUG`) with the
  exact command and error.
- Write down exactly what a tester would need to run every flow for real:
  services, test accounts per role, seed data, environment variables, an
  inbox for email. This list is one of the most useful things you produce.
- Run whatever parts do start (public pages, the API's front door, the
  CLI's help) and keep them in play.
- Carry on with discovery and flows. Map from the code what you cannot
  open. In `ct-evaluate`, flows you cannot run are traced in code (guide,
  Trace mode). The verdict stays **CANNOT TELL**.

"The app does not start from its own instructions" is one of the most
valuable findings there is. Report it plainly.
