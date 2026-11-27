# Service double contracts and failure scenarios

The email presets reject missing required fields. They are minimal local
contracts, not full vendor validators. Check real SDK/provider behavior against
a sandbox before claiming integration readiness.

Explicit configured routes override presets, so a test can induce failure on a
normally successful preset route:

```yaml
redact_keys: [email, customer_name]
redact_patterns: ['synthetic-private-[A-Za-z0-9]+']
routes:
  - method: POST
    path: /emails
    required: [from, to, subject]
    responses:
      - status: 429
        headers: {Retry-After: '1'}
        json: {error: rate_limited}
      - status: 200
        delay_ms: 100
        json: {id: mail_1}
  - method: POST
    path: /hooks/*
    responses:
      - disconnect: true
      - status: 200
        json: {ok: true}
```

A sequence advances atomically per matching route; its last response repeats.
`DELETE /_uf/requests` resets requests, inbox and sequence counters. Delays are
bounded to 60 seconds. Required fields are checked for presence. The product's
retry/backoff, idempotency and visible error handling are what the test asserts.
Custom email routes return scripted answers; they do not deliver to the preset
inbox. Inspect recorded requests to check their recipients and contents.

Recorded requests redact common credential fields recursively, query tokens,
known credential patterns and configured private fields/patterns. The in-memory
inbox retains original test message links so tests can follow them. Use synthetic
data, bind to loopback, and keep recordings private. Export only reviewed,
sanitized derivatives with `ct.py export`.
