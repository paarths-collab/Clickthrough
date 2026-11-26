<!-- clickthrough:start -->
## Readiness rules (Clickthrough)

- Never say a project or feature is "ready", "done", "working" or "complete"
  unless a user-flow report exists for the current commit in
  `.clickthrough/runs/` with every P0 flow passing with evidence. If there is no
  such report, say exactly what has and has not been verified by using the
  product.
- Passing unit tests, a clean build, or code that "should work" are not
  evidence that a user can use the product.
- After building or changing anything, and before saying it is done or
  fixed, run the `ct-ready-check` skill: start the real product and walk
  the user flows you touched. Report what was verified by use and what
  was not.
- While building, follow the "While you build" list in `ct-ready-check`
  (one name per field everywhere, every caller of a changed route, every
  setting has a reader, every route to a goal gets the same checks and
  side effects).
- The session that built or changed the product does not give the release
  verdict. That runs in a separate, fresh session using the `ct-run`
  skill.
- To check readiness or find what is broken for users, use the `ct-run`
  skill (it includes security checks from `ct-security`). To fix what an
  audit found, use `ct-fix`, then a fresh `ct-run recheck`. What to look
  for is in the `ct-patterns` skill; rules are in `.clickthrough/guide.md`.
<!-- clickthrough:end -->
