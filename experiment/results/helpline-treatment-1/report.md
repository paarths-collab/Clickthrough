# User-flow report

- Run: 20261117T095810Z-54b1337
- Commit: 54b133783e2f8b5542034e632949a9a5a0bb20f6 (product code clean; the working tree only has the evaluator's files: `package.json` devDependencies, `package-lock.json`, `.userflow/`, `userflow-tests/`)
- Evaluator: claude (Claude Code subagent), claude-fable-5-2
- Independent of the builder: yes - this session did not write or change any product code
- Mode: auto - the surface map and the flow list were NOT checked by a human
- Areas covered: all six (A1 accounts, A2 customer portal and contact form, A3 agent dashboard/inbox/ticket, A4 admin, A5 email and background worker, A6 MCP server)   Areas not covered: none

## Verdict: NOT READY

A real user cannot rely on this product yet. 7 of the 14 must-work (P0) flows failed, and 31 of 79 flows failed in total, every one of them twice (full run and solo rerun) and again on the hand walk. The worst things a user will hit: any customer can read any other customer's ticket by changing the number in the address, and any logged-in customer or agent can download every ticket as a CSV; internal notes reach customers (by email from the web app, and in the portal and by email when added through MCP or with "Send and close"); nobody can reset a forgotten password; the contact form throws the visitor's message away; and one mistyped email address on the public contact form crashes the background worker so that no email is sent to anyone until someone removes that row from the database by hand.

READY needs every P0 flow passing with evidence. CANNOT TELL means the
product could not be run or P0 flows are unverified.

## Is the software alive

| Check | Result | Note |
|---|---|---|
| Install | ok | Nothing to install for the product (README). Node v26.8.1 (README asks for 22.13+). |
| Build / typecheck | n/a | The project has neither. |
| Existing tests | 14 pass, 0 fail | `npm test` (run with TMPDIR inside the project). They pass while 31 user flows fail. |
| Boot with seed data | ok | `PORT=4290 npm run seed` then `PORT=4290 npm start`. Port 4280 from the README was taken on this machine; `PORT` works as documented. Seed: 5 users, 32 tickets, 3 canned replies. |
| Each service responds | ok at boot | Web: `/health` 200, entry page loads in Chrome (only console error: `/favicon.ico` 404). Worker: process up, mail gets marked sent within about 2 s. Database: SQLite file readable, seed rows present. MCP: official client connects over stdio and lists 6 tools (the PRD promises 7). No errors in the server log at startup. |
| Testing tools work | ok | Playwright 1.65.1 driving installed Chrome (`channel: 'chrome'`; the bundled build was not on the machine), node:sqlite read-only, `@modelcontextprotocol/sdk` client, server log file. |

## Goals

One row per goal, one line per route. A goal works only if every route works.

| Goal | Route | Flow | Priority | Status |
|---|---|---|---|---|
| G01 Create a customer account | sign-up page (normal) | F001 Visitor creates a customer account and lands in the portal logged in | P0 | pass |
|  | sign-up page (wrong_input) | F002 Visitor is told what is wrong with a bad sign-up | P1 | pass |
| G02 Log in and log out | customer (normal) | F003 Customer logs in, sees their portal, logs out and is really out | P0 | FAIL |
|  | staff (normal) | F004 Agent and admin log in and each sees their own menu | P0 | pass |
|  | customer (wrong_input) | F005 Wrong password is refused with a reason | P1 | pass |
|  | customer (interrupted) | F006 A logged-out person who opens an inside page is sent to log in | P1 | pass |
| G03 Get back in after forgetting my password | forgot password link (normal) | F007 Customer resets a forgotten password by email and logs in with the new one | P0 | FAIL |
|  | forgot password link (interrupted) | F008 A reset link works only once | P1 | FAIL |
|  | forgot password link (interrupted) | F009 A reset link older than an hour is refused | P2 | UNVERIFIED |
|  | forgot password link (wrong_input) | F010 Asking for a reset with an unknown address gives the same answer and sends nothing | P2 | pass |
| G04 Send a request without an account | contact form (normal) | F011 Visitor sends a request without an account; it becomes a ticket with the full message and they get a confirmation email | P0 | FAIL |
|  | contact form (wrong_input) | F012 Visitor who types an invalid email address is told so | P1 | FAIL |
|  | contact form (wrong_input) | F013 Visitor who leaves the subject empty is told so | P2 | pass |
|  | contact form then sign-up (handoff) | F014 A visitor who used the contact form later creates an account and finds that ticket | P1 | FAIL |
| G05 Open a ticket | sidebar > New ticket (normal) | F015 Customer opens a ticket with a subject, description and priority High | P0 | pass |
|  | My tickets > Open a new ticket (alternate) | F016 Customer opens an Urgent ticket and it stays Urgent | P1 | FAIL |
|  | sidebar > New ticket (wrong_input) | F017 Customer who leaves subject or description empty is told so | P1 | pass |
|  | My tickets > Open a new ticket (empty) | F018 A brand-new customer with no tickets opens their first one | P1 | pass |
|  | sidebar > New ticket (interrupted) | F019 Double-clicking 'Send ticket' creates one ticket, not two | P2 | FAIL |
| G06 Follow my tickets and reply, and nobody else's | My tickets > ticket (normal) | F020 Customer sees only their own tickets, opens one, reads the conversation and replies | P0 | pass |
|  | address bar (not_allowed) | F021 Customer cannot open another customer's ticket by changing the number in the address | P0 | FAIL |
|  | My tickets > ticket (normal) | F022 Internal notes already on a ticket are not shown to the customer | P0 | pass |
|  | return visit (return_visit) | F023 A customer's reply is still there when they come back later | P1 | pass |
|  | My tickets > ticket (wrong_input) | F024 Customer who sends an empty reply is told so | P2 | pass |
| G07 Close my ticket, and reopen it by replying | Close ticket button (normal) | F025 Customer closes their own ticket | P1 | pass |
|  | reply to a closed ticket (normal) | F026 Replying to a closed ticket reopens it so the team sees it again | P1 | FAIL |
| G08 See at a glance what needs doing (dashboard) | dashboard (normal) | F027 Each dashboard number matches the inbox list it links to | P1 | FAIL |
|  | dashboard (empty) | F028 A staff member with nothing assigned sees a plain empty message | P2 | pass |
| G09 Find tickets in the inbox | sidebar > Inbox (normal) | F029 Agent opens the inbox and opens a ticket from it | P0 | pass |
|  | sidebar > Inbox (normal) | F030 Inbox filters by status and by assignee | P1 | pass |
|  | sidebar > Inbox (normal) | F031 Inbox search finds words in subject and description, whatever the letter case | P1 | FAIL |
|  | sidebar > Inbox (normal) | F032 Inbox shows 10 tickets per page with Previous and Next | P1 | FAIL |
|  | sidebar > Inbox (empty) | F033 A search with no match says so | P2 | pass |
| G10 Work a ticket: reply, note, status, priority, assign | Inbox > ticket (normal) | F034 Agent replies to a customer; the customer sees it and is emailed | P0 | pass |
|  | Inbox > ticket (normal) | F035 Agent adds an internal note; the customer never sees it, on screen or by email | P0 | FAIL |
|  | Dashboard > My open tickets (alternate) | F036 Agent opens a ticket from 'My open tickets' on the dashboard and replies | P1 | pass |
|  | Inbox > ticket (normal) | F037 Agent changes status to Pending, then Closed; customer is emailed about the close | P1 | pass |
|  | Inbox > ticket (normal) | F038 Agent changes the priority | P1 | pass |
|  | Inbox > ticket (handoff) | F039 Agent assigns a ticket to another agent, who is emailed and finds it under 'Assigned to me' | P1 | pass |
|  | Inbox > ticket (normal) | F040 'Send and close' sends the reply, closes the ticket and emails the customer the reply | P1 | FAIL |
|  | Inbox > ticket (wrong_input) | F041 Agent who sends an empty reply is told so | P2 | pass |
|  | Inbox > ticket (alternate) | F042 An internal note sent with 'Send and close' stays internal | P1 | FAIL |
|  | Inbox > ticket (handoff) | F043 Reply emails still arrive after a visitor mistyped their address on the contact form | P1 | FAIL |
|  | return visit (return_visit) | F079 An agent's reply and status change are still there in a new session | P1 | pass |
| G11 Change several tickets at once | Inbox > Close selected (normal) | F044 Agent ticks two tickets and closes only those | P1 | FAIL |
|  | Inbox > Assign selected to me (normal) | F045 Agent ticks two unassigned tickets and assigns only those to themselves | P1 | pass |
|  | Inbox > Close selected (wrong_input) | F046 Clicking a bulk button with nothing ticked says so | P2 | pass |
| G12 Pending tickets close themselves | worker (normal) | F047 A pending ticket with no activity for the set number of days closes itself and the customer is told | P1 | pass |
|  | worker (alternate) | F048 A pending ticket with fresh activity is not closed early | P1 | FAIL |
| G13 Use canned replies | ticket page (normal) | F049 Agent inserts a canned reply after what they already typed and sends it | P1 | pass |
|  | sidebar > Canned replies (normal) | F050 Agent can read the canned replies but not change them | P2 | pass |
| G14 Connect an AI assistant with my API token | sidebar > API token (normal) | F051 Agent finds their API token and an assistant can connect with it | P1 | pass |
| G15 Invite a teammate | Team > invite as Agent (handoff) | F052 Admin invites a teammate as Agent; they accept by email link and join as an agent | P1 | pass |
|  | Team > invite as Admin (handoff) | F053 Admin invites a teammate as Admin and they join as an admin | P1 | FAIL |
|  | Team > Resend invite (normal) | F054 Admin sends a pending invitation again | P1 | FAIL |
|  | Team > invite (wrong_input) | F055 Admin who invites a bad or already-used address is told so | P2 | pass |
|  | invitation link (interrupted) | F056 An invitation link cannot be used twice | P2 | pass |
| G16 Deactivate a teammate | Team > Deactivate (normal) | F057 Admin deactivates a teammate: they cannot log in and their tickets go back to Unassigned | P1 | FAIL |
| G17 Change the settings (admins only) | sidebar > Settings (normal) | F058 Admin changes the company name and auto-close days and they stick | P1 | pass |
|  | sidebar > Settings (normal) | F059 With 'Email customers when an agent replies' switched off, customers get no reply emails | P1 | FAIL |
|  | address bar (not_allowed) | F060 An agent cannot see or change the settings | P1 | FAIL |
|  | sidebar > Settings (wrong_input) | F061 Admin who enters bad settings is told so | P2 | pass |
|  | address bar (not_allowed) | F067 Customers and agents are kept out of pages that are not theirs | P1 | pass |
| G18 Manage canned replies | sidebar > Canned replies (normal) | F062 Admin adds a canned reply and agents can insert it | P1 | pass |
|  | sidebar > Canned replies (normal) | F063 Admin edits and deletes a canned reply | P2 | pass |
|  | sidebar > Canned replies (empty) | F064 With every canned reply deleted the page says there are none | P2 | pass |
| G19 Export every ticket as CSV (admins only) | sidebar > Export tickets (normal) | F065 Admin downloads every ticket as a CSV file | P1 | pass |
|  | address bar (not_allowed) | F066 Customers and agents cannot download the export | P0 | FAIL |
| G20 AI assistant reads the inbox | MCP list_tickets / get_ticket (normal) | F068 Assistant lists tickets (all, by status, by agent) and reads one with its conversation | P1 | FAIL |
|  | MCP search_tickets (normal) | F069 Assistant searches tickets | P1 | FAIL |
|  | MCP with a bad token (not_allowed) | F076 An assistant with a wrong token, or a deactivated agent's token, is refused in words | P1 | pass |
|  | MCP get_ticket (wrong_input) | F077 Assistant asking for a ticket that does not exist is told so | P2 | pass |
| G21 AI assistant opens a ticket for a customer | MCP create_ticket, existing customer (normal) | F070 Assistant opens a ticket for an existing customer; it appears in their portal and the inbox | P1 | pass |
|  | MCP create_ticket, new email (alternate) | F071 Assistant opens a ticket for an address with no account; the customer is created and the ticket works like any other | P1 | FAIL |
| G22 AI assistant replies or leaves an internal note | MCP add_reply (public) (normal) | F072 Assistant replies publicly; the customer sees it and is emailed | P1 | pass |
|  | MCP add_reply internal: true (normal) | F073 Assistant adds an internal note with internal: true; the customer never sees it and is not emailed | P0 | FAIL |
| G23 AI assistant changes status and assignment | MCP set_status (normal) | F074 Assistant closes a ticket; the web app shows it closed and the customer is emailed | P1 | FAIL |
|  | MCP assign_ticket (normal) | F075 Assistant assigns a ticket to an agent | P1 | pass |
| G24 Read help articles (Help centre) | sidebar > Help centre (normal) | F078 Customer opens the Help centre from the sidebar | P2 | FAIL |

Totals: P0 7/14, P1 26/48, P2 14/17, unverified 1, blocked 0. All 79 flows were run: 47 pass, 31 fail, 1 unverified.

Goals where every flow passed: G01, G13, G14, G18.
Goals with at least one failed flow: G02, G03, G04, G05, G06, G07, G08, G09, G10, G11, G12, G15, G16, G17, G19, G20, G21, G22, G23, G24.

## Findings

Worst first. Each one is written so the builder can act on it. Evidence paths are relative to the project root; `E` stands for `.userflow/runs/20261117T095810Z-54b1337/evidence`. Every failed flow has `E/<flow>/output.txt` and `failure.png` (full run), `E/rerun/<flow>/` (solo rerun, same result) and `E/walk/<flow>/walk.txt` + `sheet.png` (hand walk).

### 1. A customer can read any other customer's ticket by changing the number in the address [FLOW_BROKEN] [P0]
- Flow: F021 Customer cannot open another customer's ticket by changing the number in the address
- User did: logged in as Dana, opened her ticket #1, changed the address to `/portal-ticket.html?id=3` (then `id=7`).
- Expected: "We could not find that ticket"; nothing of Eli's shown (PRD 5: customers see their own tickets and nobody else's).
- Got: Eli's tickets in full: "#3 Export to CSV fails", "Eli Navarro wrote Clicking the button gives a blank file.", with Reply and Close buttons. Server answered 200 with the whole ticket.
- Breaks at: step 2, server. Reading one ticket (`GET /api/tickets/<id>` in `server.js`) has no owner check for customers; posting and closing do check. I did not press Reply or Close on the foreign ticket.
- Evidence: E/F021/output.txt, E/F021/failure.png, E/rerun/F021/, E/walk/F021/sheet.png

