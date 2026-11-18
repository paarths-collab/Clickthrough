---
name: uf-patterns
description: What actually breaks for users, and how to see it. A catalogue of the ways products fail between frontend, backend, database, background jobs, email and MCP tools, each with the check that exposes it by using the product. Use when checking whether something works, before calling a feature done, when asked to find what is broken, and when writing user-flow tests.
---

# What breaks for users, and how to see it

Code review finds code that looks wrong. Users hit code that looks right
and does the wrong thing, because the break is *between* two parts that
are each fine on their own. This is the list of those breaks.

## The one method under all of it

Take one thing a user does and follow it through every part it touches:

```
click → request → handler → saved data → whoever reads it next → what a person sees
                                          (other page, other user, worker, email, MCP)
```

Check each arrow by using the product, not by reading the code. Most of the
patterns below are one arrow failing.

Judge by the **result**, never the message. "Saved!", "Task added!" and a
green tick are written by the page. The result is what is still there
after a refresh, what the other user sees, what the email says, what the
database holds.

## Any kind of product, any language

The examples below say page, click and email because web apps are common.
The language does not matter; the kind of product does. Translate:

| Product | The user's door (drive it through this) | Its "menu" | "Come back later" | The result to check |
|---|---|---|---|---|
| Web app | browser | nav, sidebars, links | refresh, log in again | screen, saved data, emails |
| Service / API | HTTP, gRPC, socket client | API docs, schema | new connection or token | response, saved data |
| CLI tool | run the command in a shell | `--help`, docs | run it again, new shell | stdout, stderr, exit code, files |
| Library / SDK | install the package into a fresh project and call it | docs, README examples | new process | return values, errors, files |
| Desktop / mobile app | the app's UI (UI automation or by hand) | menus, screens | quit and relaunch | screen, files, app data |
| Embedded / firmware | buttons, serial, USB, network; emulator or real board | manual, commands | power cycle | device behaviour, output |
| Data pipeline / batch | feed input, trigger a run | job list, docs | run again on same input | output data, counts, rejects |

Use whatever tool fits the door. Use the project's own language and test
runner when they can drive it.

A few breaks that only show outside the web:

- **Says it failed or worked wrongly in its exit code.** Exit 0 on error;
  errors printed to stdout and breaking pipes.
- **Works only on the author's machine.** Hard-coded paths, runs only from
  the repo folder, missing step for a clean install or build.
- **Works from source, not when installed.** Files or exports missing from
  the published package; README example fails against it.
- **Crashes instead of reporting.** Panic, segfault or uncaught exception
  where the user needed an error they can act on. For native code, run the
  flows on a sanitizer or debug build too.
- **Interrupted mid-way leaves a mess.** Ctrl-C, crash or power loss leaves
  a half-written file, a stale lock, or a second run that behaves
  differently.

## A. The page and the server disagree

1. **Different names for the same thing.** Page sends `projectId`, server
   reads `project_id`; email link has `?token=`, page reads `?t=`; page
   sends `Admin`, server wants `admin`; page asks for `per_page`, server
   reads `limit`. User sees success and a wrong or empty result.
   *Check:* do it in the UI, then look at what was saved. Open the item
   again from somewhere else.
2. **Wrong endpoint or method.** Page calls a route that does not exist and
   ignores the 404. *Check:* watch network calls during every flow; any
   4xx/5xx the user was not told about is a finding.
3. **Errors swallowed.** Server refuses (400, 500), page shows nothing or
   shows success. *Check:* send empty, too long, spaces only, wrong format.
   The user must be told why, in words.
4. **Odd response shapes.** Empty list sent as 204 with no body, missing
   field, null. Page throws and sits on "Loading…". *Check:* a brand-new
   account with no data on every screen.

## B. It says it worked and it did not

5. **Not saved.** Wrong parameter order, wrong row, wrong table. Page shows
   the new value from its own memory. *Check:* refresh, log out and back
   in, open in a fresh browser.
6. **Looks done on screen only.** Checkbox ticks, row strikes through, the
   server call failed. *Check:* refresh, then look from a list or count
   elsewhere.
7. **Double submit.** Double-click makes two. *Check:* double-click every
   create button.

## C. Who can see and do what

8. **Writes are checked, reads are not.** Another user's item opens by
   changing the id in the address. *Check:* with a second account, change
   every id in every address and call the API for it directly.
9. **Hidden is not protected.** Page is missing from a role's menu but
   opens when typed; an endpoint (export, settings, admin) only checks for
   a login. *Check:* for every page and endpoint of a higher role, try it
   as each lower role and as a logged-out visitor.
