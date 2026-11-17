# User-flow report

- Run: 20261117T081226Z-539f506
- Commit: 539f506ec50be7be1882a80ac363ffb0bbfc28fa (product code clean; uncommitted files are the evaluator's only: `.userflow/flows.yaml`, `.userflow/tool-gaps.md`, `userflow-tests/`, a `@playwright/test` devDependency in `package.json`, `package-lock.json`)
- Evaluator: claude (Claude Code subagent), claude-fable-5-2
- Independent of the builder: yes - this session did not write or change the product. The same session wrote the flow tests and then evaluated with them (one long context, not a fresh one).
- Mode: auto - the surface map and the flow list were NOT checked by a human.
- Areas covered: all (A1 Accounts, A2 Projects and tasks, A3 Team)   Areas not covered: none

## Verdict: NOT READY

A real user cannot rely on Tasklet today. Anyone with an account can read
another person's project and add tasks to it by changing a number in the
address, which breaks the one privacy promise the product makes. On top of
that, three of the core actions tell the user they worked and then lose the
result: ticking a task, quick-adding a task from the dashboard, and changing
the display name. A new user who signs up is thrown back to the login page
with no explanation.

7 of 13 P0 flows failed. Every failure below was seen twice (full run, then
alone after a reset) with the same result, and walked by hand with
screenshots.

## Is the software alive

| Check | Result | Note |
|---|---|---|
| Install | ok | `npm install` exit 0. Product has no runtime dependencies. |
| Build / typecheck | none | The project has no build, typecheck or lint step. |
| Existing tests | 3 pass, 0 fail | `npm test`. They cover `lib.js` only (password hash, email regex); none touches the server, a page or the database. |
| Boot with seed data | ok | `npm run seed` -> "Seeded: 3 users, 3 projects, 5 tasks."; `npm start` -> "Tasklet running at http://localhost:4173". README and package.json agree. |
| Each service responds | ok, one cosmetic error | Login page loads in Chrome; `GET /health` 200; SQLite has the seed rows. `/favicon.ico` is 404 (a console error on first page load). No errors in the server log at startup. |
| Testing tools work | ok, one gap | Browser (Playwright 1.65.1 driving installed Chrome), HTTP (curl), read-only DB (`sqlite3 -readonly`, `node:sqlite` readOnly), server log. No way to receive email. Reset: `npm run reset` works while the server is up. |

## Goals

One row per goal, one line per route. A goal works only if every route works.

| Goal | Route | Flow | Priority | Status |
|---|---|---|---|---|
| G01 Create my account and get in | sign-up page | F001 sign up, land on dashboard logged in | P0 | **fail** |
| | sign-up page | F002 email already registered | P1 | pass |
| | sign-up page | F003 password too short | P2 | pass |
| | login page, later | F004 log in later with the new account | P0 | pass |
| G02 Log in | login page | F006 log in, see dashboard and projects | P0 | pass |
| | login page | F007 wrong password | P1 | pass |
| G03 Log out | sidebar > Log out | F008 log out, dashboard closed afterwards | P1 | pass |
| G04 Forgot my password | login page > Forgot password? | F009 reset by email | P1 | **fail** |
| G05 Create a project | sidebar > Projects | F010 create, see it in lists | P0 | pass |
| | sidebar > Projects | F011 empty name is explained | P1 | **fail** |
| | sidebar > Projects | F012 double-click makes one project | P2 | **fail** |
| G06 See my projects and open one | Projects page row | F013 | P1 | pass |
| | Dashboard row | F014 | P1 | pass |
| G07 Add a task to a project | project page > Add task | F015 | P0 | pass |
| | Dashboard > Quick add | F016 | P0 | **fail** |
| | project page > Add task | F017 spaces-only title is explained | P2 | **fail** |
| | project page > Add task | F018 add, refresh, there once | P1 | pass |
| | Dashboard > Quick add | F019 quick add with no projects | P1 | **fail** |
| G08 Tick a task, stays done | project page checkbox | F020 tick | P0 | **fail** |
| | project page checkbox | F021 untick | P1 | **fail** |
| | project page checkbox | F022 still done on return | P0 | **fail** |
| G09 Delete a task | project page > Delete | F023 | P1 | pass |
| G10 See all my tasks | sidebar > My Tasks | F024 owner with tasks | P1 | pass |
| | sidebar > My Tasks | F025 new user, "no tasks yet" | P1 | **fail** |
| G11 Invite a teammate | sidebar > Team | F026 | P1 | **fail** |
| | typed address /team.html | F027 | P2 | pass |
| | invite email to teammate | F028 | P1 | blocked (TOOL_GAP) |
| G12 Change my display name | sidebar > Settings | F029 change, shows everywhere | P1 | **fail** |
| | sidebar > Settings | F030 empty name is explained | P2 | pass |
| | sidebar > Settings | F031 still there next login | P1 | **fail** |
| | sidebar > Settings | F040 name that is a number | P1 | **fail** |
| G13 Keep my data private | own account | F032 Bob sees only his own | P0 | pass |
| | change id in address | F033 Bob cannot open Alice's project | P0 | **fail** |
| | change id, use Add task | F034 Bob cannot add to Alice's project | P0 | **fail** |
| | logged out, typed address | F035 logged-out visitor sees nothing | P0 | pass |
| | own account, second visit | F036 Bob returns | P2 | pass |
| | change id, use Delete / tick | F039 Bob cannot delete or tick Alice's tasks | P0 | **fail** (data safe, see finding 12) |
| G14 Start with an empty account | empty states > first project > first task | F005 | P1 | pass |
| G15 Find my way around | sidebar | F037 Dashboard, Projects, My Tasks, Settings | P1 | pass |
| G16 Reports (in the menu, not in the PRD) | sidebar > Reports | F038 | P2 | **fail** |

Goals that fully work: G02, G03, G06, G09, G14, G15. Goals with at least one
broken route: G01, G04, G05, G07, G08, G10, G11, G12, G13, G16.

Totals: P0 6/13, P1 10/20, P2 4/7, unverified 0, blocked 1.
40 flows: 39 run (20 pass, 19 fail), 1 blocked.

## Findings

Worst first. Evidence paths are relative to the project root; `E` =
`.userflow/runs/20261117T081226Z-539f506/evidence`.

### 1. Any logged-in user can read another user's project and tasks [FLOW_BROKEN] [P0]
- Flow: F033 Another account holder cannot open someone else's project by changing the address
- User did: Bob logged in, opened his own project (address ends `project.html?id=3`), changed the address to `id=1`.
- Expected: "Nobody else can see your projects or tasks" (PRD) - a "not found" or a refusal.
- Got: the page titled "Website relaunch" with Alice's three tasks, an Add task box, checkboxes and Delete buttons.
- Breaks at: step 2, server. `GET /api/projects/1/tasks` answered 200 with Alice's data to Bob. The route (server.js:99-106) looks the project up by id only and never compares its owner with the logged-in user.
- Evidence: `E/F033/failure.png`, `E/walk/F033-walk.png`, `E/test-output.txt`, `E/rerun/F033-output.txt`, `E/cause/requests-and-responses.txt`

### 2. Any logged-in user can add tasks to another user's project [FLOW_BROKEN] [P0]
- Flow: F034 Another account holder cannot add tasks to someone else's project
- User did: Bob, on Alice's project page (as in finding 1), typed "Bob was here" and clicked Add task. Alice then logged in in her own browser and opened "Website relaunch".
- Expected: the task is refused; Alice's project has only her 3 tasks.
- Got: Bob's screen listed the new task; Alice's project shows 4 tasks including "Bob was here"; the database has that row under project 1.
- Breaks at: step 2, server. `POST /api/tasks {"title":"Bob was here","project_id":1}` answered 201. The route (server.js:109-114) inserts with whatever `project_id` is sent and never checks who owns the project.
- Evidence: `E/F034/failure.png`, `E/walk/F034-walk.png`, `E/test-output.txt`, `E/rerun/F034-output.txt`, `E/cause/requests-and-responses.txt`

### 3. Saving a display name that is a number renames a different user [FLOW_BROKEN] [P1]
- Flow: F040 Owner picks a display name that is just a number, and only their own name changes
- User did: Alice opened Settings, typed "2" as her display name, clicked Save. Bob then logged in in his own browser.
- Expected: Alice is now "2"; Bob is still "Bob".
- Got: Alice saw "Saved!" and "Signed in as 2", but her stored name is still "Alice". Bob's dashboard says "Welcome back, 1.0" and "Signed in as 1.0"; the database row for bob@example.com has name `1.0`.
- Breaks at: step 2, server. `PUT /api/settings {"name":"2"}` answered 200. server.js:80 runs `UPDATE users SET name = ? WHERE id = ?` with the values in the order (user id, name), so it sets the name of the user whose id equals the typed text to the caller's id. Same cause as finding 7. Priority raised from P2 to P1 after the run because the damage lands on someone else's account.
- Evidence: `E/F040/failure.png`, `E/walk/F040-walk.png`, `E/test-output.txt`, `E/rerun/F040-output.txt`

### 4. Ticking a task is never saved [INTEGRATION] [P0]
- Flows: F020 Owner ticks a task done (P0); F022 ...leaves, comes back later, and it is still done (P0); F021 Owner unticks a task (P1)
- User did: Alice opened "Website relaunch" and ticked "Write homepage copy". (F022: ticked "Post the job ad", logged out, logged in again in a fresh browser. F021: unticked "Pick a colour palette" and refreshed.)
- Expected: "Tick a task to mark it done; it stays done when you come back" (PRD).
- Got: the row is struck through at once, with no error. The Projects page still says "2 open". Reopening the project, refreshing, or coming back later shows the task unticked (F021: ticked again). Database: `done` never changes.
- Breaks at: step 2, between page and server. The page sends `POST /api/tasks/<id>/complete {"done":true}` (public/project.html:49); the server answers 404 `{"error":"Not found."}` because the only route it has is `PATCH /api/tasks/<id>` (server.js:131). The page ignores the 404.
- Evidence: `E/F020/failure.png`, `E/F021/failure.png`, `E/F022/failure.png`, `E/walk/F020-walk.png`, `E/walk/F021-walk.png`, `E/walk/F022-walk.png`, `E/test-output.txt`, `E/rerun/F020-output.txt`, `E/rerun/F021-output.txt`, `E/rerun/F022-output.txt`, `E/cause/requests-and-responses.txt`

### 5. Quick add says "Task added!" and the task is nowhere [INTEGRATION] [P0]
- Flows: F016 Owner adds a task from the quick-add box on the dashboard (P0); F019 New user with no projects tries quick add (P1)
- User did: Alice typed "Call the recruiter" in Quick add, chose "Hiring", clicked Add task; then opened "Hiring" and My Tasks. (F019: Carol, who has no projects, typed "Plan my week" and clicked Add task.)
- Expected: the task is in "Hiring" and on My Tasks. (F019: told to create a project first, or the task can be found.)
- Got: a green "Task added!". "Hiring" still lists only "Post the job ad" and still says "1 open"; My Tasks does not list the task. Database: the task row exists with `project_id` NULL, so no page can ever show it. For Carol the same happens, and her My Tasks is then stuck on "Loading…" (finding 8). The goal works from the project page (F015 passes) and is broken from the dashboard.
- Breaks at: step 2, between page and server. The dashboard sends `{"title":"Call the recruiter","projectId":2}` (public/dashboard.html:39); the server reads `body.project_id` (server.js:112) and stores NULL. The project page sends `project_id` and works. Nothing stops a quick add when the user has no project.
- Evidence: `E/F016/failure.png`, `E/F019/failure.png`, `E/walk/F016-walk.png`, `E/walk/F019-walk.png`, `E/test-output.txt`, `E/rerun/F016-output.txt`, `E/rerun/F019-output.txt`, `E/cause/requests-and-responses.txt`

### 6. Signing up throws the new user back to the login page [INTEGRATION] [P0]
- Flow: F001 New user signs up and lands on their dashboard, already logged in
- User did: clicked "Create an account", filled name, email and password, clicked Sign up.
- Expected: "After signing up you land on your dashboard, already logged in" (PRD).
- Got: the login page, empty, with no message saying the account exists or that they must now log in. The account was created and logging in by hand works (F004 passes).
- Breaks at: step 3, between page and server. `POST /api/signup` answered 201 with no session cookie and no `sessions` row (server.js:47-58 never starts a session). The page then goes to `/dashboard.html`, whose login check `GET /api/me` gets 401 and sends the browser to `/`.
- Evidence: `E/F001/failure.png`, `E/walk/F001-walk.png`, `E/test-output.txt`, `E/rerun/F001-output.txt`, `E/cause/requests-and-responses.txt`

### 7. Changing the display name says "Saved!" and saves nothing [FLOW_BROKEN] [P1]
- Flows: F029 Owner changes their display name and sees it everywhere; F031 ...and it is still there next time they log in
- User did: Alice opened Settings, changed the name to "Alice Smith", clicked Save, then clicked Dashboard. (F031: logged out and in again.)
- Expected: "The new name shows everywhere and is still there next time you log in" (PRD).
- Got: "Saved!" and the sidebar switches to "Signed in as Alice Smith" - until the next page, which says "Welcome back, Alice" and "Signed in as Alice". Settings shows "Alice" again. Same after logging in again. Database: name is still "Alice".
- Breaks at: step 2, server. `PUT /api/settings {"name":"Alice Smith"}` answered 200 `{"ok":true,"name":"Alice Smith"}` but changed no row: server.js:80 passes (user id, name) to `UPDATE users SET name = ? WHERE id = ?`, i.e. the wrong way round. The page updates the sidebar from the response, which is why it looks saved.
- Evidence: `E/F029/failure.png`, `E/F031/failure.png`, `E/walk/F029-walk.png`, `E/walk/F031-walk.png`, `E/test-output.txt`, `E/rerun/F029-output.txt`, `E/rerun/F031-output.txt`, `E/cause/requests-and-responses.txt`

### 8. My Tasks never finishes loading for a user with no tasks [SOFTWARE_BUG] [P1]
- Flow: F025 New user with no tasks sees a friendly "no tasks yet" message on My Tasks
- User did: Carol (no projects, no tasks) logged in and clicked My Tasks.
- Expected: a friendly "no tasks yet" message (PRD).
- Got: "Loading…" forever. Page error: `Failed to execute 'json' on 'Response': Unexpected end of JSON input`. Every brand-new user hits this.
- Breaks at: step 1, between server and page. `GET /api/my-tasks` answers 204 with an empty body when there are no tasks (server.js:121); the page calls `res.json()` on it (public/my-tasks.html) and throws before it can show its "No tasks yet" text.
- Evidence: `E/F025/failure.png`, `E/walk/F025-walk.png`, `E/test-output.txt`, `E/rerun/F025-output.txt`, `E/cause/requests-and-responses.txt`, `E/nav-sweep/nav-sweep.txt`

### 9. "Forgot password?" does nothing [MISSING_FEATURE] [P1]
- Flow: F009 Owner who forgot their password resets it by email from the login page
- User did: opened the login page and clicked "Forgot password?" (twice in the hand walk).
- Expected: "If you forget your password you can reset it by email from the login page" (PRD).
- Got: nothing. The screen is identical before and after, the address gains a `#`, no request is made. A user who forgets their password is locked out for good.
- Breaks at: step 1, page. The link is `<a href="#" id="forgot">` with no handler (public/index.html), and the server has no reset route and no code that sends email.
- Evidence: `E/F009/failure.png`, `E/walk/F009-walk.png`, `E/test-output.txt`, `E/rerun/F009-output.txt`

### 10. There is no way to reach the Team page [MISSING_FEATURE] [P1]
- Flow: F026 Owner invites a teammate from the Team page in the sidebar
- User did: Alice logged in and looked for "Team" in the sidebar.
- Expected: "Invite teammates by email from the Team page in the sidebar" (PRD).
- Got: the sidebar has Dashboard, Projects, My Tasks, Reports, Settings, Log out. No Team item there or on any page, for any of the three accounts.
- Breaks at: step 1, page. A Team page exists at `/team.html` and works when the address is typed (F027 passes: "Invite sent.", the address is listed and saved), but the menu list in public/app.js:17-23 has no entry for it. Whether an invited person ever receives an email could not be checked (F028 blocked); nothing in the code sends one.
- Evidence: `E/F026/failure.png`, `E/walk/F026-walk.png`, `E/F027/final.png`, `E/test-output.txt`, `E/rerun/F026-output.txt`

### 11. Creating a project with an empty name fails silently with a server error [SOFTWARE_BUG] [P1]
- Flow: F011 Owner leaves the project name empty and is told a name is required
- User did: Alice opened Projects, left the name empty, clicked Create project.
- Expected: "If you leave the name empty you are told a name is required" (PRD).
- Got: nothing happens on screen: no message, no browser prompt. No project is created (that part is right).
- Breaks at: step 2, server and page. `POST /api/projects {"name":""}` answered 500 `{"error":"Internal error"}`; server log: `[error] POST /api/projects: CHECK constraint failed: length(trim(name)) > 0`. The route (server.js:93-97) does not validate the name, and the page (public/projects.html) does nothing when the answer is not ok.
- Evidence: `E/F011/failure.png`, `E/walk/F011-walk.png`, `E/test-output.txt`, `E/rerun/F011-output.txt`, `E/cause/requests-and-responses.txt`, `.userflow/runs/20261117T081226Z-539f506/raw/server-evaluate.log`

### 12. Another user's task rows are offered with working-looking Delete and tick, and no refusal [FLOW_BROKEN] [P0]
- Flow: F039 Another account holder cannot delete or tick someone else's tasks
- User did: Bob, on Alice's project page (finding 1), clicked Delete beside "Book photographer" and ticked "Write homepage copy". Alice then opened the project in her own browser.
- Expected: no rows to act on, or a refusal in words; Alice's tasks unchanged.
- Got: **Alice's tasks were not changed** - all 3 are there and unticked for her, and the database rows are unchanged. What fails is the other half: Bob is shown her rows, Delete does nothing with no explanation, and the tick shows as done on his screen.
- Breaks at: step 2, page. `DELETE /api/tasks/3` answered 404 (the server does check the owner here, server.js:127-130) and the tick went to the missing `/complete` route (finding 4). The page shows neither answer. Note: the tick is only refused because ticking is broken for everyone; once finding 4 is fixed this flow must be rechecked.
- Evidence: `E/F039/failure.png`, `E/walk/F039-walk.png`, `E/test-output.txt`, `E/rerun/F039-output.txt`, `E/cause/requests-and-responses.txt`

### 13. Double-clicking "Create project" makes two projects [FLOW_BROKEN] [P2]
- Flow: F012 Owner double-clicks "Create project" and still gets one project
- User did: typed "Offsite" and double-clicked Create project.
- Expected: one "Offsite" (not stated in the PRD; what a reasonable user expects).
- Got: two "Offsite" rows in the list and two rows in the database. There is no way to delete a project, so the duplicate stays.
- Breaks at: step 2, page. Two submits send two `POST /api/projects`; the button is not disabled while the first is in flight.
- Evidence: `E/F012/failure.png`, `E/walk/F012-walk.png`, `E/test-output.txt`, `E/rerun/F012-output.txt`

### 14. A task title of only spaces is refused without a word [FLOW_BROKEN] [P2]
- Flow: F017 Owner submits a task title that is only spaces and is told a title is needed
- User did: on "Hiring", typed three spaces in "New task" and clicked Add task.
- Expected: a message that a title is needed (not stated in the PRD; reasonable expectation).
- Got: nothing changes and nothing is said; the spaces stay in the field. No task is created (that part is right).
- Breaks at: step 2, page. `POST /api/tasks` answered 400 `{"error":"Title is required."}`; the page (public/project.html:41) only acts when the answer is ok.
- Evidence: `E/F017/failure.png`, `E/walk/F017-walk.png`, `E/test-output.txt`, `E/rerun/F017-output.txt`, `E/cause/requests-and-responses.txt`

### 15. "Reports" in the sidebar is a dead end [FLOW_BROKEN] [P2]
- Flow: F038 Owner opens Reports from the sidebar
- User did: clicked "Reports" in the sidebar.
- Expected: a page (the PRD never mentions reports, but the menu offers it).
- Got: a blank white page with the words "Not found", no sidebar, no link back. Same for all three accounts.
- Breaks at: step 1. public/app.js:21 links to `/reports.html`; no such file exists; the server answers 404.
- Evidence: `E/F038/failure.png`, `E/walk/F038-walk.png`, `E/test-output.txt`, `E/rerun/F038-output.txt`, `E/nav-sweep/nav-sweep.txt`

## Navigation

Swept on the evaluate run as alice, bob and carol (`E/nav-sweep/nav-sweep.txt`,
screenshots beside it). The sidebar is identical for all three.

| Nav item | Opens | Result |
|---|---|---|
| Dashboard | /dashboard.html | works |
| Projects | /projects.html | works |
| My Tasks | /my-tasks.html | works for alice and bob; stuck on "Loading…" with a page error for carol (no tasks) - finding 8 |
| Reports | /reports.html | dead: bare "Not found", 404 - finding 15 |
| Settings | /settings.html | opens (saving is broken - finding 7) |
| Log out | / (login page) | works; the dashboard address then redirects to login |
| Team (promised in the PRD) | - | item does not exist - finding 10 |
| Login page: "Forgot password?" | - | dead: nothing happens - finding 9 |
| Login page: "Create an account" | /signup.html | works |
| Sign-up page: "Log in" | / | works |
| Project page: "← All projects" | /projects.html | works |

Pages with no way in: `/team.html` (Team page with a working invite form).
Promised but not found: password reset by email; "Team" in the sidebar; the "name is required" message for an empty project name; any invite email.

## Errors seen along the way

Console errors, failed network calls and server log errors seen during
flows, including flows that passed.

| Where | Error | Flow |
|---|---|---|
| Server log | `[error] POST /api/projects: CHECK constraint failed: length(trim(name)) > 0` (once per empty-name attempt; 4 times in this run: full run, rerun, hand walk, cause probe) | F011 |
| Browser, My Tasks | page error `Failed to execute 'json' on 'Response': Unexpected end of JSON input` after `GET /api/my-tasks -> 204` | F025, F019, nav sweep (carol) |
| Network | `POST /api/tasks/<id>/complete -> 404` on every tick or untick | F020, F021, F022, F039 |
| Network | `POST /api/projects -> 500` | F011 |
| Network | `GET /reports.html -> 404` | F038, nav sweep |
| Network | `GET /api/me -> 401` straight after a successful sign-up | F001, F004 |
| Browser, every first page load | console error for `GET /favicon.ico -> 404` (seen in preflight and in the walks; cosmetic) | all |
| Network, expected refusals in flows that passed | `POST /api/signup -> 409` (F002), `-> 400` (F003); `POST /api/login -> 401` (F007); `PUT /api/settings -> 400` (F030); `GET /api/me -> 401` when logged out (F008, F035) | F002, F003, F007, F008, F030, F035 |

No flow that passed produced an unexpected error. The server does not log
requests, so the server log can only show crashes.

Seen in the hand walk and not counted as failures:
- After sign-up there is no confirmation of any kind; the user cannot tell whether the account was made.
- After a quick add the project choice silently jumps back to the first project.
- Delete removes a task at once, with no confirmation and no undo.
- My Tasks is read-only: no tick, no delete, no link to the task's project.
- Nothing lets a user rename or delete a project, edit a task title, change their password or delete their account. The PRD does not promise these.
- Login, sign-up, project, task and invite fields have placeholders but no labels; "done" and "you are here" are shown only by styling.

## Not verified

| Flow or surface | Why | What would be needed |
|---|---|---|
| F028 Invited teammate receives the invite by email (S073) | No mailbox or mail catcher in this environment; the product documents no mail setup. (Reading the code, nothing sends email - not a verified result.) | A local mail catcher wired to the product, and the product actually sending mail |
| Last step of F009 (receive reset email, set new password) | Same gap; the flow fails earlier anyway | Same |
| Email side effect of F026 / F027 | Same gap | Same |
| Tick refusal in F039 once ticking works | Today every tick fails (finding 4), so "Bob cannot tick Alice's task" is true for the wrong reason | Recheck after finding 4 is fixed |
| Browsers other than desktop Chrome; phone-size screens | Only installed Google Chrome was driven | Other browsers / device emulation |
| Two people using one account at the same time; session expiry | Not in the PRD; no flow written | A stated intent for sessions |
| Review of the surface map and flow list | Mode was auto: no human checked them | A human pass over `.userflow/flows.yaml` |

## Stubs and limits

- No stubs. Nothing of this product, and no third-party service, was faked.
- F027 types the address `/team.html` on purpose: the page has no way in, and the flow exists to tell the builder the page itself works. F033, F034, F035 and F039 type addresses on purpose: that is the "not allowed" action being tested.
- "What was saved" was checked by reading `tasklet.db` read-only, and by return visits in a fresh browser session where the flow calls for it.
- The first full test run of this session was discarded: the hand walk showed my helper for "wait until the product has answered" returned too early (TEST_DEFECT in the tests, not in the product). It was fixed and everything was rerun from a clean start; the results did not change. The discarded output is kept in `E/discarded-first-run/`.
- This run cannot judge security beyond the flows above (password storage, cookie flags, rate limiting), performance, or accessibility.
