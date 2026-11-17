# Helpline

A shared support inbox for small teams. See `PRD.md` for what it does.

Needs Node 22.13 or newer. No packages to install.

## Run it

```bash
npm run seed
```

```bash
npm start
```

`npm start` runs two processes: the web app on http://localhost:4280 and
the background worker, which sends queued email and closes stale pending
tickets. `npm run web` and `npm run worker` start them one at a time.
`PORT` changes the port.

`npm run reset` puts the data back to the seeded state. It is safe to run
while the app is up.

## Accounts

Every seeded account has the password `helpline123`.

| Role | Email |
|---|---|
| Admin | mira@helpline.test |
| Agent | alice@helpline.test |
| Agent | bob@helpline.test |
| Customer | dana@customer.test |
| Customer | eli@customer.test |

## Email in development

Nothing is really emailed. Mail the worker has sent is listed at
http://localhost:4280/dev/mail, newest first.

## MCP server

```bash
HELPLINE_TOKEN=<an agent's API token> npm run mcp
```

It speaks MCP over stdio (newline-delimited JSON-RPC) and uses the same
database as the web app. Each agent's token is on the "API token" page.

## Tests

```bash
npm test
```

## Files

| File | What |
|---|---|
| `server.js` | Web app and JSON API |
| `worker.js` | Background worker |
| `mcp-server.js` | MCP server |
| `dev.js` | Starts web and worker together |
| `db.js`, `lib.js` | Database and helpers |
| `seed.js` | Seed and reset |
| `public/` | Pages |
