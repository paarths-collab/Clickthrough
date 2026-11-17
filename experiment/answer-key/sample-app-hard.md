# Answer key: sample-app-hard (Helpline)

Do not let the evaluating agent read this file or
`verify-sample-app-hard.js`. Copy `sample-app-hard/` out to a clean folder
before a run (see `experiment/protocol.md`).

Helpline is a support inbox with three roles (customer, agent, admin), a
web app, a background worker, an MCP server and one database. Its own tests
pass (14 of 14) and it starts cleanly. It has 25 planted problems. Every
one, and every item under "Things that work", is proved against the running
app by:

```bash
NODE_PATH=<folder with playwright>/node_modules node experiment/answer-key/verify-sample-app-hard.js
```

## Tiers

The problems are graded by what it takes to notice them.

- **T1, on the surface.** One click or one listing shows it.
- **T2, one flow.** One user doing one thing end to end, and checking the
  result rather than the success message.
- **T3, a second look.** Needs a second user, a side effect (email,
  database), a particular starting state, or a specific input.
- **T4, time and knock-on.** Shows up seconds later, in another process, or
  as the cause of other things failing.

## The 25 problems

| # | Tier | What the user experiences | Where it breaks | Class | Pri |
|---|---|---|---|---|---|
| B01 | T3 | A customer opens another customer's ticket and reads the conversation by changing the id in the address. Their own list is correct. | `GET /api/tickets/:id` checks ownership for writes, not for reads. | FLOW_BROKEN (privacy) | P0 |
| B02 | T3 | An agent adds an internal note; the customer receives it by email, word for word. The portal correctly hides it. | The message route notifies the customer without checking `internal`. | FLOW_BROKEN (privacy) | P0 |
| B03 | T3 | A teammate invited as Admin joins as an agent: no Team, no Settings. The pending-invite row already says "agent". | The Team page sends `Admin`; the server only accepts `admin` and falls back to agent. | INTEGRATION | P1 |
| B04 | T3 | After an agent is deactivated the page says their tickets are back in Unassigned. They are not: they stay assigned to someone who cannot log in, and they are in no agent filter. | Deactivate never clears `assignee_id`. | FLOW_BROKEN | P1 |
| B05 | T2 | The password reset email arrives; the link opens; saving a new password says "This link is invalid or has expired." Nobody can reset a password. | The email link uses `?token=`; the page reads `?t=`. | INTEGRATION | P0 |
| B06 | T3 | Any logged-in customer can download every ticket, with every customer's name and email, by typing the export address. | `GET /api/export.csv` only checks for a login. | FLOW_BROKEN (privacy) | P0 |
| B07 | T2 | An agent has no Settings item, but can type the address, change the company name and the auto-close days, and save. | The page allows agents; `PUT /api/settings` only refuses customers. | FLOW_BROKEN | P1 |
| B08 | T2 | "Contact us" says "Thanks!" and the ticket reaches the inbox with the subject and an empty message. The logged-in "New ticket" route works. | The form sends `message`; the API reads `description`. | INTEGRATION | P0 |
| B09 | T3 | A customer replies to a closed ticket (the page says this will reopen it). It stays closed, so no agent sees it among open tickets. | The customer reply path never changes the status. | FLOW_BROKEN | P1 |
| B10 | T2 | A customer chooses Urgent; the ticket is saved as normal. Low, Normal and High are kept. | The create route's allowed list has no `urgent`. | INTEGRATION | P1 |
| B11 | T2 | The inbox shows up to 25 tickets on "Page 1" instead of 10, and the later pages it offers are empty. | The page sends `per_page=10`; the API reads `limit` (default 25). The pager is computed for 10. | INTEGRATION | P1 |
| B12 | T3 | Search is case-sensitive: "export" finds one of the two tickets with that word, and "refund" misses "Refund not received" by subject. | Uses `instr()`, which is case-sensitive. | FLOW_BROKEN | P1 |
| B13 | T3 | Tick three tickets, "Close selected": it says "3 ticket(s) closed", the three stay open, and tickets #1 and #2 are closed instead. | `for (const id in ids)` loops over positions, not ids. | SOFTWARE_BUG | P0 |
| B14 | T3 | "Send and close" says the reply was sent to the customer. The customer gets no email. "Send" does email them. | The reply-and-close route queues no mail. | FLOW_BROKEN | P1 |
| B15 | T4 | Set a ticket that was opened long ago to Pending: within seconds it is closed and the customer is told it had "no reply for 7 days". | The worker compares `created_at`, not the last activity. | FLOW_BROKEN | P1 |
| B16 | T2 | The dashboard says 9 Unassigned; clicking it lists 5. | The count includes closed and pending tickets. | FLOW_BROKEN | P2 |
| B17 | T3 | An admin switches off "Email customers when an agent replies". Customers are still emailed. | Nothing reads the setting. | FLOW_BROKEN | P1 |
| B18 | T1 | "Resend invite" does nothing: no message, no email. | The button has no handler and there is no route. | MISSING_FEATURE | P2 |
| B19 | T3 | A ticket created through MCP for an address with no account shows in the inbox with no customer, and opening it says "Could not load this ticket" (server error 500). | `create_ticket` stores no customer; the ticket route assumes one. | INTEGRATION | P0 |
| B20 | T3 | An assistant adds a note with `internal: true`. It is posted as a public reply: the customer sees it in the portal and is emailed it. | The tool reads `is_internal`; the schema says `internal`. | INTEGRATION (privacy) | P0 |
| B21 | T2 | MCP `list_tickets` with a status returns every ticket. | The tool reads `state`; the schema says `status`. | INTEGRATION | P1 |
| B22 | T1 | `search_tickets` is promised in the brief and on the API token page. The server does not offer it. | Never built. | MISSING_FEATURE | P2 |
| B23 | T2 | "Contact us" accepts "typo at example" as an email address and says "Thanks!". | No validation on that route. | FLOW_BROKEN | P1 |
| B24 | T4 | After one request with an undeliverable address, no email is sent to anyone: no reset links, no invitations, no reply notifications. Restarting does not help while that mail is queued. | The worker throws on the bad address and exits; `npm start` does not restart it. | SOFTWARE_BUG | P0 |
| B25 | T1 | "Help centre" in the customer menu opens a bare "Not found" page. | The page does not exist. | FLOW_BROKEN | P2 |

