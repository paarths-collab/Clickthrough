<!-- user-flow-qa:start -->
## Readiness rules (user-flow QA)

- Never say a project or feature is "ready", "done", "working" or "complete"
  unless a user-flow report exists for the current commit in
  `.userflow/runs/` with every P0 flow passing with evidence. If there is no
  such report, say exactly what has and has not been verified by using the
  product.
- Passing unit tests, a clean build, or code that "should work" are not
  evidence that a user can use the product.
- The session that built or changed the product does not evaluate it.
  Evaluation runs in a separate, fresh session using the `uf-run` skill.
- To check readiness or find what is broken for users, use the `uf-run`
  skill. Rules for that work are in `.userflow/guide.md`.
<!-- user-flow-qa:end -->
