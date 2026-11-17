# Baseline run: Helpline (sample-app-hard), no skills

Final message of the evaluating agent, unedited apart from one local path.
Prompt: "Evaluate whether this project is ready for real users. Report everything that is broken."

## 1. Verdict

Not ready for real users. The core loop runs (sign up, log in, open ticket, reply, close), and the project's own tests pass 14/14, but the tests cover almost none of what is broken. I found privacy leaks (internal notes emailed to customers, customers reading each other's tickets, customers downloading the full export), a password reset that never works, a bulk action that closes the wrong tickets, a background worker that one mistyped email address kills permanently, and an MCP server that turns "internal" notes into public replies. No real email is sent at all, and the page that shows mail is open to anyone. Roughly half of the 22 PRD items fail in at least one way.

## 2. What is broken

"Ran it" = seen in the running product (browser via Playwright, HTTP calls, or the MCP server over stdio). "Read it" = from code only.

**Privacy and access**

1. **Internal notes are emailed to the customer.** Agent ticks "Internal note (customers never see this)", sends; customer gets a "New reply" email containing the note. *Ran it*: as alice on ticket #2 in the browser, the note text appeared in mail to dana on /dev/mail.
2. **Any customer can read any other customer's ticket.** Changing the id in `/portal-ticket.html?id=N` shows someone else's subject, description, name and public conversation (the API response also carries their email). Internal notes are filtered there; replying is blocked. *Ran it*: brand-new account opened Dana's ticket #1.
3. **Any logged-in customer or agent can download the full ticket export.** PRD says admins only. *Ran it*: `/api/export.csv` returned 200 with every ticket and customer email for a customer session and for an agent session.
4. **Agents can see and change Settings.** Not in their menu, but `/settings.html` works. *Ran it*: alice renamed the company to "Changed By Agent" and turned off customer emails; the new name showed in the admin's sidebar.
5. **Sent-mail page is public and is the only "email".** `/dev/mail` needs no login and lists every message including reset and invitation links, so anyone can request a reset for any account and read the link. *Ran it*: fetched it with no cookie (200), then used a token from it to change dana's password through the API. *Read it*: `worker.js` only marks mail as sent; nothing is ever delivered (PRD lists real email as out of scope, but real users would receive nothing).
6. **Contact form trusts whatever email is typed.** A request filed with dana's address, no login, lands in Dana's portal as her ticket. A contact-only address can be claimed by anyone who signs up with it (no email verification) and they then see that ticket. *Ran it* (both).

**Customer flows**

7. **Password reset link never works.** Opening the emailed link and saving a new password shows "This link is invalid or has expired"; the new password does not log in. *Ran it* in the browser. Cause (*read it*): the mail links `?token=`, `reset.html` reads `?t=`. Calling the API with the right field works and is single-use (*ran it*).
8. **Contact form loses the message.** The ticket arrives with an empty description. *Ran it*: agent view of the ticket showed "Sam Visitor wrote" and nothing else. Cause: page sends `message`, server reads `description`.
9. **Contact form accepts invalid emails**, and says "Thanks!". *Ran it* with `typo.person-at-example`. A request with no name or message is also accepted.
10. **One invalid address kills the worker for good.** After item 9 the worker crashed (`Cannot deliver mail 4: bad recipient`), `npm start` kept the web app up and did not restart it; a later reset request produced no mail (sent count 3 before, 3 after). Restarting the worker crashes again on the same queued mail. So all mail and auto-closing stop until someone repairs the database. *Ran it*.
11. **"Urgent" is saved as "Normal".** *Ran it*: new ticket with Urgent showed badge "normal". Low/Normal/High are kept.
12. **Replying to a closed ticket does not reopen it.** Page says "Replying will reopen it"; status stays closed, and the portal has no other reopen control. *Ran it*.
13. **"Help centre" menu link is a 404** ("Not found"). *Ran it*.
14. **Customer who closes their own ticket gets no "closed" email.** *Ran it* (mail count unchanged). PRD wording is ambiguous on this; lower priority.

**Agent flows**

15. **Bulk close closes the wrong tickets.** *Ran it*: ticked #3 and #4, clicked Close selected, got "2 ticket(s) closed"; #3 and #4 stayed open and #1 was closed. Via API, ids [13,15] closed #1 as well. No "closed" email is sent for bulk closes either. Cause: `for (const id in ids)` uses array positions.
16. **Send and close sends no email**, though the page says "Reply sent to the customer and ticket closed". *Ran it*: no mail of any kind for ticket #14.
17. **Send and close ignores the Internal note tick.** With the box ticked, the text is stored as a normal public reply. *Ran it*: the bubble was not marked internal in the agent view. (*Read it*: non-internal messages are shown in the customer portal.)
18. **"Email customers when an agent replies" switch does nothing.** *Ran it*: with it off, the customer still got the reply mail.
19. **Pending tickets are closed by ticket age, not inactivity.** *Ran it*: ticket #5 (created 28 days ago) got an agent reply, was set to Pending, and was closed about 4 seconds later; customer was mailed "We had no reply for 7 days". Cause: worker compares `created_at`.
20. **Inbox paging is wrong.** 17 open tickets all appear on "Page 1 of 2"; Next shows "No tickets here." With Any status: 25 rows, 7 rows, then two empty pages of "4". *Ran it*. Cause: page sends `per_page`, server reads `limit` (default 25).
21. **Search is case-sensitive.** "Refund" finds 1, "refund" finds 0. *Ran it*.
22. **Dashboard "Unassigned" count is wrong.** Card says 9, the linked inbox shows 5 (count includes closed tickets). *Ran it*.
23. **"Closed this week" links to all closed tickets, not this week's.** *Read it* (seed data has all 12 closed within the week, so the numbers happened to match).

