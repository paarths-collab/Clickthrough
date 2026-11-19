---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

Review this code from an online shop for software issues. All user-facing flows using it currently "work" (no errors shown). Be brief: list the issues, how serious each is, and how you would prove each one.

```python
# events.py
def record_order_event(db, customer_email, event):
    try:
        db.execute("INSERT INTO order_events (customer_id, event) VALUES (%s, %s)", (customer_email, event))
    except Exception:
        log.debug("event not stored")

# cleanup.py  (runs once an hour)
LIMIT = 500
def delete_expired_carts(db):
    db.execute("DELETE FROM carts WHERE id IN (SELECT id FROM carts WHERE updated_at < now() - interval '30 days' LIMIT %s)", (LIMIT,))

# schema: order_events.customer_id is integer NOT NULL; carts hold names, addresses and items
```
