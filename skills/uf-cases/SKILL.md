---
name: uf-cases
description: Go deep on one component (a screen, form, list, dialog, endpoint, CLI command or agent tool) or one whole workflow (a multi-step journey across components and roles). First understand what it is and does, then list every case and path a user can produce (inputs, states, roles, actions, orders, branches, timing, combinations), choose the set to test with stated reasons, write them as tests and check each one. Use for P0 components and workflows during an audit, when asked for all the test cases or edge cases of something, and before calling a feature done.
---

# Every case a user can produce, for a component or a whole workflow

Flows check that a goal can be reached. This checks that a component, and
a whole workflow, hold up under everything users actually do. Work through
the steps in order; do not start listing cases before you understand the
thing. Components first (sections 1 to 5), then whole workflows (section 6).

## 1. Understand it (the component card)

Write `.userflow/cases/<surface-id>.md`, starting with a card, and check
every line of it against the running product (or the code, if it cannot
run):

- **For:** what a user uses it for, in their words.
- **Who:** every role that can see it, and who must not.
- **Reached from:** every way in (menu, link, deep link, email, API, tool).
- **Inputs:** each field or parameter: type, required or not, limits,
  format, default, and where that rule is enforced (page, server, database).
- **Actions:** every button, key, gesture, option or flag, including cancel,
  back and close.
- **States:** empty, loading, one item, many, at a limit, error, disabled,
  read-only, and the record's own states (draft, active, archived, ...).
- **Reads and writes:** what it loads, what it saves, side effects (email,
  job, webhook, audit row), and which other screens show its result.
- **Rules:** what must always hold, from the intent, docs and validation.

## 2. List the dimensions

| Dimension | Values to cover |
|---|---|
| Each input | valid; each way it can be invalid; boundaries (empty, just under and over each limit, exactly at it); whitespace only; very long; Unicode, emoji, right-to-left; HTML, script and SQL-looking text; leading zeros, negative, decimal; dates across time zones, leap days, past and future; duplicates of an existing value |
| State before | each state from the card |
| Who | each role, another tenant, logged out, API key, AI agent |
| Action | each action, plus cancel, back, refresh, double submit, keyboard only |
| Order | the different orders in which steps can be done |
| Timing | two tabs, two users on the same record, slow or failed network, session expiring mid-way, retry after an error |
| Where | phone width, another browser, other language and locale |
| After | refresh, come back later, the other user's view, the email or side effect, undo |

## 3. Combine without exploding

Write down how many full combinations exist (the product of the value
counts). Testing all of them is rarely possible, so:

- **Every value at least once.**
- **Every pair** of values across dimensions that can affect each other
  (pairwise / all-pairs). Use a generator if one is available (PICT,
  `allpairspy`, a test library's own); otherwise build the pairs by hand.
- **Every combination** where the risk is high: permissions, money,
  deletion, data shared between users.
- **State × action table:** every action in every state, including the
  actions that must be refused in that state.
- **Orders:** all orders of steps that the product lets users do in any
  order, plus the risky orders (delete while someone edits, pay twice,
  submit after the session expired).

Record the numbers: possible, chosen, and why each skipped group is safe
to skip.

## 4. Expected result for each case

From the rules on the card. If the intent does not say, use what a
reasonable user would expect and note it in `decisions.md`. Judge by the
result, not the message (guide: what the user sees, what was saved, it
lasts, side effects).

## 5. Write, run, record

- Write the cases as a table-driven test: one row per case, in
  `userflow-tests/<surface-id>.cases.<ext>`, through the user's door.
- Run them. Record each row's result in the cases file.
- Every failure becomes a flow in `.userflow/flows.yaml` (variant
  `wrong_input`, `interrupted`, `not_allowed`, `abuse`, ...) with its
  finding, so it reaches the report and `uf-fix`.
- Set the surface's `cases:` field in the registry to the cases file.

## 6. Whole workflows

A workflow is a journey across several components, often several people
and some time: sign up → invite a teammate → they accept → they do the
first task; or place an order → pay → ship → return → refund.
Many breaks only show here: each screen works alone, and the handoff
between them does not.

1. **Understand it (the workflow card)**, in `.userflow/cases/<goal-id>.md`:
   the goal; every step, with the component and the role doing it; what
   each step hands to the next (a record, a status, a link, an email, a
   token); where the journey can start; where it ends and what must then
   be true; the time that can pass between steps.
2. **Draw the paths.** Steps as boxes, choices as arrows. List every path
   from each start to each end: every route to the goal, every branch at
   every step (accept or decline, approve or reject, pay or cancel).
3. **Add the ways people leave the path,** at every step: back, refresh,
   abandon and return later, do it on another device, do two steps in the
   other order, skip a step by typing an address, repeat a step, let a
   link or session expire, a different person or role takes the next step,
   someone changes or deletes the record mid-journey.
4. **Combine:** every path at least once; every step × every way of
   leaving it at least once; full combinations where money, permissions,
   deletion or other people's data are involved. Record possible, chosen,
   and why skipped groups are safe.
5. **Check the handoffs.** At each arrow, what the next step receives is
   what the previous step meant to send: the right record, status, role,
   link and session. This is where most workflow breaks are.
6. **Write and run** each path as one end-to-end test through the user's
   door (several browsers or clients when several people take part), and
   record results as in section 5. Failures become flows with findings.

## How deep

- P0 components and workflows: all of the above.
- P1: every value once, boundaries, roles, the state × action table;
  for workflows, every path once and every handoff checked.
- P2: every value once; for workflows, the main path.

For a component that cannot run, list and reason through the cases in
code; failures are `likely_broken` with a confidence.
