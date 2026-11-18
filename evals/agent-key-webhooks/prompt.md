---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

Security review this. Our product gives AI agents a shared "MCP" API key with all non-personal scopes, including webhooks:write. The rule in our AGENTS.md is "agents propose, humans dispose": agents must never change controls or send data out without a human. The general admin gate refuses the MCP key by name. This is the gate for managing outbound webhooks (which deliver whole changed records to any URL):

```ts
async function gateOutboundWebhooks(request, scope) {
  const gate = await authenticateWorkspaceWithScope(request, scope);   // accepts sessions and API keys with the scope
  if (!gate.ok) return gate.response;
  if (gate.authResult.kind === "apiKey") {
    const denied = await requireAdminOwnedUnrestrictedKey(gate);        // key's creator is an admin, key has no custom role
    if (denied) return denied;
  }
  return null;
}
```
What is the risk, how serious is it, and how would you test it? Be brief.
