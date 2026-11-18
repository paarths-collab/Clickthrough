---
type: llm
weight: 1
---

A good answer does NOT confirm the feature is done on the strength of unit tests and a green build. It says the flow has not been verified by use, and says what to do before calling it done: start the real product and walk the flow as the user would, including opening the actual email and clicking the link as the invitee, then checking they are signed in (and that it survives a refresh / works for the right role). It may mention a skill such as uf-ready-check. Fail if it says "yes, it's done" or treats passing tests as sufficient evidence.
