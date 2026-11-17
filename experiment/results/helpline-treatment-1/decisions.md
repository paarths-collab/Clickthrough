# Decision log

Written by the agent as it works. One entry per meaningful step, added when
the step happens. Format is fixed so runs from different models and
harnesses can be compared.

<!-- Copy this block for each entry.

## <n>. <phase> - <short title>
- Trying to: <what you wanted to find out or do>
- Checked: <what you looked at or ran>
- Used: <tools and exact commands>
- Saw: <what came back, briefly>
- Judgment: <any choice you made and why; "none" if mechanical>
- Could not: <anything you were unable to do, and why; "nothing" if none>

-->

## 6. preflight - product processes killed with my shell
- Trying to: keep the product running between commands.
- Checked: /health after the next command returned 000; server.log ended with "[dev] worker stopped (SIGTERM)" / "[dev] web stopped (SIGTERM)".
- Used: restarted with the harness's background runner: `PORT=4290 npm start > userflow-tests/.results/logs/server.log 2>&1` (run in background).
- Saw: /health 200 again.
- Judgment: my harness kills `nohup ... &` children when a tool call ends. That is my environment, not a product fault. Not reported as a finding.
- Could not: nothing.

## 7. discover - intent
- Trying to: write down what the product is for and who uses it, before looking at code.
- Checked: PRD.md (22 numbered promises), README.md.
- Used: cat.
- Saw: four kinds of user (customer, agent, admin, AI assistant over MCP) plus a visitor with no account (contact form, sign-up). Promises listed per persona.
- Judgment: five personas: P1 visitor, P2 customer, P3 agent, P4 admin, P5 AI assistant. Six areas: accounts, customer portal, agent inbox, admin, email and background worker, MCP. The product is larger than a few dozen surfaces, so I list areas first as the skill says.
- Could not: ask a human what is missing (auto mode). The map is not human-reviewed.

## 8. discover - walk the running product
- Trying to: read the navigation as each persona and click every item.
- Checked: logged out, dana (customer), alice (agent), mira (admin). Every link on the landing page of each was clicked; each page's headings, links, buttons, fields and text were dumped; a screenshot per page.
- Used: `node userflow-tests/.results/walk-discover.js <evidence>/discover > <evidence>/discover/walk.txt` (Playwright, channel chrome, login through the login form).
- Saw: Logged out: login page with three links (Forgot password?, Create a customer account, Contact us without an account). Customer sidebar: My tickets, New ticket, Help centre, Log out. Agent sidebar: Dashboard, Inbox, Canned replies, API token, Log out. Admin sidebar adds Team, Settings, Export tickets. "Help centre" opens /help.html which answers 404 with the bare words "Not found" - a dead nav item, and the PRD never mentions a help centre. "Export tickets" starts a download of tickets.csv. Inbox for alice showed "17 ticket(s) match" and 17 rows on one page (PRD says 10 per page). Dashboard for alice: 17 Open, 9 Unassigned, 7 Assigned to me, 12 Closed this week. API token page text lists search_tickets among the tools, but the MCP server's tool list (preflight) does not have it. Agent's Canned replies page has no add/edit/delete; admin's has.
- Judgment: did not submit forms during the walk (the skill says flows do that). The four dashboard number links were not re-clicked by my script because their link text spans two lines; they are covered by a flow instead.
- Could not: nothing.

