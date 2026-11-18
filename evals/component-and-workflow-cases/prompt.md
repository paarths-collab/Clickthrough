---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

Our app has a "Invite teammate" dialog: an admin types an email and picks a role (Member or Admin), clicks Send. The invitee gets an email with a link valid for 7 days, opens it, sets a name and password, and lands in the workspace with that role. Members can't open the dialog. A workspace can have at most 10 seats.

List the test cases we should run for (a) the dialog itself and (b) the whole invite workflow, and say how you'd choose which to run. Be concise: dimensions and representative cases, not hundreds of rows.
