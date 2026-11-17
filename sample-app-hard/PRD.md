# Helpline: product brief

Helpline is a shared support inbox for a small company. Customers send in
problems, the support team answers them, and an admin runs the team. An AI
assistant can work the same inbox through an MCP server.

## Who uses it

- **Customers** send tickets and follow them in a small portal.
- **Agents** answer tickets from a shared inbox.
- **Admins** are agents who also manage the team and the settings.
- **AI assistants** act for one agent through the MCP server, using that
  agent's API token.

## Customers

1. **Account.** A customer creates an account with name, email and
   password, and lands in the portal already logged in. Log in and log out
   work as usual.
2. **Forgot password.** From the login page a user asks for a reset link,
   gets it by email, opens it, chooses a new password and can then log in
   with it. The link works once and expires after an hour.
3. **Contact us without an account.** Anyone can send a request with their
   name, email, a subject and a message. We check that the email address
   looks valid and tell them if it does not. The request becomes a ticket
   with their full message, and they get a confirmation email.
4. **New ticket.** A logged-in customer opens a ticket with a subject, a
   description and a priority: Low, Normal, High or Urgent. The ticket
   keeps the priority they chose.
5. **My tickets.** Customers see their own tickets and nobody else's, open
   one, read the conversation and reply. Internal notes are never shown to
   customers in any way.
6. **Close and reopen.** A customer can close their own ticket. Replying to
   a closed ticket reopens it, so the team sees it again.
7. **Email.** A customer is emailed when an agent replies and when the
   ticket is closed.

## Agents

8. **Dashboard.** Shows how many tickets are open, how many open tickets
   nobody has taken (Unassigned), how many are assigned to me, and how many
   were closed this week. Each number links to the inbox showing exactly
   those tickets.
9. **Inbox.** A list of tickets with filters for status and for who it is
   assigned to, and a search box. Search looks in the subject and the
   description and is not case-sensitive. The list shows 10 tickets per
   page with Previous and Next.
10. **Working a ticket.** An agent can reply to the customer, add an
    internal note, change status (Open, Pending, Closed), change priority,
    and assign the ticket to themselves or another agent. An agent who is
    assigned a ticket by someone else gets an email.
11. **Send and close.** One button sends the reply and closes the ticket.
    The customer gets the reply by email, exactly as with Send.
12. **Canned replies.** An agent can insert a canned reply into the reply
    box; it is added to whatever they have already typed.
13. **Bulk actions.** In the inbox an agent ticks several tickets and
    closes them, or assigns them to themselves, in one go. Only the ticked
    tickets change.
14. **Pending tickets close themselves.** A ticket left Pending with no
    activity for the number of days in Settings (7 by default) is closed
    automatically and the customer is told by email.

## Admins

15. **Team.** Admins invite a teammate by email as an Agent or an Admin.
    The teammate gets an email with a link, chooses a name and password,
    and joins with the role they were invited as. Pending invitations can
    be sent again.
16. **Deactivating.** An admin can deactivate a teammate. That person can
    no longer log in, and their tickets go back to Unassigned so someone
    else picks them up.
17. **Settings.** Only admins can see or change settings: the company name,
    the number of days before pending tickets close, and whether customers
    are emailed when an agent replies. When that switch is off, customers
    get no reply emails.
18. **Canned replies.** Admins create, edit and delete canned replies.
19. **Export.** Admins download every ticket as a CSV file. Nobody else can.

## AI assistants (MCP)

20. The MCP server offers these tools: `list_tickets` (optionally by
    status and by assigned agent), `get_ticket`, `search_tickets`,
    `create_ticket`, `add_reply`, `set_status`, `assign_ticket`.
21. A ticket created through MCP for an email address with no account
    creates that customer, and the ticket then behaves like any other.
22. `add_reply` with `internal: true` adds an internal note. Without it,
    the reply is public and the customer is emailed.

## Not in scope

Attachments, SLAs, satisfaction surveys, more than one company per
installation, and real outgoing email (development shows sent mail on a
page instead).