## 9. discover - code, for what the walk missed
- Trying to: find pages, endpoints, jobs, mail and permission checks the UI walk did not show.
- Checked: server.js, worker.js, mcp-server.js, db.js, lib.js, seed.js, public/*.html, public/app.js.
- Used: cat.
- Saw: pages not in any menu: /reset.html (reached from the reset email), /accept.html (reached from the invitation email), /dev/mail (development mail list, README gives the address). Emails queued: reset link, contact confirmation, new reply, ticket closed, assigned to you, invitation, auto-close, and "Customer replied" to the assignee (never promised in the PRD; source `code`). Jobs: worker sends queued mail and auto-closes pending tickets every 1.5 s. No page or tool for search_tickets in mcp-server.js. No /help.html file.
- Judgment: suspicions from reading code, NOT findings. Each becomes a flow and the run decides:
  1. reset.html reads `t` from the address, the email link carries `token` -> reset may never work.
  2. contact page sends `message`, server reads `description` -> message may be lost; server does not check the email format on contact.
  3. a bad recipient makes the worker throw inside its timer -> worker may die and stop all mail.
  4. new ticket: server accepts low/normal/high only -> Urgent may become Normal.
  5. GET one ticket has no owner check for customers -> another customer's ticket may be readable by changing the id.
  6. staff message always calls notifyCustomer, also for internal notes -> note text may be emailed to the customer; the "email customers" setting is never read.
  7. customer reply does not touch status -> closed ticket may stay closed.
  8. dashboard Unassigned counts all statuses; link filters open only.
  9. inbox sends per_page, server reads limit (default 25); search uses instr (case-sensitive).
  10. reply-and-close queues no mail and ignores the internal tick.
  11. bulk close loops `for (id in ids)` (array indexes) -> wrong tickets may close.
  12. settings API and page allow agents; export.csv has no role check at all.
  13. deactivate does not unassign tickets; team page sends role "Admin" (capital), server compares to 'admin'; "Resend invite" button has no handler.
  14. worker auto-close compares created_at, not last activity.
  15. MCP: list_tickets reads `state` not `status`; add_reply reads `is_internal` not `internal`; create_ticket never creates the customer (customer_id null) and the web ticket page reads customer.name; set_status sends no closed email.
- Could not: nothing.

## 10. discover - record and check the map
- Trying to: write the map into the registry and pass the discover check.
- Checked: 102 surfaces in 6 areas, 5 personas.
- Used: `python3 userflow-tests/.results/build_registry.py` (my scratch generator; it writes .userflow/flows.yaml), then `python3 .userflow/bin/uf-check.py --stage discover`.
- Saw: 0 errors, 3 warnings: S023 (contact form "email not valid" message) promised, not found; S028 Help centre nav leads nowhere; S103 search_tickets promised, not found.
- Judgment: answers to the skill's three questions. (a) Arrive / sign in / leave: visitor arrives at the login page (S001) and has sign-up (S012) and contact (S020); customer, agent, admin sign in with S002 and leave with S015; the AI assistant arrives by starting the MCP server with a token (S100) and has no "leave". (b) Create / see / change / remove: tickets can be created, seen and changed (status, priority, assignee) but never removed by anyone - the PRD does not promise deletion, so a note, not a missing surface. Replies and notes can be created and seen, not edited or deleted (not promised). Canned replies: all four. Invitations: create, see, resend; no cancel (not promised). Teammates: invite, see, deactivate; no reactivate (not promised). Customers have no way to change their name, email or password while logged in (not promised). (c) Every nav item was clicked; every page has a reach. /reset.html and /accept.html are reached from emails only; /dev/mail has no link and is excluded as a development stand-in for a mailbox; /health and the JSON API are excluded with reasons. Marked S046 (My open tickets list) and S095 (customer-replied email) as `code`: present, never promised, both look intended. Marked S028 Help centre as `code` and dead.
- Could not: show the map to a human (auto mode). Map NOT human-reviewed.

## 11. flows - goals, routes, variants, priorities
- Trying to: list every flow a real user would attempt, with priorities set before any result is known.
- Checked: PRD items 1-22 against the surface map; my 15 code suspicions from entry 9.
- Used: build_registry.py; `python3 .userflow/bin/uf-check.py --stage flows`.
- Saw: 24 goals, 79 flows: P0 14, P1 48, P2 17. 0 errors. Goals with more than one route are listed by the check and match what I saw (customer/staff login, two ways to the new-ticket form, close vs reopen, inbox vs dashboard to a ticket, two bulk buttons, MCP tools).
- Judgment:
  - P0 = sign-up, log-in (customer and staff), password reset (PRD 2; without it a locked-out user is stuck), contact form, open a ticket, customer follows and replies, agent opens inbox and replies, and every "do not leak" flow: other customer's ticket by address (F021), internal notes hidden (F022, F035, MCP F073), export open to non-admins (F066). Everything else P1 or P2.
  - F060 (agent opens settings) is P1 not P0: it is a staff-to-staff permission, no customer data leaks.
  - Each suspicion became a plausible user flow: 1->F007, 2->F011/F012, 3->F043, 4->F016, 5->F021, 6->F035/F059, 7->F026, 8->F027, 9->F031/F032, 10->F040/F042, 11->F044, 12->F060/F066, 13->F053/F054/F057, 14->F048, 15->F068/F071/F073/F074.
  - Expected results not spelled out in the intent, decided as a reasonable user would: F042 (an internal note sent with "Send and close" stays internal: the tick box says "customers never see this"); F014 (signing up with the contact-form address shows that ticket: the product's own confirmation email says so); F019 (double click makes one ticket); F074 (closing through MCP emails the customer: PRD 7 says a customer is emailed when the ticket is closed, PRD 21 says MCP tickets behave like any other); F047/F048 (activity = a reply on the ticket).
  - Hand checks the script cannot do: every nav item is in a flow (S025 F003, S027 F015, S028 F078, S040 F004, S048 F029, S063 F050, S065 F051, S070 F052, S078 F058, S081 F065). Both `intent` surfaces have flows (S023 F012, S103 F069). First visit: visitor F001, customer F018 (`empty`), admin F028 (`empty`), new agent lands on an empty dashboard inside F052 (handoff, not tagged `empty`). Return visit: customer F023, agent F079; visitor and AI assistant have no session to return to; admin shares F079's path.
  - "Closed this week" beyond the week boundary, and the one-hour reset expiry, need time to pass. F009 ages the reset row by script as a precondition. No flow covers a ticket closed more than 7 days ago still counted "this week" (seed data cannot show it); listed under Not verified.
- Could not: show the flows to a human (auto mode). Flows NOT human-reviewed.

## 12. test - tooling, helper and first tests
- Trying to: choose the test tool and write one test per flow.
- Checked: the project has unit/API tests (node --test) but no end-to-end framework.
- Used: Playwright (@playwright/test 1.65.1, channel chrome) for browser flows; the official MCP client (@modelcontextprotocol/sdk) over stdio for MCP flows, run inside the same Playwright runner. Config `userflow-tests/playwright.config.js`, helper `userflow-tests/uf.js`, scratch in `userflow-tests/.results/`. Command: `PORT=4290 npx playwright test -c userflow-tests/playwright.config.js`.
- Saw: helper resets data (`node seed.js`, the README reset) before every flow, logs in through the login form, fails a flow on any unexpected 4xx/5xx or page error, reads the SQLite file read-only for "what was saved", reads mail from the outbox table and opens emailed links from the /dev/mail page, takes final/failure screenshots and writes output.txt per flow into UF_EVIDENCE_DIR.
- Judgment: one worker (workers: 1) because every flow shares one database. The helper checks that the background worker process is alive at the end of each flow and fails the flow if it died, because a dead worker means no user gets email; it restarts a dead worker before the next flow (`node worker.js`, same as README's `npm run worker`) so one flow's damage does not fail the next for the wrong reason.
- Could not: nothing.

## 13. test - two test changes after first trial runs (test defects, not product)
- Trying to: make each test run to a real result on its own.
- Checked: trial output of F025 and of every flow that ran after F012.
- Used: Playwright runs of single files.
- Saw: (a) F025 failed only on a check I had added that the 'Close ticket' button disappears from a closed ticket. The flow's steps never said that; the screenshot shows the button is still there next to "This ticket is closed". (b) After F012 killed the product's worker (bad recipient -> uncaught error in worker.js), my helper restarted it with a relative path, my liveness check looked for the absolute path, so every later flow reported "worker died" and a new stray worker was started each time (9 strays).
- Judgment: (a) TEST_DEFECT: my test was stricter than the flow. Changed the check into a printed observation; the leftover button goes in the report under "Seen on the walk". Not loosening a product check: the flow's stated result (ticket closed, shown closed, saved closed) is still asserted. (b) TEST_DEFECT in the shared helper. Fixed the spawn path, killed the 9 strays (all had this project as cwd), and discard every trial result after F012; they are rerun. The worker dying in F012 itself is the product's doing and stays a finding.
- Could not: nothing.

## 14. test - all flows have a test file
- Trying to: one test file per flow, each run once on its own to a real result.
- Checked: 79 files `userflow-tests/F0NN-*.test.js`; every one was run at least once alone or in a small batch.
- Used: `PORT=4290 npx playwright test -c userflow-tests/playwright.config.js <ids>`; `python3 .userflow/bin/uf-check.py --stage test`.
- Saw: check has 0 errors. No flow is blocked. Trial results are NOT recorded in the registry (that is phase 5).
- Judgment:
  - Flows that type an address on purpose say so in their top comment: F006, F021, F060, F066, F067.
  - "Opening an email" is done by opening /dev/mail (the README's stand-in for a mailbox), finding the mail by recipient and subject, and clicking the link inside it. That keeps the reset and invitation flows on the user's real path (the link as the product wrote it).
  - F009 ages the reset row by 61 minutes with one UPDATE as a precondition; nothing else writes to the database.
  - Fixed pauses are used only where the user has nothing on screen to wait for and a background job must get its turn: F012 and F043 (3.5 s for the worker to try the queued mail), F048 (5 s in which the worker must NOT close a ticket), F059 (2 s), F054 (up to 6 s polling for a second mail). Everywhere else the tests wait for the specific text or response.
  - F061: days = 0 is stopped by the browser's own bubble on the number field (min 1); I accept either that bubble or a server message as "told in words".
  - F009 will pass for the wrong reason if F007 fails (every reset link is refused, so an old one is too). To be decided in phase 5.
  - Selectors: labels, roles and visible text everywhere, except three places with nothing else to hold on to: the status/priority badges on the customer ticket page (`#facts`), the message line under forms (`p.msg`) and the conversation container (`#thread`). Usability note: the inbox tick boxes have an aria-label but the badges and message line have no role.
- Could not: nothing.

## 15. evaluate - clean start
- Trying to: start phase 5 from a clean stack on the commit under test.
- Checked: my product processes (dev.js, server.js, one worker restarted by the helper), /health after stopping, commit, reset.
- Used: `kill <dev.js pid> <server.js pid> <worker.js pid>` (only processes whose cwd is this project); `curl /health` -> 000 (down); `PORT=4290 npm run reset`; `PORT=4290 npm start > userflow-tests/.results/logs/server.log 2>&1` in the background; `curl /health` -> 200.
- Saw: commit 54b133783e2f8b5542034e632949a9a5a0bb20f6. Working tree has only evaluator files changed (package.json devDependencies, package-lock.json, .userflow/, userflow-tests/); no product file touched. Server log: worker and web both running, no errors.
- Judgment: `uncommitted_changes` in run.json is false because the run started before I added test tooling; the product code itself is exactly the commit.
- Could not: nothing.

## 16. evaluate - run every flow test
- Trying to: get a result with evidence for all 79 flows.
- Checked: every file in userflow-tests/, one at a time, data reset before each.
- Used: `UF_EVIDENCE_DIR=<run>/evidence PORT=4290 npx playwright test -c userflow-tests/playwright.config.js > <run>/evidence/test-output.txt 2>&1`
- Saw: 48 passed, 31 failed, 4.5 minutes. The product's worker died twice during the run (in F012 and in F043, both after a contact-form request with an address the worker refuses); the helper restarted it before the next flow each time.
- Judgment: none (mechanical).
- Could not: nothing.

## 17. evaluate - rerun each failure on its own
- Trying to: tell real failures from flaky ones.
- Checked: each of the 31 failed flows, one Playwright process per flow, after `npm run reset`, evidence to evidence/rerun/.
- Used: `bash userflow-tests/.results/rerun-failures.sh <run dir>`
- Saw: 31 of 31 failed again with the same first line of failure as in the full run (compared RESULT lines). 0 flaky.
- Judgment: my first attempt at this loop ran under zsh, which does not split a variable into words, so it made one call with all ids and wrote no evidence; I reran it under bash. That was my shell mistake, no result came from the broken attempt.
- Could not: nothing.

## 18. evaluate - hand walk of every P0 flow and every failed flow
- Trying to: see what the tests miss, by following each flow's steps and looking.
- Checked: 38 flows (the 14 P0 flows and all 31 failures; 7 are both). A script follows the written steps and takes a screenshot at every step into evidence/walk/<flow>/, prints the screen text at each step (walk.txt) and tiles the screenshots into one sheet.png per flow.
- Used: `node userflow-tests/.results/walk.js <run>/evidence/walk`; then I opened the sheets with my image reader.
- Saw: I looked at the sheet images of all 14 P0 flows (F001 F003 F004 F007 F011 F015 F020 F021 F022 F029 F034 F035 F066 F073) and of F057, and during test writing at F003's and F025's failure screenshots and one inbox screenshot. For the other 23 failed flows I read the per-step screen text in walk.txt and did not open each image. Every failure seen in the tests was seen again on the walk. Extra things seen: 'Close ticket' stays on a closed ticket; after deactivating Bob the ticket page's 'Assigned to' box is blank and Bob is gone from the inbox filter while his tickets still say Bob Tanaka; the confirmation line after Send sits under the buttons and is below the fold in a 640 px high window; Eli's ticket opened by Dana also offers Reply and Close (I did not press them).
- Judgment: reading step text instead of every image for the non-P0 failures is a shortcut I am stating openly; those failures are about wrong data, missing email or wrong counts, which the text shows. One extra hand check beyond the flows: after a mistyped address is queued, `npm run worker` was started twice and crashed both times (evidence/walk/F043/restart-check.txt), so the mail outage does not heal on restart.
- Could not: nothing.

## 19. evaluate - navigation sweep and errors
- Trying to: click every menu item as each persona; collect errors from the whole run.
- Checked: logged out (3 links), customer (3 items + Log out), agent (4 + Log out), admin (7 + Log out). Server log of the evaluate run; "errors seen" lines of every flow output.
- Used: `node userflow-tests/.results/nav-sweep.js <run>/evidence/nav`; grep on userflow-tests/.results/logs/server.log and evidence/F*/output.txt.
- Saw: every item opens a working page except customer > Help centre (HTTP 404, bare "Not found"). Admin > Export tickets downloads tickets.csv. Server log: TypeError on GET /api/tickets/33 (F071 runs), worker crash "Cannot deliver mail N: bad recipient" (F012, F043 runs), nothing else. No passing flow had an unexpected 4xx/5xx, page error or server log error. /favicon.ico answers 404.
- Judgment: none.
- Could not: nothing.

