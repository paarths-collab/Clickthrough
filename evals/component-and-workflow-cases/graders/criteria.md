---
type: llm
weight: 1
---

A good answer covers BOTH levels (stating up front what the component and workflow are is a plus, not required):
(a) the dialog: email input classes and boundaries (empty, invalid, duplicate/already a member, already invited, very long, different case), role choice (Member and Admin both persisted correctly), who may use it (member refused, logged out, other workspace), seat limit (9→10 allowed, 11th refused with a message), double submit, cancel;
(b) the whole workflow: the paths (accept, ignore, link expired after 7 days, link used twice, invite revoked before acceptance, invitee already has an account, opened on another device or signed in as someone else), and checks at the handoffs (the email actually arrives with a working link, the invitee lands signed in, with the invited role, in the right workspace; the seat count updates; the admin sees the new member).
It explains how it limits the combinations (each value at least once, pairwise, full combinations only for risky ones such as permissions and seat limits) rather than claiming to test every permutation. Fail if it covers only the dialog, only the happy path, or never addresses the role surviving to the end of the workflow.
