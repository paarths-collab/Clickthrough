---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

Review this code from a web app for software issues. All user-facing flows using it currently "work" (no errors shown). Be brief: list the issues, how serious each is, and how you would prove each one.

```ts
// audit.ts
export async function recordAction(db, actorTool: string, action: string) {
  try {
    await db.query("INSERT INTO audit_log (actor_id, action) VALUES ($1, $2)", [actorTool, action]);
  } catch (e) {
    console.debug("audit skipped");
  }
}

// retention.ts  (runs once a day)
const BATCH = 2000;
export async function purgeOldAuditRows(db) {
  await db.query("DELETE FROM audit_log WHERE id IN (SELECT id FROM audit_log WHERE created_at < now() - interval '400 days' LIMIT $1)", [BATCH]);
}

// schema: audit_log.actor_id is uuid NOT NULL
```
