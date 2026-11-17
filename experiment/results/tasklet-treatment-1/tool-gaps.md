# Tool gaps

One entry each time an agent wanted to do something and could not. This file
decides which tools get built later, so be specific about what was missing.

<!-- Copy this block for each entry.

## <date> - <short title>
- Run: <run-id>
- Phase: <preflight | discover | flows | test | evaluate>
- Wanted to: <the check or action>
- Blocked by: <what was missing: tool, access, account, data>
- Affected: <flow or surface ids>
- Did instead: <weaker check used, or "nothing - marked unverified/blocked">
- Would fix it: <the smallest tool or access that removes the gap>

-->

## 2026-11-17 - Cannot receive email
- Run: 20261117T081226Z-539f506
- Phase: preflight
- Wanted to: receive the password-reset email and the teammate-invite email the PRD promises
- Blocked by: no mailbox, no mail catcher, and the product documents no mail configuration
- Affected: F028 (blocked), last step of F009 and of F026 (both fail earlier for product reasons), surfaces S005, S073
- Did instead: check what the product shows the user, what it sends over the network and what it saves in the database
- Would fix it: a local mail catcher (e.g. a documented SMTP sink on localhost) wired to the product

## 2026-11-17 - Cached Playwright browser build does not match
- Run: 20261117T081226Z-539f506
- Phase: preflight
- Wanted to: launch Playwright's bundled Chromium
- Blocked by: @playwright/test 1.65.1 wants chromium revision 1255; the cache has 1234, 1248, 1254
- Affected: none (worked around)
- Did instead: drive installed Google Chrome with `channel: 'chrome'`
- Would fix it: pin the Playwright version to a cached build, or allow `npx playwright install chromium`

## 2026-11-17 - Subagent cannot write report.md
- Run: 20261117T081226Z-539f506
- Phase: evaluate
- Wanted to: write the filled-in report to `.userflow/runs/<run-id>/report.md` (uf-evaluate step 9)
- Blocked by: the harness refuses the Write tool for report files in a subagent ("Subagents should return findings as text, not write report files.")
- Affected: the report file only; statuses and evidence are in flows.yaml
- Did instead: returned the full report text to the calling session; left the template copy in place
- Would fix it: run uf-run in a main session, or let the caller save the returned text to the run folder

## 2026-11-17 - collect-run.sh finds no session log for a subagent
- Run: 20261117T081226Z-539f506
- Phase: evaluate (finishing)
- Wanted to: copy the harness session log into `raw/`
- Blocked by: the session did not start in this folder, so `~/.claude/projects/<encoded project path>` does not exist
- Affected: `raw/` has server logs and my working files only
- Did instead: nothing - noted in decisions.md
- Would fix it: pass `--session <file>` from the parent session, or run collect-run.sh from the parent after the run
