---
name: uf-env
description: Build a disposable, local, test-only copy of the whole product - every service, seeded data, a test account per role, an inbox for email - started and reset with one command, and committed so every later audit and CI run reuses it. Use when the product cannot be started for testing, when uf-preflight is blocked, or when asked to set up a test environment.
---

# A test copy of the product, once, for every run after

Every audit needs the product running with data and accounts. If each run
rebuilds that by hand, every run is slow and different. Build it once,
commit it, and reuse it.

## Rules

- **Local and disposable only.** Every database, store, queue and inbox
  runs on this machine with test data. Never point it at a remote or
  production service (guide rule 9). No real secrets in committed files.
- **Real parts where you can, stand-ins only where you must.** Run this
  product's own code and schema for real. A service that is not in the
  repo (an identity hub, a payment provider, a third-party API) gets a
  stand-in at the network edge, built from what this product actually
  calls. List every stand-in: results through a stand-in are not proof the
  real service works.
- **Respect the project's rules.** If containers are not allowed, use
  native packages (system package manager, nix, language toolchains).

## What to build, in `userflow-tests/stack/`

| File | Does |
|---|---|
| `up` | Start everything from nothing; wait until each part answers; print the URLs. |
| `seed` | Load the test data: at least one account per role, two tenants if the product has tenants, an empty account for first-visit flows. |
| `reset` | Back to the seeded state in seconds, between flows. |
| `down` | Stop everything and remove what `up` created. |
| `env.test` | The environment variables the product needs, with local values only. |
| `accounts.md` | Each test account: role, tenant, how to sign in. |
| `README.md` | What runs, how, every stand-in and what it does not cover, and what a run on a fresh machine needs installed. |

Plus, when the product sends email or messages: a local mail catcher with
a way for tests to read the inbox. When the product insists on https or a
real domain (security policy, secure cookies): a local https front.

## Steps

1. **List what the product needs to run** from the README, config, env
   files, `uf-inventory.py` output (env vars, outbound calls, jobs) and
   the code that connects to each service.
2. **For each part, choose:** run it for real locally, or a stand-in.
   Write the choice and the reason in `decisions.md`.
3. **Build `up`, `seed`, `reset`, `down`.** Apply the product's real
   migrations or schema; never hand-write a schema the repo already has.
4. **Prove it from scratch:** `down`, then `up`, `seed`; every part
   answers; sign in as each role; send one email and read it from the
   inbox; `reset` and check the data is back; `down` leaves nothing
   running.
5. **Record it:** fill `run.boot`, `run.seed`, `run.reset`, `run.stop` in
   `.userflow/flows.yaml`, and add to `.userflow/tool-gaps.md` anything
   the stack still cannot do.
6. **Offer CI.** The template `.userflow/templates/ci-github.yml` runs the
   stack and the flow tests on every pull request. Adding a CI workflow
   changes the project: ask the human first.

If a part cannot run locally at all, say exactly what is missing (a
binary, a licence, a service only the human can grant) and carry on with
the parts that do; flows that depend on it are traced in code.