### 2. Any logged-in customer or agent can download every ticket as CSV [FLOW_BROKEN] [P0]
- Flow: F066 Customers and agents cannot download the export
- User did: logged in as Dana (customer), typed `/api/export.csv`; same as Alice (agent). Neither has "Export tickets" in the menu.
- Expected: refused in words; no file (PRD 19: admins download; "Nobody else can").
- Got: `tickets.csv` downloaded both times: 32 tickets, 15 of them Eli's, with customer names and email addresses.
- Breaks at: server. The export route in `server.js` is placed before the staff/admin role checks, so only "logged in" is required.
- Evidence: E/F066/output.txt, E/rerun/F066/, E/walk/F066/walk.txt

### 3. Internal notes are emailed to the customer [FLOW_BROKEN] [P0]
- Flow: F035 Agent adds an internal note; the customer never sees it, on screen or by email
- User did: as Alice, opened ticket #3, ticked "Internal note (customers never see this)", typed a note, clicked Send.
- Expected: "Internal note added."; the customer sees nothing of it anywhere (PRD 5: "never shown to customers in any way").
- Got: the note is hidden in Eli's portal, but Eli is sent an email "New reply on "Export to CSV fails"" whose body is the full note text.
- Breaks at: step 3, server. The message route in `server.js` calls `notifyCustomer` for every staff message, internal or not.
- Evidence: E/F035/output.txt, E/rerun/F035/, E/walk/F035/sheet.png (panel 4 is the customer's mailbox)

### 4. An internal note added through MCP is public: the customer sees it and gets it by email [INTEGRATION] [P0]
- Flow: F073 Assistant adds an internal note with internal: true
- User did: MCP `add_reply` with `ticket_id: 3`, a body and `internal: true` (as the tool's own schema describes).
- Expected: an internal note (PRD 22); not shown to the customer, no email.
- Got: tool answered `{"ok": true, "internal": false}`; the note is saved as a public reply, appears in Eli's portal as "Alice Brandt (support)" and is emailed to Eli.
- Breaks at: MCP server. The schema declares `internal`; the handler in `mcp-server.js` reads `args.is_internal`.
- Evidence: E/F073/output.txt, E/F073/customer-view.png, E/rerun/F073/, E/walk/F073/sheet.png

### 5. Nobody can reset a forgotten password [INTEGRATION] [P0, and P1 for F008]
- Flows: F007 Customer resets a forgotten password by email; F008 A reset link works only once (stops at the same point)
- User did: Forgot password? -> typed dana@customer.test -> opened the email -> clicked the link -> typed a new password -> Save new password.
- Expected: "Password changed. You can log in with it now."; log in with the new password (PRD 2).
- Got: the email arrives and the link opens "Choose a new password", but Save always answers "This link is invalid or has expired." Password unchanged; the new password is refused at login.
- Breaks at: step 4, between page and server. The emailed link is `/reset.html?token=...`; `public/reset.html` reads `param('t')`, so it sends no token and the server answers 400.
- Evidence: E/F007/output.txt, E/F007/failure.png, E/F008/output.txt, E/rerun/F007/, E/walk/F007/sheet.png

### 6. The contact form loses the visitor's message [INTEGRATION] [P0, and P1 for F014]
- Flows: F011 Visitor sends a request without an account; F014 ...later creates an account and finds that ticket
- User did: Contact us without an account -> name, email, subject, a two-sentence message -> Send.
- Expected: a ticket "with their full message" and a confirmation email (PRD 3).
- Got: "Thanks! We have your request (reference #33)" and the confirmation email arrive, but the ticket's description is empty. The agent sees "Pat Visitor wrote" and nothing under it; the visitor, after signing up, sees the same empty bubble.
- Breaks at: step 2, between page and server. `public/contact.html` sends the field as `message`; the contact route in `server.js` reads `body.description`.
- Evidence: E/F011/output.txt, E/F011/failure-alice.png, E/F014/output.txt, E/rerun/F011/, E/walk/F011/sheet.png

### 7. One mistyped address on the contact form stops all email, and a restart does not bring it back [SOFTWARE_BUG] [P1]
- Flows: F043 Reply emails still arrive after a visitor mistyped their address; also seen in F012
- User did: a visitor sent the contact form with email `pat@visitor` (no ".com"). Then Alice replied to Eli's ticket.
- Expected: either the visitor is told the address is wrong, or it is ignored; Eli gets his reply email.
- Got: the visitor is told "Thanks!". About 1.5 s later the worker process exits with `Error: Cannot deliver mail 1: bad recipient "pat@visitor"`. Eli's reply mail stays queued and is never sent; `/dev/mail` stays empty. Auto-closing of pending tickets is done by the same process (README), so it stops too; I did not separately watch that. Starting the worker again (`npm run worker`) crashes again on the same queued mail, both times I tried.
- Breaks at: worker. `deliver()` in `worker.js` throws for a recipient that is not a valid address, inside the timer, with nothing catching it; the bad mail is first in the queue forever. The door is open because the contact form does not check the address (finding 8).
- Evidence: E/F043/output.txt, E/rerun/F043/, E/walk/F043/walk.txt, E/walk/F043/restart-check.txt, E/F012/output.txt

### 8. The contact form accepts an invalid email address [MISSING_FEATURE] [P1]
- Flow: F012 Visitor who types an invalid email address is told so
- User did: contact form with email `pat-at-visitor`.
- Expected: told the address does not look valid; nothing saved (PRD 3).
- Got: "Thanks! We have your request (reference #33)". A user `pat-at-visitor` and a ticket are saved, a confirmation mail is queued to that address, and the worker dies trying to send it (finding 7).
- Breaks at: server. The contact route checks only that email and subject are not empty.
- Evidence: E/F012/output.txt, E/rerun/F012/, E/walk/F012/walk.txt

### 9. An internal note sent with "Send and close" is shown to the customer [FLOW_BROKEN] [P1]
- Flow: F042 An internal note sent with 'Send and close' stays internal
- User did: as Alice, ticked "Internal note (customers never see this)", typed a note, clicked "Send and close".
- Expected: the note stays internal (or the product refuses and says why).
- Got: "Reply sent to the customer and ticket closed." The note is saved as a public reply and Eli sees it in the portal as "Alice Brandt (support)". (No email went out, only because this button sends none: finding 13.) Priority was set to P1 before the run; the effect is as serious as findings 3 and 4.
- Breaks at: page and server. The "Send and close" call does not pass the tick box and the reply-and-close route always saves a public message.
- Evidence: E/F042/output.txt, E/F042/customer-view.png, E/rerun/F042/, E/walk/F042/walk.txt

### 10. "Close selected" closes the wrong tickets [FLOW_BROKEN] [P1]
- Flow: F044 Agent ticks two tickets and closes only those
- User did: Inbox, ticked #3 and #6, clicked "Close selected".
- Expected: only #3 and #6 closed (PRD 13).
- Got: "2 ticket(s) closed.", but #3 and #6 are still open and #1 "Refund not received" (never ticked) is closed. "Assign selected to me" (F045) works correctly.
- Breaks at: server. The bulk close loop in `server.js` iterates `for (const id in ids)`, i.e. list positions 0 and 1, and closes tickets with those numbers.
- Evidence: E/F044/output.txt, E/F044/open-list-after.png, E/rerun/F044/, E/walk/F044/walk.txt

### 11. An agent can see and change the settings [FLOW_BROKEN] [P1]
- Flow: F060 An agent cannot see or change the settings
- User did: as Alice (agent, no Settings in her menu) typed `/settings.html`, changed the company name, clicked Save settings.
- Expected: "No access" (PRD 17: only admins can see or change settings).
- Got: the full settings form with its values; "Settings saved."; the company name is changed for everyone. (A customer typing the same address does get "No access": F067.)
- Breaks at: page and server. `public/settings.html` allows `['agent', 'admin']` and the settings routes sit under the staff check, not the admin check.
- Evidence: E/F060/output.txt, E/rerun/F060/, E/walk/F060/walk.txt

### 12. A ticket opened through MCP for a new address cannot be opened by anyone [SOFTWARE_BUG] [P1]
- Flow: F071 Assistant opens a ticket for an address with no account
- User did: MCP `create_ticket` for newperson@customer.test; then Alice clicked the ticket in the inbox.
- Expected: the customer is created and the ticket behaves like any other (PRD 21).
- Got: no customer is created; the inbox row shows customer "—"; opening it shows "Could not load this ticket" (HTTP 500; server log: `TypeError: Cannot read properties of undefined (reading 'name')`). So nobody on the team can read or answer it in the web app.
- Breaks at: MCP server and web server. `create_ticket` in `mcp-server.js` only looks the customer up and stores `customer_id` null; `GET /api/tickets/<id>` then reads `customer.name`.
- Evidence: E/F071/output.txt, E/F071/failure-alice.png, E/rerun/F071/, E/walk/F071/walk.txt

### 13. "Send and close" sends the customer no email at all [FLOW_BROKEN] [P1]
- Flow: F040 'Send and close' sends the reply, closes the ticket and emails the customer the reply
- User did: as Alice, typed a reply on ticket #3, clicked "Send and close".
- Expected: the customer gets the reply by email, "exactly as with Send" (PRD 11).
- Got: "Reply sent to the customer and ticket closed."; reply saved, ticket closed, customer sees both in the portal; no email of any kind was queued (waited 6 s; `/dev/mail` empty).
- Breaks at: server. The reply-and-close route saves the message and the status and queues no mail.
- Evidence: E/F040/output.txt, E/rerun/F040/, E/walk/F040/walk.txt

### 14. Pending tickets are closed automatically even when there was activity seconds ago [FLOW_BROKEN] [P1]
- Flow: F048 A pending ticket with fresh activity is not closed early
- User did: as Mira, replied on pending ticket #20, then set the auto-close days to 3 in Settings.
- Expected: #20 stays Pending (PRD 14: "no activity for the number of days").
- Got: within seconds #20 (and #18) were closed and the customer was emailed "We had no reply for 3 days, so this ticket was closed automatically" - 3 seconds after the reply. F047 (ticket really idle) passes.
- Breaks at: worker. `closeStaleTickets()` in `worker.js` compares the ticket's `created_at`, not its last activity.
- Evidence: E/F048/output.txt, E/rerun/F048/, E/walk/F048/walk.txt

### 15. Replying to a closed ticket does not reopen it [FLOW_BROKEN] [P1]
- Flow: F026 Replying to a closed ticket reopens it so the team sees it again
- User did: as Dana, opened closed ticket #22, read "This ticket is closed. Replying will reopen it.", sent a reply.
- Expected: ticket open again and in the team's open inbox (PRD 6).
- Got: "Reply sent.", the reply is saved, the ticket still says closed and is not in the open inbox. The team will not see it unless they look at closed tickets.
- Breaks at: server. The message route updates only `updated_at`.
- Evidence: E/F026/output.txt, E/rerun/F026/, E/walk/F026/walk.txt

### 16. Deactivating a teammate leaves all their tickets assigned to them [FLOW_BROKEN] [P1]
- Flow: F057 Admin deactivates a teammate
- User did: as Mira, Team -> Deactivate on Bob Tanaka.
- Expected: Bob cannot log in and his tickets go back to Unassigned (PRD 16).
- Got: Bob is refused at login ("This account has been deactivated.") - that half works. The page says "Their tickets are back in Unassigned", which is not true: all 10 of his tickets still say Bob Tanaka, the open+Unassigned list still has 5 tickets, Bob is no longer offered in the inbox's "Assigned to" filter, and on his tickets the "Assigned to" box is blank.
- Breaks at: server. The deactivate route sets `active = 0` and deletes sessions; it does not touch tickets.
- Evidence: E/F057/output.txt, E/F057/unassigned-after-deactivate.png, E/rerun/F057/, E/walk/F057/sheet.png

### 17. Inviting someone as Admin makes them an agent [INTEGRATION] [P1]
- Flow: F053 Admin invites a teammate as Admin and they join as an admin
- User did: Team -> email, Role "Admin" -> Send invitation; invitee accepted from the email.
- Expected: joins as admin (PRD 15).
- Got: the pending invitation already says "agent"; the invitee lands signed in as agent with no Team/Settings. I found no other way in the product to make a second admin.
- Breaks at: between page and server. `public/team.html` sends the option text "Admin"; the invite route compares with `'admin'`.
- Evidence: E/F053/output.txt, E/rerun/F053/, E/walk/F053/walk.txt

### 18. Switching off "Email customers when an agent replies" changes nothing [FLOW_BROKEN] [P1]
- Flow: F059
- User did: as Mira, unticked the switch, saved (it stays unticked after reload), replied to ticket #3.
- Expected: no reply email (PRD 17).
- Got: Eli is emailed "New reply on ..." as before.
- Breaks at: server. The setting is saved and never read when mail is queued.
- Evidence: E/F059/output.txt, E/rerun/F059/, E/walk/F059/walk.txt

### 19. A ticket opened as Urgent is saved as Normal [INTEGRATION] [P1]
- Flow: F016 Customer opens an Urgent ticket and it stays Urgent
- User did: New ticket with "How urgent is it?" = Urgent.
- Expected: the ticket keeps the chosen priority (PRD 4).
- Got: the ticket shows and stores "normal". Low, Normal and High are kept (F015).
- Breaks at: server. The new-ticket route accepts only low, normal, high and falls back to normal.
- Evidence: E/F016/output.txt, E/rerun/F016/, E/walk/F016/walk.txt

### 20. Inbox paging does not work [INTEGRATION] [P1]
- Flow: F032 Inbox shows 10 tickets per page with Previous and Next
- User did: opened the Inbox (17 open tickets), clicked Next.
- Expected: 10 rows, "Page 1 of 2", then the other 7 (PRD 9).
- Got: all 17 rows on page 1 under "Page 1 of 2"; Next shows "No tickets here." on "Page 2 of 2".
- Breaks at: between page and server. The page sends `per_page=10`; the server reads `limit` (default 25).
- Evidence: E/F032/output.txt, E/F032/page-2.png, E/rerun/F032/, E/walk/F032/walk.txt

### 21. Inbox search is case-sensitive [FLOW_BROKEN] [P1]
- Flow: F031
- User did: searched "Refund", "refund", "authenticator", "AUTHENTICATOR" with Status "Any status".
- Expected: all four find the ticket (PRD 9: not case-sensitive).
- Got: "Refund" and "authenticator" find it; "refund" and "AUTHENTICATOR" give "0 ticket(s) match." Subject and description are both searched.
- Breaks at: server (`instr`, which compares exact letters).
- Evidence: E/F031/output.txt, E/rerun/F031/, E/walk/F031/walk.txt

### 22. The dashboard's "Unassigned" number does not match its list [FLOW_BROKEN] [P1]
- Flow: F027 Each dashboard number matches the inbox list it links to
- User did: as Alice, clicked each of the four numbers.
- Expected: each number equals the list it opens (PRD 8).
- Got: Open 17/17, Assigned to me 7/7, Closed this week 12/12, but Unassigned says 9 and its list has 5.
- Breaks at: server. The Unassigned count has no "open" condition (PRD: "open tickets nobody has taken").
- Evidence: E/F027/output.txt, E/F027/inbox-Unassigned.png, E/rerun/F027/, E/walk/F027/walk.txt

### 23. MCP list_tickets ignores the status filter [INTEGRATION] [P1]
- Flow: F068
- User did: `list_tickets` with `status: "pending"`.
- Expected: the 3 pending tickets (PRD 20).
- Got: all 32 tickets of every status. Listing all, filtering by `assignee_email`, and `get_ticket` work.
- Breaks at: MCP server. The schema declares `status`; the handler reads `args.state`.
- Evidence: E/F068/output.txt, E/rerun/F068/, E/walk/F068/walk.txt

### 24. MCP search_tickets does not exist [MISSING_FEATURE] [P1]
- Flow: F069
- User did: listed tools; called `search_tickets`.
- Expected: the tool promised in PRD 20 and on the API token page.
- Got: 6 tools, no search; the call answers "MCP error -32602: Unknown tool: search_tickets".
- Breaks at: MCP server (not built). The API token page still advertises it.
- Evidence: E/F069/output.txt, E/rerun/F069/, E/walk/F069/walk.txt

### 25. Closing a ticket through MCP sends the customer no email [FLOW_BROKEN] [P1]
- Flow: F074
- User did: `set_status` with `status: "closed"` on ticket #3.
- Expected: customer emailed that the ticket was closed (PRD 7; the web app does it, F037).
- Got: closed and shown closed in the portal; no email.
- Breaks at: MCP server. `set_status` updates the row and queues nothing.
- Evidence: E/F074/output.txt, E/rerun/F074/, E/walk/F074/walk.txt

### 26. "Resend invite" does nothing [MISSING_FEATURE] [P1]
- Flow: F054 Admin sends a pending invitation again
- User did: invited newagent@helpline.test, clicked "Resend invite" on the pending row.
- Expected: a second invitation email (PRD 15).
- Got: nothing: no request leaves the page, no second email, and the old "Invitation sent." line is still on screen, which reads as if it worked.
- Breaks at: page. The button in `public/team.html` has no click handler, and the server has no resend route.
- Evidence: E/F054/output.txt, E/rerun/F054/, E/walk/F054/walk.txt

### 27. After logging out, the Back button shows the portal again as if still signed in [FLOW_BROKEN] [P0]
- Flow: F003 Customer logs in, sees their portal, logs out and is really out
- User did: logged in as Dana, clicked Log out (login page shown), pressed the browser's Back button.
- Expected: sent to the login page.
- Got: the My tickets page with "Signed in as Dana Whitfield" and "You have no tickets yet." It is a stale shell: the session is deleted in the database, no ticket is shown, and a reload goes to the login page. No data leaks; what is wrong is that a logged-out person (or the next person at that computer) is told they are signed in as Dana with zero tickets. Login and logout themselves work. Counted as a P0 failure because the flow was written that way before the run; its harm is the smallest of the P0 failures.
- Breaks at: step 4, browser/page. On Back the page ran again and drew the sidebar from a cached answer of `/api/me` (on Back the only request the server refused was `/api/tickets`, 401; `/api/me` was not asked again). The API's answers carry no Cache-Control header.
- Evidence: E/F003/output.txt, E/F003/failure.png, E/rerun/F003/, E/walk/F003/sheet.png

### 28. Double-clicking "Send ticket" creates two tickets [FLOW_BROKEN] [P2]
- Flow: F019
- User did: filled the new ticket form and double-clicked "Send ticket".
- Expected: one ticket.
- Got: two identical tickets (#33 and #34) in My tickets and in the team's inbox.
- Breaks at: page. The button is not disabled while the request is on its way.
- Evidence: E/F019/output.txt, E/rerun/F019/, E/walk/F019/walk.txt

### 29. "Help centre" in the customer menu is a dead link [MISSING_FEATURE] [P2]
- Flow: F078
- User did: as Dana, clicked "Help centre".
- Expected: a help page.
- Got: a bare white page saying "Not found" (HTTP 404), no menu; only the browser's Back button gets out. The PRD never mentions a help centre.
- Breaks at: there is no `public/help.html`; the menu in `public/app.js` links to it.
- Evidence: E/F078/output.txt, E/F078/failure.png, E/nav/nav-sweep.txt

## Navigation

Swept in phase 5 as each persona (E/nav/nav-sweep.txt, one screenshot per item in E/nav/).

| Nav item | Opens | Result |
|---|---|---|
| Logged out: Forgot password? | /forgot.html "Forgot your password?" | ok |
| Logged out: Create a customer account | /signup.html "Create a customer account" | ok |
| Logged out: Contact us without an account | /contact.html "Contact us" | ok |
| Customer: My tickets | /portal.html "My tickets" | ok |
| Customer: New ticket | /new-ticket.html "New ticket" | ok |
| Customer: Help centre | /help.html | DEAD: HTTP 404, bare "Not found" |
| Customer: Log out | login page | ok (but see finding 27) |
| Agent: Dashboard | /dashboard.html | ok |
| Agent: Inbox | /inbox.html | ok |
| Agent: Canned replies | /canned.html (read only) | ok |
| Agent: API token | /token.html | ok (page lists a tool that does not exist: finding 24) |
| Agent: Log out | login page | ok |
| Admin: Dashboard, Inbox, Canned replies, API token | as for the agent; canned replies page has add/edit/delete | ok |
| Admin: Team | /team.html | ok |
| Admin: Settings | /settings.html | ok |
| Admin: Export tickets | downloads tickets.csv | ok |
| Admin: Log out | login page | ok |

Pages with no way in: none among product pages. `/reset.html` and `/accept.html` are reached only from emailed links (as intended). `/dev/mail` has no link (development stand-in for a mailbox; the README gives the address).
Promised but not found: MCP tool `search_tickets` (PRD 20); the contact form's "email does not look valid" message (PRD 3); a working "Resend invite" (PRD 15, button exists and is dead).

## Errors seen along the way

Console errors, failed network calls and server log errors seen during
flows, including flows that passed.

| Where | Error | Flow |
|---|---|---|
| Any first page load in a fresh browser | `GET /favicon.ico` 404 (console error; no user would notice) | seen in preflight and discovery |
| Reset page | `POST /api/reset` 400 "This link is invalid or has expired." for a fresh link | F007, F008 |
| Portal after Log out + Back | `GET /api/tickets` 401 while the page shows "Signed in as" | F003 |
| Agent ticket page | `GET /api/tickets/33` 500; server log `[error] GET /api/tickets/33: TypeError: Cannot read properties of undefined (reading 'name')` | F071 |
| Background worker | uncaught `Error: Cannot deliver mail N: bad recipient "pat-at-visitor"` / `"pat@visitor"`; process exits (`[dev] worker stopped (1)`) | F012, F043 |
| Customer menu | `GET /help.html` 404 | F078, navigation sweep |

No flow that passed produced an unexpected 4xx/5xx, a page error or a server log error.

## Seen on the walk, not counted as failures

- The "Close ticket" button stays visible on a ticket that is already closed (customer ticket page).
- When the assistant assigns a ticket through MCP (acting for Alice) to Bob, Bob gets no "Ticket assigned to you" email (PRD 10 promises one when someone else assigns). F075 passed because the assignment itself is saved and visible; the missing email is real.
- After a teammate is deactivated, their tickets show a blank "Assigned to" box on the ticket page and the person disappears from the inbox's "Assigned to" filter, so those tickets cannot be found by assignee.
- Another customer's ticket opened by address (finding 1) also offers "Send reply" and "Close ticket". I did not press them.
- On the agent ticket page the confirmation line ("Reply sent to the customer.") appears under the buttons, below the fold in a 640 px high window; the new message in the thread is the only visible sign.
- Settings: after "Company name is required." the red line stays on screen while a different mistake (0 days) is stopped only by the browser's own bubble.
- Double submit was tried only on New ticket (finding 28). Other forms were not tried.
- Nobody can delete a ticket, cancel an invitation, reactivate a teammate, or change their own name or password while logged in. None is promised in the PRD.

## Not verified

| Flow or surface | Why | What would be needed |
|---|---|---|
| F009 A reset link older than an hour is refused | The old link was refused, but every reset link is refused (finding 5), so this proves nothing about the one-hour rule. Status `unverified`. | Fix reset, then rerun. |
| F008 "works once" half | The first use fails, so the second use was never reached. Status `fail` (same cause as F007). | Fix reset, then rerun. |
| "Closed this week" excludes tickets closed more than 7 days ago | All 12 seeded closed tickets were closed within the last 3 days and I cannot make a week pass. The number and its list matched (12/12) on this data. | Seed data with an older closed ticket, or clock control. |
| Whether Dana can reply to or close Eli's ticket from the page in finding 1 | Not in a flow; I did not press the buttons. | A not_allowed flow for writing to another customer's ticket. |
| Double submit on forms other than New ticket | Only F019 was written. | More `interrupted` flows. |
| Real delivery of email | The product has no real mail transport (PRD: out of scope). "Emailed" here means the worker marked the outbox row sent and `/dev/mail` lists it. | A real or sandbox mail transport. |
| Session expiry | Sessions have no visible expiry and none is promised. Only "no session" (F006) and "after log out" (F003) were checked. | An intent for session lifetime. |
| Human check of the map and flows | Auto mode: nobody reviewed the 102 surfaces and 79 flows. | A human reading `.userflow/flows.yaml`. |

## Stubs and limits

No third-party service was stubbed; the product has none. Nothing in this product was mocked. Mail was read from the product's own outbox table and its `/dev/mail` page.

Limits of this run: one desktop Chrome at 1280x720 (tests) and 1000x640 (walk); no mobile, no other browser, no screen reader, no load. The hand walk covered all 14 P0 flows and all 31 failed flows (38 flows): I looked at the tiled screenshots of the 14 P0 flows and of F057, and for the other 23 failed flows I read the on-screen text captured at each step instead of opening every image. The raw harness session log was not collected (subagent; `collect-run.sh` found none).

- Flaky flows (different result on rerun): none (31 of 31 failures failed the same way on the solo rerun)
- Test defects found and fixed during this run: two, both while writing tests in phase 4, before the evaluation run: (1) F025 had an extra check that the "Close ticket" button disappears, which the flow never promised - turned into a printed observation; (2) the shared helper restarted a dead worker with a relative path that its own liveness check could not see, so every later flow reported a dead worker - fixed, stray workers killed, all affected trial results discarded. None found in phase 5.
- Test tooling added to the project: devDependencies `@playwright/test` and `@modelcontextprotocol/sdk` in `package.json`, `package-lock.json`, `node_modules/`; `userflow-tests/playwright.config.js`, `userflow-tests/uf.js`, 79 files `userflow-tests/F0NN-*.test.js`; scratch tools and logs in `userflow-tests/.results/`. Also written: `.userflow/flows.yaml`, `.userflow/tool-gaps.md`, `.userflow/runs/20261117T095810Z-54b1337/`. No product file was changed. Nothing was committed.
