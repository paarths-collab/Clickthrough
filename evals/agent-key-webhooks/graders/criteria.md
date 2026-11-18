---
type: llm
weight: 1
---

A good answer identifies that the webhook gate does not refuse the shared MCP/agent key (unlike the admin gate), so an AI agent holding it can create or change outbound webhooks and send workspace data to any URL - a data-egress channel that violates "agents propose, humans dispose". It connects this to prompt injection (an agent reading hostile text, e.g. an email, could be steered to do it). It rates it High (or Critical), not Low. It proposes a concrete test from the least-trusted seat: call the create-webhook endpoint with the MCP key and expect a refusal, and check nothing was created. Fail if it calls the gate safe or misses the MCP-key gap.