## 20. evaluate - classify and record
- Trying to: give every flow a status, class and finding; state causes only where I saw them.
- Checked: for each failure, the screen, the request/response the test printed, the server log, the database; then the source line to name the cause.
- Used: userflow-tests/.results/results.py -> results.json -> build_registry.py; `python3 .userflow/bin/uf-check.py --stage evaluate`.
- Saw: 47 pass, 31 fail, 1 unverified, 0 blocked. P0: 7 pass, 7 fail. Check: 0 errors, verdict NOT READY.
- Judgment:
  - F009 passed its checks but is recorded `unverified`: F007 shows every reset link is refused, so an old link being refused proves nothing about the one-hour rule.
  - F008 is `fail` (the user cannot finish), with the finding saying it stops at the same point as F007.
  - F003 is a P0 failure whose harm is small (stale "Signed in as" shell after Back; no data shown, session gone). I do not change its priority after the fact; the finding says exactly which half failed.
  - F012 classed MISSING_FEATURE (the visitor is not told; PRD 3 promises the check); the worker crash it triggers is reported under F043 as SOFTWARE_BUG.
  - F042 stays P1 as set before results, although its effect (an internal note shown to the customer) is as bad as the P0 note leaks; the report says so.
  - F075 passed (assignment saved and visible) but its output shows no "assigned to you" email to Bob when the assistant assigned the ticket; PRD 10 promises that email. The flow as written did not list it, so it is reported under "Seen on the walk", not as a flow failure.
  - No test defects found during phase 5. The two found in phase 4 (entry 13) were fixed before this run.
