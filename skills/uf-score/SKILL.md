---
name: uf-score
description: Score a finished audit against a list of problems the human already knows about - what it found, what it missed, false alarms, how each finding was known - and add a row to the scorecard. Use after an audit when asked to score, grade or compare runs. Never in the session that did the audit, and never before it finishes.
---

# Score an audit

The point is to learn where audits fall short, so the skills and the
harness can be improved, and so cheaper models can be measured later.

## Inputs

- **The audit's report** (`report.md`, `AUDIT-*.md`, or its final message).
- **Known issues:** the human's own list of what is broken, written before
  they read the report. A file outside the audited repo, or pasted in. If
  there is none, ask for it; without it you can only score evidence
  quality, not what was missed.
- **Run facts** from `run.json` or the human: harness, model, condition
  (`skills` or `baseline`), mode, time, tokens.

This session must not be the one that ran the audit: an auditor that sees
the known issues stops being a fair test.

## Score

For every known issue: **found** (the report describes what the user
experiences; naming the cause is a bonus), **partly** (right area, wrong
or vague effect), or **missed**.

For every finding in the report that is not on the list: **extra real**
(check it against the code or the product before counting it), **false
alarm** (not real, or no user or attacker is affected), or **unsure**.

For every finding, how it was known: `ran`, `traced` or `read`, and
whether its evidence holds up (a screenshot, an output, a file and line
that says what the report claims).

Also: did the report say READY while a known issue is P0 or a Critical or
High security problem (`wrong_ready`)? Did it state what it did not cover?

## Write

1. A short scoring note next to the report: the table of known issues with
   found / partly / missed, the extra and false findings, and two or three
   sentences on what the audit missed and why (no way to run it, area not
   covered, pattern not checked).
2. One row in the scorecard (`experiment/scorecard.csv` in the pack, or a
   `scorecard.csv` the human names), same columns as the existing rows.
3. When an issue was missed because a skill gave no instruction for it,
   say which skill and what it should add. That is the input for the next
   refinement.

Add newly confirmed extra findings to the human's known-issues list only
if they agree.
