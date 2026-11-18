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

For a product with hundreds of surfaces, list area by area, but finish the
list for every area before any testing starts. Commit the registry when the
list is done, so a later session can pick it up.
