# Tester kit request

What this audit needs from you to test the flows it cannot test yet.
Only the items marked **needed** apply to this project; the rest were
already available or are not relevant. Each says which flows it unlocks.

Put passwords, keys and tokens into the session's environment secrets
under the names shown. Do not paste them into the chat.

| # | Item | Status | Unlocks | How to provide |
|---|---|---|---|---|
| 1 | **A staging or preview URL** where the product runs with real services and test data | needed / have / not relevant | flows that need real sign-in, email, files, integrations | `UF_STAGING_URL` |
| 2 | **OK that staging data is test data**, and which tenants or workspaces may be written to | | every write on staging | a sentence in chat |
| 3 | **A test inbox with an API** (a test-mail service whose addresses the tests can read), for invites, sign-up, password reset and notifications | | email flows | `UF_INBOX_API_KEY`, inbox domain in chat |
| 4 | **Test accounts on staging**, one per role, plus a second tenant, using addresses from the test inbox | | role, permission and isolation flows | `UF_<ROLE>_EMAIL`, `UF_<ROLE>_PASSWORD` |
| 5 | **Services in sandbox or test mode on staging** (payments, messaging, AI provider with a spending cap, code hosts, ...) | | flows behind each service | configured on staging, not given to the agent |
| 6 | **Sandbox API keys** for local testing, only where staging cannot be used | | same | `UF_<SERVICE>_KEY` |
| 7 | **Schema or setup files that are not in the repo** (a separate auth or identity service, a shared database) | | a faithful local copy instead of a guessed one | a file or repo path |
| 8 | **OK for read-only checks on production** (pages, links, logged-out API refusals; nothing is created or changed) | | production smoke checks | a sentence in chat |
| 9 | **Permission to download tools** the local copy needs (database, auth server, browser), listed by name and version | | the local copy | a sentence in chat |

Never needed, and never accepted: production write access, real people's
mailboxes or accounts, live payment or production API keys.
