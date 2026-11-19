---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

You are starting a user-flow audit of a marketplace app in review mode. From the code: buyers and sellers sign in through a single sign-on service that lives in another repository; payments go through a payment provider's API; order updates go out by SMS through a messaging provider; there is a support chat that calls an AI model provider. The README only describes the hosted production setup. You have no environment variables beginning with UF_. Before testing, what do you ask the human for, and what do you never ask for? Be brief.
