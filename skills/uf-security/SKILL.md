---
name: uf-security
description: Security as user flows - check what each kind of user, API key and AI agent can do that they must not, and what leaks out through side doors. Covers access control, tenant isolation, agent and key privileges, audit trails, data egress, injection, secrets and privacy, each checked by using the product as the least-trusted caller, or traced in code when it cannot run. Use for a security review, before release, or with uf-run.
---

# Security, as flows

Most security holes a user can exploit are flows: someone does a thing
they must not be able to do, and it works. So test them like flows, from
the least-trusted seat: another tenant, a lower role, a logged-out
visitor, an API key, an AI agent fed hostile text.

Same rules as the rest of the pack (`.userflow/guide.md`): run it if you
can, trace it in code if you cannot, record how you know. Never attack
anything but a local or test instance, and never use real people's data.

## 1. Build the access map first

From `uf-inventory.py` output and the code, list every way in:

| Caller | Examples |
|---|---|
| Logged-out visitor | public pages, sign-up, reset, shared links, webhooks |
| Each role | member, admin, owner, restricted, guest |
| Another tenant | a user of a different workspace / org / account |
| API key, per scope | read-only, write, admin-created, role-limited |
| AI agent | MCP key, tool calls, anything that reads untrusted text then acts |
| Service / cron / internal | service secrets, job endpoints |

For each endpoint, page, tool and job, write who should get in. That
table is the spec; every cell is a check. Gaps where nobody decided are
findings.

## 2. Checks (each: how to try it, and what to look for in code)

**A. Access control**
1. **Read without permission.** Change ids in addresses and requests to
   another user's or tenant's item. Code: is ownership checked on reads,
   not only writes; is the tenant id taken from the session, never from the
   body, query or a header?
2. **Act above your role.** Every admin page and endpoint, called as each
   lower role and as logged out. Code: the check is on the server, not just
   a hidden menu item.
3. **Mass assignment.** Send extra fields (`role`, `owner_id`, `workspace_id`,
   `price`) in create/update requests. Code: allow-list of writable fields.

**B. Keys and AI agents** (the "agents propose, humans dispose" rule)
4. **What a key can do that a human must approve.** With each key type,
   try approve, delete, change settings, create keys, invite, export,
   create webhooks or integrations, rotate secrets. Code: every gate that
   lets keys in; does it refuse the agent's key where it should?
5. **Prompt injection to action.** Anything an agent reads (emails,
   tickets, documents, web pages, issue text) can carry instructions. Can
   that text make the agent call a tool that sends data out or changes
   access? Code: which tools can an agent call after reading untrusted
   input, and which of those need a human?

**C. Audit and accountability**
6. **Destructive and control-changing actions leave a record.** Delete,
   bulk delete, role changes, key creation, settings, exports. Do it, then
   look for the audit row: who, what, when, from which key. Code: an audit
   call or trigger on every such path, including bulk and API-key routes.

**D. Data leaving the product**
7. **Egress channels.** Outbound webhooks, exports, integrations, email
   with record contents, share links. Who can create them, to where, with
   what data? Code: `outbound` and `email` in the inventory.
8. **SSRF.** Any feature that fetches a URL the user typed (webhooks, link
   previews, imports). Point it at `http://127.0.0.1`, `169.254.169.254`,
   internal hostnames. Code: URL validated and resolved address checked.
9. **Leaks through side doors.** Raw API responses, error messages, logs,
   emails and exports carrying fields the screen hides (other users'
   emails, internal notes, tokens, stack traces).

**E. Input handling**
10. **Injection.** SQL, command, template, path traversal, header, XSS in
    every place user text is stored and shown back. Code: parameterised
    queries, no string-built shell or SQL, output escaping.
11. **Crash on bad input.** Wrong types, huge bodies, null, missing fields:
    500 instead of a message is a finding; a crash in a worker is worse.

**F. Sessions and secrets**
12. **Sessions.** Logout really ends it; reset and invite links work once
    and expire; cookies `HttpOnly`/`Secure`/`SameSite`; CSRF on state
    changes; sessions end when a user is removed or their password resets.
13. **Brute force and abuse.** Rate limits on login, reset, invite, signup,
    expensive endpoints.
14. **Secrets.** None in the repo, the client bundle, logs or error
    responses; secret comparisons in constant time; keys stored hashed;
    encryption keys rotatable.

**G. Privacy** (when the product holds personal data)
15. **Export and erase are complete.** Every table and file store with
    personal data is in the data-subject export and the erase path.
16. **Retention actually runs** at the volume the product will have, and
    the legal pages it asks people to agree to exist.

**H. Dependencies**
17. Run the ecosystem's audit (`npm audit`, `pip-audit`, `cargo audit`,
    `govulncheck`, OWASP check, ...). High and critical in production
    dependencies are findings; note fixed versions.

## 3. Write them down

Each check that applies becomes a flow in `.userflow/flows.yaml` with
`variant: abuse` (or `not_allowed`), the caller as the persona, and the
expected result "refused, told why, nothing changed, nothing leaked".
Record results like any other flow: `pass`, `fail`, or `likely_broken`
with confidence when traced in code.

Severity in the finding, separate from flow priority:
- **Critical:** data of other tenants readable or writable, auth bypass,
  remote code execution, secrets exposed.
- **High:** an agent or key can do what needs a human; destructive action
  with no audit; data egress anyone can set up; SSRF to internal services.
- **Medium:** missing rate limits, incomplete privacy export or erase,
  weak session handling.
- **Low:** hardening and drift.

Fill the "Security checklist" table in the report: every one of the 17
checks, with ran, traced or not done (and why). A check left out of the
table is a gap in the audit.

Any Critical or High that is `fail` or `likely_broken` makes the verdict
NOT READY or "CANNOT TELL, likely NOT READY", whatever the flow priority.
