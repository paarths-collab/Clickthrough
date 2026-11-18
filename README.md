<div align="center">

# user-flow-qa

**Your tests pass. Does the product actually work for the person using it?**

A skill pack that makes AI coding agents test your product the way a real user would:
every flow, on the real running app, with evidence.

Claude Code · Codex · Cursor &nbsp;|&nbsp; any language &nbsp;|&nbsp; web, API, CLI, mobile, desktop, firmware

</div>

---

## Why

Agents say "done" when the code looks right. Users find out it isn't.
**user-flow-qa** makes the agent stop reading code and start using the product:

1. **Map** everything a user can touch: pages, endpoints, commands, jobs.
2. **List** every flow, including every route to the same goal.
3. **Test** each flow against the running app, security included.
4. **Report** flow by flow, with proof: "tested 42 of 42, 3 broken, here's how".

## Quick start

**1. Install.** Ask your agent, from your project root:

```bash
git clone --depth 1 https://github.com/paarths-collab/user-flow-qa.git /tmp/ufqa && bash /tmp/ufqa/install.sh both .
```

Commit what it adds and merge it into your default branch.
It never deletes anything and is safe to run again.

**2. Ask.** In a new session (not the one that built the product):

```
Is this project ready for real users? Use uf-run. auto
```

Prefer the Claude Code plugin? `/plugin install user-flow-qa --marketplace paarths-collab/user-flow-qa`

## What you get

| Ask for | Skill |
|---|---|
| A full release audit | `uf-run` |
| A check before the agent says "done" | `uf-ready-check` |
| Every case of one feature or workflow | `uf-cases` |
| What other users, roles, keys or agents can reach | `uf-security` |
| Fixes, each proven by a real run | `uf-fix` |
| A throwaway test copy of your app | `uf-env` |

More in [`skills/`](skills/). Try it on the bundled demo apps with planted bugs:
[`sample-app/`](sample-app/) (10 bugs) and [`sample-app-hard/`](sample-app-hard/) (25 bugs).

## Requirements

bash and git to install, Python 3 with PyYAML for the checker.
The agent picks its own tools to drive your product.

## License

[MIT](LICENSE)
