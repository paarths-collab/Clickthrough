---
name: uf-flows
description: Phase 3 of user-flow QA. Turn the surface map into the full list of user flows - what each kind of user comes to do, every route to each goal, and the variants (wrong input, not allowed, interrupted, empty state, return visit) - written as user actions and what the user should see. Use after uf-discover, or when asked to list user journeys, user flows, scenarios or acceptance cases for a product.
---

# uf-flows: what will a user try to do?

A flow is one user getting one thing done, from where they start to a
result they can see and that is still there later. You are writing down
every flow a real user would attempt, including the ones where they make a
mistake or do something unexpected, because that is where products break.

Follow `.userflow/guide.md`. Log each step in `decisions.md`. Work from
`.userflow/flows.yaml`; you should not need to read source code here.

## 1. Goals first

For each persona, list what they come to the product to get done, in their
words: "add a task to a project", not "POST /api/tasks". Add each to
`goals:`. Take goals from the intent, not only from the surfaces, so that a
goal the product forgot to build still appears.

## 2. Every route to each goal

Often there is more than one way to do the same thing: a button on the
detail page and a quick-add box on the dashboard, the web UI and an MCP
tool, a form and a bulk import. Users use all of them, and it is common for
one route to work and another to be broken.

For each goal, list every route you saw in the surface map. **Each route is
its own flow** with the same `goal` and a different `route`. Never test one
route and call the goal covered. The report will say "works from the
project page, broken from the dashboard".

## 3. Variants

For each goal, go down this list and write a flow for every variant that
applies. Do not write variants that cannot happen.

| Variant | The user... |
|---|---|
| `normal` | does it the expected way. One per route. |
| `alternate` | does it another valid way (a different route, order or option). |
| `wrong_input` | leaves a field empty, types something invalid, picks a bad file. They should be told what is wrong, in words. |
| `not_allowed` | tries something their role or account should not do, including opening another user's item by changing the address. |
| `interrupted` | refreshes mid-way, presses back, double-clicks submit, closes the tab, or their session expires. |
| `empty` | arrives with nothing yet: new account, no data, no results. |
| `return_visit` | leaves and comes back later (fresh session, log in again): is what they did still there? |
| `handoff` | depends on a second user: invite then accept, submit then approve. |

## 4. Write each flow

Add to `flows:` with every field in the template. The parts that matter
most:

- `start`: where the user really begins, usually logged out at the entry
  page. Not a deep link.
- `steps`: each a `do` (a user action: click, type, choose) and a `see`
  (what the user should then see). Use the labels on the screen. No
  endpoint names, no function names.
- `persisted`: what must be saved, stated so it can be checked: "a task
  with this title under this project".
- `side_effects`: emails, notifications, jobs, calls to other systems.
- `priority`:
  - `P0`: the product is pointless or unsafe without it. Sign-up, sign-in,
    the main thing the product is for, not leaking one user's data to
    another, not losing what a user saved.
  - `P1`: important and used often.
  - `P2`: nice to have, rare, or cosmetic.
- `status: untested`.

Expected results come from the intent. If the intent does not say what
should happen, use what a reasonable user would expect, and record that
judgment in `decisions.md`.

## 5. Check coverage

Run `python3 .userflow/bin/uf-check.py --stage flows` and fix every error.
It enforces:

- every surface appears in at least one flow (or has `excluded: <reason>`),
- every goal has at least one flow,
- every flow has a start and complete steps.

It also prints goals with more than one route. Check that list against
what you saw in the product.

Then check by hand what the script cannot: every navigation item is used
in some flow; every surface tagged `intent` has a flow (it will fail, which
is the point); every persona has a first-visit flow and a return-visit
flow.

## 6. Stop for review (not in auto mode)

Show the human the goals, the routes per goal, flow counts by priority, and
the P0 list in full. Ask: which flows are missing, and are the priorities
right? Their answer is worth more than another pass by you. In auto mode,
skip the stop and record that the flows were not reviewed.

## Large products

Write flows for one area at a time, P0 first. It is fine to finish P0 and
P1 for an area and leave P2 flows listed with steps but untested.
