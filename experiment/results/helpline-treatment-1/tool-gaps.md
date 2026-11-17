# Tool gaps

Things the evaluator wanted to do and could not.

## 1. No way to make time pass
- Wanted: check "the reset link expires after an hour" and "Closed this week" (a ticket closed more than 7 days ago must not be counted) the way a user meets them.
- Could not: the product has no clock control and I cannot wait an hour or a week.
- Did instead: F009 ages the reset row by 61 minutes with one UPDATE as a precondition. No flow covers the 7-day boundary of "Closed this week".
- Effect: F009 is `unverified` (also because every reset link is refused, F007). The week boundary is listed under Not verified.

## 2. Session log not collected
- Wanted: `.userflow/bin/collect-run.sh` to copy the harness session log into the run's raw/ folder.
- Could not: I am a subagent started in another folder; the script found no Claude Code log for this project path.
- Effect: raw/ is empty. decisions.md, evidence/ and report.md are complete.

## 3. Real email cannot be observed
- Wanted: see a customer actually receive mail.
- Could not: the product has no real mail transport (PRD: out of scope); "sent" means the worker marked the outbox row.
- Did instead: read the outbox table and the /dev/mail page.
- Effect: "is emailed" in this report means "the worker marked it sent and /dev/mail lists it".
