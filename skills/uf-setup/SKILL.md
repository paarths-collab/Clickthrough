---
name: uf-setup
description: Set up user-flow QA in the current project - creates the .userflow folder (registry, guide, helper scripts), adds the readiness rules to CLAUDE.md or AGENTS.md, and can enable the plugin for every session on this repo, including cloud sessions. Use when asked to set up or install user-flow QA, or when uf-run finds no .userflow folder.
---

# Set up user-flow QA in this project

Run from the project's root folder. The installer never deletes anything
and is safe to run again.

## 1. Find the installer

The installer is `install.sh` in the root of the user-flow QA pack.

- **Loaded from the plugin:** it is two folders above this skill's base
  directory: `<base directory>/../../install.sh`. `${CLAUDE_PLUGIN_ROOT}`
  points to the same pack root if it is set.
- **Not found:** fetch the pack (it is public):
  `git clone --depth 1 https://github.com/paarths-collab/user.git <a temp folder>`
  and use `<that folder>/install.sh`. Never clone it inside the project.

## 2. Pick the mode

| Mode | What it does | Use when |
|---|---|---|
| `plugin` | `.userflow/`, rules in `CLAUDE.md`, and `.claude/settings.json` entries that make Claude Code (also cloud sessions) load this plugin for everyone on the repo. Skills are not copied. | Claude Code, and the plugin is how you got these skills. Default. |
| `claude` | Copies the skills into `.claude/skills/`, rules in `CLAUDE.md`. | Claude Code without the plugin. |
| `codex` | Copies the skills into `.agents/skills/`, rules in `AGENTS.md`. | Codex. |
| `both` | `claude` and `codex` together. | Both agents work on this repo. |

If the human named a mode, use it. Otherwise use `plugin` under Claude
Code and `codex` under Codex.

## 3. Run it

```bash
bash <path to install.sh> <mode> .
```

Show the human what it printed.

## 4. Commit, if they agree

The files only reach cloud sessions once committed and pushed. Ask before
committing. The files to add are whatever the installer printed as
created or changed (typically `.userflow/`, `CLAUDE.md` or `AGENTS.md`,
`.gitignore`, and `.claude/settings.json` or the skills folder).
`.userflow/runs/` is ignored on purpose: run logs can hold secrets.

## 5. Next

Tell the human the three ways to use it:

- release check, in a **new** session: "Is this project ready for real
  users? Use uf-run." (add `auto` to run without stopping for review);
- quick bug hunt: "Find what is broken for users. Use uf-patterns.";
- the building session runs `uf-ready-check` before it says "done" (the
  rules now say so).
