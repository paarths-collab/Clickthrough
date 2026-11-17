---
name: uf-discover
description: Phase 2 of user-flow QA. Map everything a user can touch in a product - navigation and sidebars, pages, forms, buttons, API endpoints, MCP tools, jobs, notifications, roles and stored data - starting from what the product is meant to do and from the running app's own menus, then from the code. Use after uf-preflight, when asked to inventory or map a product's features or surfaces, or in update mode after the product has changed.
---

# uf-discover: what can a user touch?

You are making the map that every later phase depends on. A flow that is
not on the map never gets tested, so the aim here is completeness, and the
main risk is mapping only what the code happens to contain.

Follow `.userflow/guide.md`. Log each step in `decisions.md`. The product
must be running (see `uf-preflight`).

## Three sources, in this order

The order matters. If you read the code first, you will see the product the
builder made and stop noticing the product that was asked for.

### 1. Intent: what is the product for?

Read the PRD, spec, README, landing-page copy, issue tracker, and anything
the human told you. Write one paragraph in `product.purpose` and list where
it came from in `product.intent_sources`.

From the intent, list who uses the product (personas) and everything it
says they can do. If there is no written intent at all, ask the human for a
short description. If you are in auto mode and cannot ask, write the
purpose from the product's own UI text, and say in the report that intent
was inferred and missing features cannot be detected.

### 2. The running product: what does it show a user?

Open the real product as each persona, starting logged out.

**Read the navigation first.** The sidebar, top bar, menus, tabs, footer and
any "more" or account dropdowns are the product's own summary of what it
offers. They give you the gist faster than any file. For each persona:

- List every navigation item as a surface of type `nav`. Take a screenshot
  of each menu, opened.
- Click every item. Record what it opens in `leads_to`, or `nowhere` if it
  is dead, errors, or lands on an empty or placeholder page.
- Note what differs between personas: items one role sees and another does
  not.
- Compare the menu with the intent. Something in the intent with no menu
  item, or a menu item the intent never mentions, is worth a note.

Then walk each page the navigation opens. Record every form, button, link,
tab, modal, filter, empty state and message as a surface. Follow links into
pages that are not in the menu (detail pages, settings sub-pages, wizards).

### 3. The code: what exists that you did not see?

Now read the code to find what the UI walk missed: routes and pages,
API endpoints, MCP tools, CLI commands, background jobs, scheduled tasks,
webhooks, outgoing email and notifications, roles and permission checks,
and the tables or collections that hold user data.

For every page or screen found in code, work out how a user gets there by
clicking, and record it in `reach` (for example `sidebar > Projects > row`).
If no menu, link or button leads to it, `reach: none`. That is a finding:
the feature exists and no user can find it.

## Record each surface

Add to `surfaces:` in `.userflow/flows.yaml` with `type`, `name`,
`location`, `personas`, `reach`, and `source`:

- `both`: promised in the intent and present in the product. Normal.
- `intent`: promised, and you could not find it. A missing feature. Keep it
  on the map so a flow gets written for it and fails visibly.
- `code`: present, never promised. May be unfinished, leftover, or simply
  undocumented. Note which you think it is.

Also record the personas, with how to become each one (`auth`).

## Large products

If the product has more than a few dozen surfaces, list its areas under
`areas:` first, from the navigation's top level. Map one area fully, mark
it `mapped`, then the next. If you run short of room, stop at an area
boundary and leave the rest `pending`. A complete map of four areas is
worth more than a thin map of ten.

## Update mode

When the registry already exists and the product has changed: compare the
current commit with `last_run.commit` on the flows, read what changed,
re-walk the navigation, and add, change or retire surfaces. Mark flows that
touch changed surfaces `untested`. Do not rebuild the registry from zero.

## Check your work

Run `python3 .userflow/bin/uf-check.py --stage discover` and fix every
error. Then ask yourself, and write the answers in `decisions.md`:

- For each persona, is there a surface for how they first arrive, how they
  sign in, and how they leave?
- For each thing a user can create, can they also see it, change it and
  remove it? Missing ones are surfaces with `source: intent` or notes.
- Did every nav item get clicked, and does every page have a `reach`?

## Then stop for review (not in auto mode)

Show the human a short summary: personas, the navigation as you found it,
counts of surfaces by type, everything tagged `intent` or `code`, dead nav
items, and pages with no way in. Ask what is missing or wrong. They know
things about the product that are written nowhere. In auto mode, skip the
stop and record that the map was not reviewed.
