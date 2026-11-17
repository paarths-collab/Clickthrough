---
name: uf-ready-check
description: Quick check by the session that built or changed something, before it says done, ready, working, fixed or complete. Starts the real product and walks the user flows the change touches, the way a user would, and reports what was verified by use and what was not. Use at the end of any build, feature or fix, before claiming it works.
---

# Before you say it is done

You just built this, so you believe it works. That belief is the problem:
the code you wrote looks right to you. Users will not read it; they will
use it. So before you say "done", use it the way they do, through their
door: the browser, the command line, the installed library, the app, the
API, the device. Any language, any kind of product; `uf-patterns` has a
table for translating the web words below. Pick your own tools.

This is not a release verdict. You may say "verified by use" for the flows
you walked. You may not say READY. A full check runs later in a fresh
session with `uf-run`.

## While you build (prevents most breaks)

- One name per field, the same everywhere it crosses a boundary (UI, API,
  database, config, CLI flags, file formats, tool schemas, docs). When you
  rename one, search for all.
- When you add or change a route, find every caller and every reader.
- When you add a setting, find the code that reads it. No reader, no
  setting.
- When you add a second way to reach a goal (shortcut, bulk, visitor form,
  MCP tool), give it the same checks and side effects as the first.
- When you add a permission check to a write, add it to the read.
- Everything new is reachable the way users find things (menu, `--help`,
  docs, exported API), or has a stated reason it is not.
- Every failure reaches the user as something they can act on (a message,
  an error value, a non-zero exit code), not silence or a crash.

## The check (10 to 30 minutes)

1. **Start it for real.** Follow the README as a new user would: install,
   build, and run every part it needs (or install the package into a fresh
   project). If it does not start, say so and stop. Do not report anything
   as working.
2. **List what you touched, as user goals.** In the user's words: "a
   customer resets their password", not "fixed reset handler". Add every
   other route to the same goal (see `uf-patterns`, section D).
3. **Walk each goal as the user.** Start where they start. Do what they
   do. Then check the result, not the message: come back later (refresh,
   rerun, relaunch), look from anyone else who should or must not see it,
   check anything it sends or writes, and look at what was saved.
4. **Try it wrong once.** One wrong input, and, if roles exist, one user
   who must not be allowed. They must be told why, and nothing must leak.
5. **Run the questions.** Load `uf-patterns` and go through the sections
   that match the layers you touched. Each "Check" that applies, do it.
6. **Confirm it is still alive.** Every process still running, no errors
   or crashes in the logs from your flows.
7. **Leave a test behind:** one test per goal you walked, in
   `userflow-tests/`, doing what you did through the same door. Use the
   project's own test runner if it can.

If you find a break, fix it and walk that goal again from step 3.

## What to say

Use exactly these three lists:

- **Verified by use:** goal, route, what you did, what you saw as the
  result.
- **Not verified:** goal or route, and why (no time, no way to see email,
  could not start a process).
- **Found and fixed during the check:** what broke, and that you walked it
  again.

Then: "Built and checked by the same session. Run `uf-run` in a fresh
session for a release verdict."

Never write "should work", "looks correct" or "tests pass" as evidence.
If you did not see it work, it is not verified.
