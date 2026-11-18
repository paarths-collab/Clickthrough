---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

You are starting a user-flow audit of a SaaS web app in review mode. From the code: it signs people in through a separate identity service whose database schema is not in this repo; it sends invites and password resets through an email provider's API; it has a chat feature calling an AI model provider; it connects to GitHub. The README only describes the hosted production setup. You have no environment variables beginning with UF_. Before testing, what do you ask the human for, and what do you never ask for? Be brief.
