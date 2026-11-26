<div align="center">

# Clickthrough

**Your tests pass. Does the product actually work for the person using it?**

A skill pack that makes AI coding agents test your product the way a real user would:
every flow, on the real running app, with evidence.

Claude Code · Codex · Cursor &nbsp;|&nbsp; any language &nbsp;|&nbsp; web, API, CLI, mobile, desktop, firmware

</div>

---

## Why

Agents say "done" when the code looks right. Users find out it isn't.
**clickthrough** makes the agent stop reading code and start using the product:

1. **Map** everything a user can touch: pages, endpoints, commands, jobs.
2. **List** every flow, including every route to the same goal.
3. **Test** each flow against the running app, security included.
4. **Report** flow by flow, with proof: "tested 42 of 42, 3 broken, here's how".

## Quick start

**1. Install.** Ask your agent, from your project root:

```bash
git clone --depth 1 https://github.com/paarths-collab/Clickthrough.git /tmp/clickthrough && bash /tmp/clickthrough/install.sh both .
```

Commit what it adds and merge it into your default branch.
It never deletes anything and is safe to run again.

**2. Ask.** In a new session (not the one that built the product):

```
Is this project ready for real users? Use ct-run. auto
```

For a large product, do it in two steps, so you see the whole map before
any testing starts.

On a small usage plan (or if you don't say), the agent does this by itself:
it maps everything first, stops, and tells you how big the job is. Set
`CT_BUDGET` (`small`, `medium`, `large` or `metered`) in the session's
environment to tell it your budget; the guide has a table mapping Claude,
ChatGPT/Codex and Cursor plans and seats to these sizes. On `metered`
(pay per use) it asks for a spending cap first. Every bug it reports comes
with proof in `.clickthrough/proof/`: a video and trace of the failing flow,
or a request and response transcript.

*Step 1, discover everything* (stops when the map is done):

```
Discover every user flow and workflow in this project. Use ct-run discover. auto. Map every page, endpoint, tool and job, and write a workflow card for every goal. Do not test yet.

You may build a local test copy of the product and download the tools it needs (database, auth server, browser), pinned by version. Run only against local or test data; never write to a remote or production database. Put what you need from me in the tester kit.
```

*Step 2, test everything* (new session; repeat until the report says every flow is tested):

```
Test the user-flow map. Use ct-run continue. auto. Audit only: do not change product code.

You may build a local test copy of the product and download the tools it needs, pinned by version, and use service doubles for outside services. Run only against local or test data; never write to a remote or production database. Put what you need from me in the tester kit.
```

Prefer the Claude Code plugin? `/plugin install clickthrough --marketplace paarths-collab/Clickthrough`

**Set up before the rename (user-flow-qa, `uf-*` skills)?** Run the install
again. It moves `.userflow/` to `.clickthrough/` and `userflow-tests/` to
`clickthrough-tests/`, updates the rules block, and lists the old `uf-*`
skill folders for you to delete. Environment variables `UF_*` (such as
`UF_BUDGET`) are now `CT_*`. Plugin users: uninstall `user-flow-qa` and
install `clickthrough`.

## What you get

| Ask for | Skill |
|---|---|
| A full release audit | `ct-run` |
| A check before the agent says "done" | `ct-ready-check` |
| Every case of one feature or workflow | `ct-cases` |
| What other users, roles, keys or agents can reach | `ct-security` |
| Software issues in the code (swallowed errors, wrong writes, jobs that never catch up, races, config drift) | `ct-code` |
| Fixes, each proven by a real run | `ct-fix` |
| A throwaway test copy of your app | `ct-env` |

More in [`skills/`](skills/). Try it on the bundled demo apps with planted bugs:
[`sample-app/`](sample-app/) (10 bugs) and [`sample-app-hard/`](sample-app-hard/) (25 bugs).

## Requirements

bash and git to install, Python 3 with PyYAML for the checker.
The agent picks its own tools to drive your product.

## License

[MIT](LICENSE)
