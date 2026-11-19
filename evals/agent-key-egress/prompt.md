---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

Security review this. Our invoicing app lets customers connect an AI assistant. The assistant gets one API key per account with every scope that is not personal, including `exports:write`. Our rule: an assistant may draft invoices, but anything that changes controls or sends data out of the product needs a human. The general admin gate refuses assistant keys. This is the gate for scheduled exports, which push every new invoice (with customer names, addresses and amounts) to any SFTP or HTTPS address:

```python
def gate_scheduled_exports(request, scope):
    caller = authenticate_with_scope(request, scope)   # accepts sessions and API keys with the scope
    if caller.kind == "api_key":
        require_key_created_by_admin(caller)          # the key's creator is an admin
    return caller
```
What is the risk, how serious is it, and how would you test it? Be brief.