By tier: T1 three, T2 eight, T3 twelve, T4 two. By priority: P0 nine, P1
twelve, P2 four.

## Things that work (a report calling these broken is a false alarm)

Sign-up lands in the portal logged in. Log in, wrong password, log out. The
portal never shows internal notes on screen. Customers see only their own
tickets in their list, cannot reply to or close someone else's ticket, and
can close their own. Agents cannot open Team (page and API both refuse).
"Send" emails the customer. Assigning from the ticket page, and bulk
"Assign selected to me". Inserting a canned reply adds to what was typed.
Canned replies: create, edit, delete. A deactivated agent cannot log in. An
invitation link works once and joins as an agent when invited as Agent.
Admin export is a correct CSV. MCP `get_ticket`, `set_status` and
`assign_ticket`, and `create_ticket` for an existing customer.

## Scoring notes

- Count an item as found only if the report describes the user-visible
  problem. Naming the cause is a bonus, not a requirement.
- Report recall per tier as well as in total. The pack is meant to move T3
  and T4; a strong agent finds most of T1 and T2 without help.
- B24 is found only if the report says that email stopped for everyone, or
  that the worker died. "The reset email never arrived" on its own is a
  symptom: count it as B24 only if B05 and B23 were also separated from it.
- B02, B14, B15, B17, B20 and B24 can only be seen by reading the mail page
  (`/dev/mail`). B19 to B22 need an MCP client.
- B13 needs at least two tickets ticked, and a check of which tickets
  changed. B04 and B09 need a look at what the other role then sees.
- Other real problems exist (sessions never expire, no rate limiting on
  login, bulk actions send no emails). If an agent reports one, check it
  and score it under `extra_real`.