10. **Leaks through a side door.** The screen hides it, but the email, the
    export, the raw API response or the MCP tool shows it (internal notes,
    other customers' emails). *Check:* as the least-trusted user, read
    every email they get and every raw response their pages receive.
11. **Role or option lost on the way.** Invited as admin, joins as agent;
    chose Urgent, saved as normal. *Check:* pick the non-default option in
    every select, then look at what was stored and what the user can do.

## D. One goal, several routes

12. **One route works, another is broken.** Add from the project page
    works, quick-add does not; logged-in "new ticket" works, "contact us"
    drops the message; the UI works, the MCP tool does not. *Check:* list
    every way to reach each goal (pages, shortcuts, bulk, forms for
    visitors, API, MCP, CLI) and run each one to the end.
13. **Side effects on one route only.** "Send" emails the customer, "Send
    and close" does not; single close emails, bulk close does not.
    *Check:* run every route of a goal and compare the side effects, not
    just the screen.

## E. Side effects: email, notifications, webhooks

14. **Missing.** The promised email never goes out. *Check:* after every
    action that promises one, open the inbox (or mail catcher, or outbox)
    and read it.
15. **Sent when it must not be.** Internal note emailed; "notify" switched
    off and still notifying. *Check:* actions that must stay quiet.
16. **Wrong content.** Link in the email points to the wrong page or
    parameter. *Check:* click every link in every email, as the recipient.
17. **A setting nothing reads.** The switch saves and changes nothing.
    *Check:* flip each setting, then do the action it is meant to govern.

## F. Background jobs and time

18. **Wrong clock.** Job measures from creation instead of last activity,
    or the reverse. *Check:* make data that is old by one measure and new
    by the other, then wait for the job.
19. **One bad record kills the job.** Worker throws and exits; nothing
    restarts it; every later email or task silently stops. *Check:* feed
    one bad input (invalid address, missing field), then confirm that an
    unrelated side effect later still happens, and that the process is
    still alive.
20. **Job result never visible.** It runs, but no page shows the change.
    *Check:* look from the user's screen after the job runs.

## G. Lists, counts, search, bulk

21. **Count and list disagree.** Card says 9, the list it links to has 5.
    *Check:* click every number and count what opens.
22. **Paging wrong.** 25 rows on "page 1 of 3", later pages empty.
    *Check:* page to the end; the total of all pages must equal the count.
23. **Search misses.** Case-sensitive, subject only, exact match only.
    *Check:* search lower case, upper case, a word from the body.
24. **Bulk hits the wrong items.** Loop over positions instead of ids.
    *Check:* select items that are not first in the list; check which ones
    changed, including the ones you did not select.
25. **Filter ignored.** *Check:* every filter returns only matching items.

## H. Lifecycle and state

26. **Account flows broken end to end.** Signup does not log in, reset link
    always invalid, invite joins with the wrong role, link works twice.
    *Check:* a brand-new person, from the first email or form to doing the
    main thing, then log out and back in.
27. **Status change not applied.** Reply should reopen and does not.
    *Check:* after the action, look from the other role's screen.
28. **Cleanup missing.** Deactivated user's items stay assigned to nobody
    who can act; deleted parent leaves orphans the UI cannot open.
    *Check:* after removing something, look for what depended on it.

## I. Tools for AI agents (MCP, API, CLI)

29. **Schema says one name, handler reads another.** `internal` vs
    `is_internal`, `status` vs `state`. The tool says ok and does the
    wrong thing. *Check:* call every tool with every documented parameter
    and verify the effect, not the "ok".
30. **Tool makes data the UI cannot show.** Created with a missing owner;
    the page then errors. *Check:* open everything a tool created in the UI.
31. **Promised tool missing.** *Check:* compare `tools/list` with the docs.

## J. The software itself

32. **Does not start, or does not stay up.** Missing step in setup, one
    process of several not started, crash after the first request.
    *Check:* from a clean copy, follow the README exactly; then confirm
    every process is still running after the flows.
33. **Bad input crashes the server.** 500 instead of a message; validation
    on one route missing on another. *Check:* the same bad input on every
    route that accepts it.

## K. Promises and navigation

34. **Promised, not there.** Brief says "reset by email", link does
    nothing. *Check:* read the brief or README line by line and find each
    promise in the running product.
35. **Dead ends.** Menu item opens a 404; a working page has no link.
    *Check:* click every menu item as every role; list pages with no way in.

## L. Everyone can use it (accessibility and layout)

36. **Keyboard only.** Every flow can be done with Tab, Enter, Space and
    Escape; focus is visible and lands somewhere sensible after a dialog.
    *Check:* walk the P0 flows without a mouse.
37. **Screen readers.** Inputs have labels, buttons have names, images
    have alternatives, errors are announced. *Check:* read the
    accessibility tree, or run an automated checker (axe, pa11y,
    Lighthouse) on each main screen.
38. **Phone width and zoom.** At 375 px wide and at 200% zoom nothing is
    cut off or needs sideways scrolling, and buttons can be tapped.
    *Check:* run the P0 flows at phone size.

## M. Existing users after an update

39. **Old data, new code.** Records created before a migration still open,
    edit and show correctly. *Check:* seed with the previous version (or
    old-shaped data), upgrade, run the flows.
40. **Old links and sessions.** Bookmarks, links in old emails and
    signed-in sessions survive a deploy. Old clients (mobile apps, CLI
    versions, API consumers) against the new server still work or get a
    clear message.

## Before you say anything works

Ask, for each goal you checked:

- Did I see the result, or only the message?
- Did I look from the other side (refresh, other user, other role, email,
  database)?
- Did I try every route to it?
- Did I try it with nothing (new account) and with something wrong?
- Is every process still alive afterwards?

If any answer is no, that goal is **not verified**. Say so.
