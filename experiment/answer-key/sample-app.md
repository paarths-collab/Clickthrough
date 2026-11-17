# Answer key: sample-app (Tasklet)

Do not let the evaluating agent read this file. Copy `sample-app/` out to a
clean folder before a run (see `experiment/protocol.md`).

Ten planted problems. Each is the kind a code review tends to miss, because
no single file looks wrong. All ten were confirmed in a real browser when
the app was written. The app's unit tests pass and it starts cleanly.

| # | What the user experiences | Where it breaks | Class | Priority |
|---|---|---|---|---|
| 1 | Add a task from the dashboard quick-add: it says "Task added!" and the task never appears anywhere. Adding from the project page works. | Dashboard sends `projectId`; the API reads `project_id`. The task is saved with no project. | INTEGRATION | P0 |
| 2 | Tick a task as done: it looks done, and is not done after a refresh. | The page calls `POST /api/tasks/:id/complete`; the server only has `PATCH /api/tasks/:id`. The 404 is ignored. | INTEGRATION | P0 |
| 3 | "Reports" in the sidebar opens a "Not found" page. | The nav links to `/reports.html`, which does not exist. | FLOW_BROKEN | P1 |
| 4 | The brief says to invite teammates from the Team page in the sidebar. There is no Team item. The page works if you type `/team.html`. | Page exists; nothing links to it. | FLOW_BROKEN | P1 |
| 5 | "Forgot password?" on the login page does nothing. | Link to `#`; password reset was never built. | MISSING_FEATURE | P0 |
| 6 | After signing up, the user is sent back to the login page with no message, instead of landing on the dashboard logged in. | Sign-up does not start a session; the dashboard sees no login and redirects. | FLOW_BROKEN | P0 |
| 7 | A logged-in user can open another user's project and read their tasks by changing the id in the address (`/project.html?id=3`). | `GET /api/projects/:id/tasks` does not check the owner. | FLOW_BROKEN (privacy) | P0 |
| 8 | Create a project with an empty name: nothing happens and no message is shown. | The server passes the empty name to the database, the constraint fails, the API returns 500, the page ignores it. | SOFTWARE_BUG | P1 |
| 9 | Change display name in Settings: it says "Saved!" and shows the new name, and the old name is back after a refresh. | The update's parameters are in the wrong order, so no row changes. | FLOW_BROKEN | P1 |
| 10 | A user with no tasks opens My Tasks: the page stays on "Loading…" forever. | The API answers 204 with no body; the page tries to read JSON and throws. | SOFTWARE_BUG | P1 |

## Things that work (a report calling these broken is a false alarm)

Log in with a seeded account, wrong-password message, log out, logged-out
pages redirect to login, create a project with a name, add a task from the
project page, delete a task, My Tasks for a user who has tasks, sending an
invite from the Team page once you are on it, sign-up validation messages
(bad email, short password, duplicate email).

## Scoring notes

- Count an item as found only if the report describes the user-visible
  problem. Naming the cause is a bonus, not a requirement.
- 4 and 5 can only be found by comparing the product with `PRD.md`.
- 7 needs a second account to notice.
- Other real problems exist (for example, sessions never expire). If an
  agent reports one, check it and score it under `extra_real`.