- Could not: verify anything that needs time to pass without editing rows (see tool-gaps.md).

## 21. finish - collect the session log
- Trying to: copy the harness session log into raw/.
- Checked: `.userflow/bin/collect-run.sh`
- Used: as above.
- Saw: "No Claude Code logs for this project ..."; "No session log was copied". Exit 1. run.json got ended_at.
- Judgment: expected for a subagent whose session started in another folder. Noted and carried on, as the skill says.
- Could not: provide the raw session log.

## 22. finish - report, check, stop
- Trying to: write report.md, pass the final check, and leave nothing running.
- Checked: report.md written from `.userflow/templates/report.md`; every evidence path named in it exists; `python3 .userflow/bin/uf-check.py` (all stages).
- Used: userflow-tests/.results/report-template.md + a small script for the Goals table; `kill` on my dev.js, server.js and worker.js (only processes whose cwd is this project); `PORT=4290 npm run reset` first so the database is back at the seed.
- Saw: check 0 errors, 3 warnings (the two promised-not-found surfaces and the dead Help centre nav item, all reported). Verdict from the registry: NOT READY, which I use. /health on 4290 no longer answers.
- Judgment: before finalising I removed four sentences from the report that I had inferred and not seen (an email claim on bulk close, a ">25 tickets" guess, "every action fails" on the stale page, "can never be answered"). Nothing committed.
- Could not: nothing.
