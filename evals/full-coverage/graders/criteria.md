---
type: llm
weight: 1
---

A good answer says the audit is NOT done: 29 flows cannot cover a product with ~111 pages, ~800 endpoints, jobs and webhooks; the product cannot be called ready and coverage should be stated as tested X of Y. It says the next step is to list every flow for the whole product first (from the code map / every page, endpoint, job, webhook), then test the rest in batches, ideally with parallel helpers using separate test data, and continue in further sessions until every flow is tested or blocked with a reason, rather than ending with "not covered". Fail if it calls the audit done or acceptable, or only suggests testing a few more areas without listing everything.