**Admin flows**

24. **Inviting as Admin creates an Agent.** *Ran it*: invited priya as Admin, list showed "agent", she accepted and got "No access" on Team. Cause: page sends "Admin", server expects "admin".
25. **"Resend invite" does nothing.** *Ran it*: clicked, sent-mail count stayed 5. No handler and no endpoint exist.
26. **Deactivating a teammate does not unassign their tickets**, though the page says "Their tickets are back in Unassigned". *Ran it*: alice's 13 tickets stayed hers; open+unassigned count did not rise. They also drop out of the assignee filter (cannot be found by name), the ticket page's assignee box shows blank, and a customer reply on such a ticket notifies nobody (mail count unchanged). Login is correctly blocked.

**MCP server**

27. **`add_reply` with `internal: true` posts a public reply.** Returned `"internal": false`; customer was emailed the note and saw it in their ticket. *Ran it*. Cause: code reads `is_internal`.
28. **`search_tickets` does not exist** ("Unknown tool"), though PRD and the API token page list it. *Ran it*.
29. **`list_tickets` ignores `status`.** `status: pending` returned all 32. *Ran it*. Cause: code reads `state`. `assignee_email` works.
30. **`create_ticket` for an unknown email creates no customer.** Ticket has no customer; opening it in the web app shows "Could not load this ticket" (HTTP 500, TypeError in the server log); the inbox shows "—"; replies to it email nobody. *Ran it*. Signing up later with that address would not show the ticket (*read it*).
31. **`set_status` closed sends no "closed" email; `assign_ticket` sends no email to the agent.** *Ran it* (no such mail appeared).

**Robustness and deployment**

32. **Malformed login requests give HTTP 500** (body `null`, or a numeric password). *Ran it*.
33. **No limit on wrong logins.** 20 wrong passwords in a row, all answered normally. *Ran it*.
34. **Session cookie has no Secure flag and no expiry** (*ran it* for the header); sessions never expire and request bodies have no size limit (*read it*).
35. **Unusable at phone width.** No viewport tag; at 375 px the dashboard is 691 px wide and the inbox 888 px. *Ran it*.
36. **`npm run reset` / `npm run seed` wipe all data with no confirmation**, and seeded accounts share a documented password and fixed API tokens. *Read it*.
37. **Tests give false confidence.** 14/14 pass with all of the above present. *Ran it*.

**Worked when I tried it:** signup, login, logout, wrong-password message, customers listing only their own tickets, internal notes hidden in the portal, customers blocked from staff pages, reply email on Send, closed email on status change, assignment email, canned reply insertion (appends), canned CRUD admin-only, status/priority/assignee changes, status and assignee filters, bulk assign, Team admin-only, admin export (32 tickets), auto-close of genuinely stale pending tickets with email, HTML in user text not executed anywhere, path traversal blocked, MCP `get_ticket` and bad-token handling.

## 3. Could not check

- Real email delivery: there is none.
- Reset link one-hour expiry: would need an hour's wait or editing the database; code has the check.
- "Closed this week" boundary and auto-close timing over real days: no aged data without editing the database; I only shortened the setting to 1 day.
- Load, concurrency, large data, HTTPS or any production deployment setup.
- Browsers other than headless Chromium; screen readers and keyboard-only use.
- MCP with a real AI client; I used a hand-written JSON-RPC client over stdio.
- Portal view after signing up with an MCP-created ticket's email (concluded from code only).

## 4. What I did

- Read all source, pages, PRD, README and tests.
- Ran `npm test` (temp dir pointed inside the project).
- Started the product with `npm start` (web on 4280 plus worker), twice; used `npm run reset` between runs.
- Browser (Playwright, headless, installed with `--no-save` and removed afterwards): all three roles. Customer: signup, portal, new ticket, ticket page, close/reply, forgot/reset, contact. Agent: dashboard, inbox, ticket page, canned replies, API token, settings. Admin: team, invite/accept, deactivate, settings, canned CRUD, export download.
- HTTP scripts and curl for the same flows plus permission and robustness probes.
- Background worker: watched mail delivery, auto-close, the crash, and a restart.
- Email: read through `/dev/mail`.
- MCP server: started over stdio with alice's token; called `initialize`, `tools/list` and every tool.
- Clean-up: all processes stopped, port 4280 free, database back to seeded state, no product file changed. My scripts, logs and screenshots are left untracked in `.eval/` in the project copy.

## 5. Time

About 12 minutes wall-clock (15:19 to roughly 15:31 local).
