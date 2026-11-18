---
name: uf-catalog
description: List every user flow in the whole product before testing any of them - one flow set per page, form, list, endpoint, command, tool and job, from the code map, the navigation and the intent - so the registry shows the full size of the job (often hundreds of flows) and the report can say "tested X of Y". Use in uf-run before testing, or when asked to list all flows, all test cases or the full test plan.
---

# List everything first, test after

An audit that tests the flows it happens to think of will look complete at
29 flows when the product has 300. So the list comes first, for the whole
product, and testing works through it. Listing is cheap; skipping is not.

## Inputs

- `.userflow/inventory.json` from `uf-inventory.py --json` (run it if it is
  missing): every page, endpoint, command, agent tool, job and webhook in
  the code, with file and line.
- The navigation as each role sees it (from `uf-discover`).
- The intent: README, spec, docs, promises in the UI.

## 1. Every entry point becomes a surface

Every inventory item of kind page, route, cli, mcp_tool, job or webhook
must belong to a surface in `.userflow/flows.yaml`. Group sensibly: one
surface for "Projects list" can cover `GET /api/v1/projects` and its page.
Record what a surface covers in `covers:` (paths, globs or tool names, for
example `["/projects", "GET /api/v1/projects*"]`). Items that are not for
users (health checks, internal build hooks) get a surface with
`excluded: <reason>`. Nothing is left out silently.

`uf-check.py --stage flows` compares the registry with the inventory and
lists every entry point no surface covers.

## 2. Every surface gets its standard flows

Write the flows each kind of surface always needs, then add the ones its
own rules and the intent call for. Standard sets:

| Surface | Flows |
|---|---|
| List / table | open from the menu; empty; one; many with paging to the end; search; each filter; sort; open an item; as each role |
| Create form | valid; each invalid input; cancel; double submit; result visible in the list and after refresh |
| Detail / edit | open; edit and save; each status change; delete (and what depends on it); as a role that may not |
| Settings | change each setting and see the behaviour it governs change; refused for roles that may not |
| Endpoint | each method as each kind of caller (role, other tenant, logged out, API key, agent); bad input; result readable through the UI |
| Agent tool / CLI command | each documented parameter; bad input; effect visible in the UI; refused when it must be |
| Job / schedule | runs on time; does the right thing; a bad record does not stop it; result visible to the user |
| Webhook in | valid and forged signature; duplicate delivery; result visible |
| Email / notification | arrives; right person; right content; every link works for the recipient |

Then every goal from the intent as a whole workflow (`uf-cases`, section 6)
and every `uf-security` check that applies, as `abuse` flows.

## 3. Prioritise, do not cut

Mark each flow P0, P1 or P2 (money, permissions, data loss, sign-in and
the product's core job are P0). Priority decides the order of testing, not
whether a flow is listed.

## 4. Done when

- `uf-check.py --stage flows` reports no uncovered entry points;
- every flow has a start and steps (short is fine; the test makes it
  exact);
- the summary line shows the total, which is the "Y" in "tested X of Y".

## Listing in parallel

For more than a handful of areas, split the listing across helper agents,
one area each, using the harness's parallel agents (Claude Code subagents,
Codex or Cursor background agents); without them, list the areas one after
another. Listing only reads the code and looks at the product, so helpers
cannot spoil each other's data and can all run at once.

- **Lead first:** run `uf-inventory.py`, walk the navigation, and split the
  inventory into areas (by menu group, folder or feature). Give each area
  an id (`A1`, `A2`, ...).
- **Each helper gets:** its area's inventory items, the navigation for that
  area, the intent sources, this skill and `uf-patterns`, `uf-security`,
  and an id prefix to use (`A3-S01`, `A3-G01`, `A3-F001`) so ids never
  collide. It returns its surfaces, goals and flows as YAML in the
  registry's format. Helpers never write `flows.yaml`.
- **Lead merges:** paste each area's YAML into the registry, join surfaces
  two areas both claimed, add the workflows that cross areas (sign-up then
  first task, invite then accept), then run `uf-check.py --stage flows`
  until no entry point is uncovered.

Finish the list for every area before any testing starts. Commit the
registry when the list is done, so a later session can pick it up.
