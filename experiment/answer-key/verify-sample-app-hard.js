#!/usr/bin/env node
// Proves the answer key for sample-app-hard (Helpline) against the real
// running app: every planted problem must show up, and every "works" item
// must work. Drives a real browser, the MCP server over stdio, the mail
// page and the database (read-only).
//
//   NODE_PATH=<folder with playwright>/node_modules node verify-sample-app-hard.js [app-dir]
//
// Keep this file away from any agent being evaluated.
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { chromium } = require('playwright');

const APP = path.resolve(process.argv[2] || path.join(__dirname, '..', '..', 'sample-app-hard'));
const PORT = process.env.VERIFY_PORT || '4391';
const BASE = `http://localhost:${PORT}`;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'helpline-verify-'));
const DB = path.join(tmp, 'verify.db');
const env = { ...process.env, PORT, HELPLINE_DB: DB, BASE_URL: BASE, WORKER_INTERVAL_MS: '300' };
const NODE = [process.execPath, '--disable-warning=ExperimentalWarning'];
const PASSWORD = 'helpline123';
const ALICE_TOKEN = 'hl_agent_alice_8e3b6a1d0c';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let appLog = '';
let app;
let browser;

function reset() {
  const out = spawnSync(NODE[0], [NODE[1], path.join(APP, 'seed.js')], { env });
  if (out.status !== 0) throw new Error(`seed failed: ${out.stderr}`);
}

function db(sql, ...args) {
  const handle = new DatabaseSync(DB, { readOnly: true });
  try { return handle.prepare(sql).all(...args); } finally { handle.close(); }
}
const one = (sql, ...args) => db(sql, ...args)[0];

const unescape = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
async function mails() {
  const html = await (await fetch(`${BASE}/dev/mail`)).text();
  const pattern = /<article class="mail">[\s\S]*?<span class="to">(.*?)<\/span>[\s\S]*?<span class="subject">(.*?)<\/span>[\s\S]*?<pre>([\s\S]*?)<\/pre>/g;
  return [...html.matchAll(pattern)].map((m) => ({
    to: unescape(m[1]), subject: unescape(m[2]), body: unescape(m[3].replace(/<a href="[^"]*">|<\/a>/g, '')),
  }));
}
async function waitMail(match, ms = 4000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const found = (await mails()).find(match);
    if (found) return found;
    await sleep(150);
  }
  return null;
}

async function visitor() {
  const context = await browser.newContext();
  return { context, page: await context.newPage() };
}
async function as(email, password = PASSWORD) {
  const { context, page } = await visitor();
  await page.goto(BASE);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL(/portal|dashboard/);
  return { context, page };
}
const msg = (page, text) => page.locator('#msg', { hasText: text }).waitFor({ timeout: 5000 });

function mcp(token = ALICE_TOKEN) {
  const child = spawn(NODE[0], [NODE[1], path.join(APP, 'mcp-server.js')], { env: { ...env, HELPLINE_TOKEN: token } });
  const waiting = new Map();
  let buffer = '';
  let next = 0;
  child.stdout.on('data', (chunk) => {
    buffer += chunk;
    let at;
    while ((at = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, at);
      buffer = buffer.slice(at + 1);
      if (line.trim()) { const m = JSON.parse(line); if (waiting.has(m.id)) waiting.get(m.id)(m); }
    }
  });
  const rpc = (method, params) => new Promise((resolve) => {
    next += 1;
    waiting.set(next, resolve);
    child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id: next, method, params })}\n`);
  });
  return {
    rpc,
    async call(name, args) {
      const res = await rpc('tools/call', { name, arguments: args });
      const text = res.result.content[0].text;
      if (res.result.isError) throw new Error(text);
      return JSON.parse(text);
    },
    close: () => child.kill(),
  };
}

// Each check returns [holds, what was seen]. For B checks "holds" means the
// planted problem is present; for D checks it means the feature works.
const checks = [];
const check = (id, title, fn) => checks.push({ id, title, fn });

check('B01', "Customer opens another customer's ticket by changing the id", async () => {
  const { page } = await as('eli@customer.test');
  await page.goto(`${BASE}/portal-ticket.html?id=1`);
  await page.locator('#thread .bubble').first().waitFor();
  const title = await page.locator('#title').textContent();
  return [title.includes('Refund not received'), `Eli sees: "${title}"`];
});

check('B02', 'Internal note is emailed to the customer', async () => {
  const { page } = await as('alice@helpline.test');
  await page.goto(`${BASE}/ticket.html?id=1`);
  await page.getByLabel('Reply', { exact: true }).fill('SECRET-NOTE do not refund');
  await page.getByLabel(/Internal note/).check();
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await msg(page, 'Internal note added.');
  const mail = await waitMail((m) => m.to === 'dana@customer.test' && m.body.includes('SECRET-NOTE'));
  return [Boolean(mail), mail ? `mail to ${mail.to}: "${mail.subject}"` : 'no mail'];
});

check('B03', 'Teammate invited as Admin joins as an agent', async () => {
  const { page } = await as('mira@helpline.test');
  await page.getByRole('link', { name: 'Team' }).click();
  await page.getByLabel('Email').fill('newadmin@helpline.test');
  await page.getByLabel('Role').selectOption('Admin');
  await page.getByRole('button', { name: 'Send invitation' }).click();
  await msg(page, 'Invitation sent.');
  const mail = await waitMail((m) => m.to === 'newadmin@helpline.test');
  const link = mail.body.match(/http\S+accept\.html\?token=[a-f0-9]+/)[0];
  const guest = await visitor();
  await guest.page.goto(link);
  await guest.page.getByLabel('Your name').fill('Nia Admin');
  await guest.page.getByLabel('Choose a password').fill('newadminpass1');
  await guest.page.getByRole('button', { name: 'Join' }).click();
  await guest.page.waitForURL(/dashboard/);
  await guest.page.locator('#sidebar nav').waitFor();
  const hasTeam = await guest.page.getByRole('link', { name: 'Team' }).count();
  const role = one('SELECT role FROM users WHERE email = ?', 'newadmin@helpline.test').role;
  return [role === 'agent' && hasTeam === 0, `stored role: ${role}; Team in menu: ${hasTeam ? 'yes' : 'no'}`];
});

check('B04', "Deactivated agent's tickets stay assigned to them", async () => {
  const { page } = await as('mira@helpline.test');
  await page.getByRole('link', { name: 'Team' }).click();
  await page.getByRole('row', { name: /Bob Tanaka/ }).getByRole('button', { name: 'Deactivate' }).click();
  await msg(page, 'deactivated');
  const still = one("SELECT COUNT(*) AS n FROM tickets t JOIN users u ON u.id = t.assignee_id WHERE u.email = 'bob@helpline.test'").n;
  await page.getByRole('link', { name: 'Dashboard' }).click();
  await page.getByRole('link', { name: /Unassigned/ }).click();
  const summary = await page.locator('#summary', { hasText: 'match' }).textContent();
  return [still > 0 && summary.startsWith('5 '), `${still} tickets still assigned to Bob; Unassigned list: ${summary}`];
});

check('B05', 'Password reset link says it is invalid', async () => {
  const { page } = await visitor();
  await page.goto(BASE);
  await page.getByRole('link', { name: 'Forgot password?' }).click();
  await page.getByLabel('Email').fill('dana@customer.test');
  await page.getByRole('button', { name: 'Send reset link' }).click();
  const mail = await waitMail((m) => m.to === 'dana@customer.test' && /Reset/.test(m.subject));
  await page.goto(mail.body.match(/http\S+reset\.html\?token=[a-f0-9]+/)[0]);
  await page.getByLabel('New password').fill('brandnewpass1');
  await page.getByRole('button', { name: 'Save new password' }).click();
  await page.locator('#msg:not(:empty)').waitFor();
  const text = await page.locator('#msg').textContent();
  return [/invalid/.test(text), `page says: "${text}"`];
});

check('B06', 'A customer can download every ticket as CSV', async () => {
  const { context } = await as('eli@customer.test');
  const res = await context.request.get(`${BASE}/api/export.csv`);
  const text = await res.text();
  return [res.status() === 200 && text.includes('dana@customer.test'), `status ${res.status()}, ${text.split('\n').length - 2} rows`];
});

check('B07', 'An agent can open and save Settings by typing the address', async () => {
  const { page } = await as('alice@helpline.test');
  const inMenu = await page.getByRole('link', { name: 'Settings' }).count();
  await page.goto(`${BASE}/settings.html`);
  await page.getByLabel('Company name').fill('Changed By Agent');
  await page.getByRole('button', { name: 'Save settings' }).click();
  await msg(page, 'Settings saved.');
  const brand = await (await fetch(`${BASE}/api/brand`)).json();
  return [brand.company_name === 'Changed By Agent' && inMenu === 0, `company name is now "${brand.company_name}"`];
});

check('B08', 'Contact form drops the message', async () => {
  const { page } = await visitor();
  await page.goto(BASE);
  await page.getByRole('link', { name: 'Contact us without an account' }).click();
  await page.getByLabel('Your name').fill('Sam Field');
  await page.getByLabel('Email').fill('sam@example.com');
  await page.getByLabel('Subject').fill('Contact check');
  await page.getByLabel('How can we help?').fill('MESSAGE-BODY-123');
  await page.getByRole('button', { name: 'Send' }).click();
  await msg(page, 'Thanks!');
  const ticket = one("SELECT description FROM tickets WHERE subject = 'Contact check'");
  return [ticket.description === '', `stored description: "${ticket.description}"`];
});

check('B09', 'Replying to a closed ticket does not reopen it', async () => {
  const { page } = await as('eli@customer.test');
  await page.getByRole('link', { name: 'Login page shows an error' }).click();
  await page.getByLabel('Reply', { exact: true }).fill('It happened again today.');
  await page.getByRole('button', { name: 'Send reply' }).click();
  await msg(page, 'Reply sent.');
  const status = one('SELECT status FROM tickets WHERE id = 21').status;
  return [status === 'closed', `status after reply: ${status}`];
});

check('B10', 'Urgent priority is saved as normal', async () => {
  const { page } = await as('dana@customer.test');
  await page.getByRole('link', { name: 'New ticket', exact: true }).click();
  await page.getByLabel('Subject').fill('Site is down');
  await page.getByLabel('What is the problem?').fill('Nothing loads.');
  await page.getByLabel('How urgent is it?').selectOption({ label: 'Urgent' });
  await page.getByRole('button', { name: 'Send ticket' }).click();
  await page.waitForURL(/portal-ticket/);
  const priority = one("SELECT priority FROM tickets WHERE subject = 'Site is down'").priority;
  return [priority === 'normal', `stored priority: ${priority}`];
});

check('B11', 'Inbox shows more than 10 per page and later pages are empty', async () => {
  const { page } = await as('alice@helpline.test');
  await page.getByRole('link', { name: 'Inbox' }).click();
  await page.locator('#list tbody tr').first().waitFor();
  const rows = await page.locator('#list tbody tr').count();
  const label = await page.locator('#page').textContent();
  await page.getByRole('button', { name: 'Next' }).click();
  await page.locator('#page', { hasText: 'Page 2' }).waitFor();
  const empty = await page.locator('#empty').count();
  return [rows > 10 && empty === 1, `${rows} rows on "${label}"; page 2 empty: ${empty === 1}`];
});

check('B12', 'Search is case-sensitive', async () => {
  const { page } = await as('alice@helpline.test');
  await page.getByRole('link', { name: 'Inbox' }).click();
  await page.getByLabel('Status').selectOption({ label: 'Any status' });
  await page.getByLabel('Search').fill('export');
  await page.getByRole('button', { name: 'Apply' }).click();
  await page.locator('#summary', { hasText: 'match' }).waitFor();
  await sleep(300);
  const summary = await page.locator('#summary').textContent();
  return [summary.startsWith('1 '), `"export" -> ${summary} (two tickets contain the word)`];
});

check('B13', 'Bulk close closes the wrong tickets', async () => {
  const { page } = await as('alice@helpline.test');
  await page.getByRole('link', { name: 'Inbox' }).click();
  for (const id of [3, 6, 9]) await page.getByLabel(`Select ticket ${id}`, { exact: true }).check();
  await page.getByRole('button', { name: 'Close selected' }).click();
  await msg(page, '3 ticket(s) closed.');
  const status = Object.fromEntries(db('SELECT id, status FROM tickets WHERE id IN (1, 2, 3, 6, 9)').map((t) => [t.id, t.status]));
  const wrong = [3, 6, 9].every((id) => status[id] === 'open') && status[1] === 'closed' && status[2] === 'closed';
  return [wrong, `selected 3, 6, 9 -> ${JSON.stringify(status)}`];
});

check('B14', 'Send and close does not email the customer', async () => {
  const { page } = await as('alice@helpline.test');
  await page.goto(`${BASE}/ticket.html?id=4`);
  await page.getByLabel('Reply', { exact: true }).fill('SENDCLOSE-TEXT all fixed');
  await page.getByRole('button', { name: 'Send and close' }).click();
  await msg(page, 'ticket closed');
  const mail = await waitMail((m) => m.to === 'dana@customer.test', 2500);
  return [!mail, mail ? `mail: ${mail.subject}` : 'no mail to the customer after 2.5 s'];
});

check('B15', 'An old ticket set to Pending is closed within seconds', async () => {
  const { page } = await as('alice@helpline.test');
  await page.goto(`${BASE}/ticket.html?id=1`);
  await page.getByLabel('Status').selectOption('pending');
  await msg(page, 'Status saved.');
  const mail = await waitMail((m) => /closed automatically/.test(m.body), 4000);
  const status = one('SELECT status FROM tickets WHERE id = 1').status;
  return [status === 'closed' && Boolean(mail), `status a moment later: ${status}; auto-close mail: ${Boolean(mail)}`];
});

check('B16', 'Dashboard Unassigned count does not match its list', async () => {
  const { page } = await as('alice@helpline.test');
  await page.locator('#unassigned', { hasText: /\d/ }).waitFor();
  const card = await page.locator('#unassigned').textContent();
  await page.getByRole('link', { name: /Unassigned/ }).click();
  const summary = await page.locator('#summary', { hasText: 'match' }).textContent();
  return [card === '9' && summary.startsWith('5 '), `card says ${card}; list says ${summary}`];
});

check('B17', 'Reply emails still go out with the switch off', async () => {
  const mira = await as('mira@helpline.test');
  await mira.page.getByRole('link', { name: 'Settings' }).click();
  await mira.page.getByLabel(/Email customers/).uncheck();
  await mira.page.getByRole('button', { name: 'Save settings' }).click();
  await msg(mira.page, 'Settings saved.');
  const { page } = await as('alice@helpline.test');
  await page.goto(`${BASE}/ticket.html?id=2`);
  await page.getByLabel('Reply', { exact: true }).fill('NOTIFY-OFF-TEXT');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await msg(page, 'Reply sent');
  const mail = await waitMail((m) => m.body.includes('NOTIFY-OFF-TEXT'));
  return [Boolean(mail), mail ? `mail still sent to ${mail.to}` : 'no mail'];
});

check('B18', 'Resend invite does nothing', async () => {
  const { page } = await as('mira@helpline.test');
  await page.getByRole('link', { name: 'Team' }).click();
  await page.getByLabel('Email').fill('later@helpline.test');
  await page.getByRole('button', { name: 'Send invitation' }).click();
  await msg(page, 'Invitation sent.');
  await waitMail((m) => m.to === 'later@helpline.test');
  await page.getByRole('button', { name: 'Resend invite' }).click();
  await sleep(1500);
  const count = (await mails()).filter((m) => m.to === 'later@helpline.test').length;
  return [count === 1, `${count} invitation mail(s) after Resend`];
});

check('B19', 'Ticket created through MCP for a new address breaks the ticket page', async () => {
  const client = mcp();
  const made = await client.call('create_ticket', { customer_email: 'newperson@customer.test', subject: 'From MCP', description: 'Made by the assistant' });
  client.close();
  const row = one('SELECT customer_id FROM tickets WHERE id = ?', made.id);
  const { page } = await as('alice@helpline.test');
  await page.getByRole('link', { name: 'Inbox' }).click();
  await page.getByRole('link', { name: 'From MCP' }).click();
  await page.locator('#title:not(:text("Loading…"))').waitFor();
  const title = await page.locator('#title').textContent();
  return [row.customer_id === null && /Could not load/.test(title), `customer_id: ${row.customer_id}; page: "${title}"`];
});

check('B20', 'MCP internal note is posted as a public reply', async () => {
  const client = mcp();
  const out = await client.call('add_reply', { ticket_id: 2, body: 'MCP-INTERNAL-NOTE customer is difficult', internal: true });
  client.close();
  const { page } = await as('dana@customer.test');
  await page.getByRole('link', { name: 'Invoice shows the wrong company name' }).click();
  await page.locator('#thread .bubble').first().waitFor();
  const seen = await page.getByText('MCP-INTERNAL-NOTE').count();
  const mail = await waitMail((m) => m.body.includes('MCP-INTERNAL-NOTE'));
  return [seen > 0 && Boolean(mail), `tool said internal=${out.internal}; customer sees it: ${seen > 0}; emailed: ${Boolean(mail)}`];
});

check('B21', 'MCP list_tickets ignores the status filter', async () => {
  const client = mcp();
  const closed = await client.call('list_tickets', { status: 'closed' });
  client.close();
  return [closed.length === 32, `status=closed returned ${closed.length} tickets (12 are closed)`];
});

check('B22', 'MCP search_tickets is promised and missing', async () => {
  const client = mcp();
  const tools = (await client.rpc('tools/list', {})).result.tools.map((t) => t.name);
  client.close();
  return [!tools.includes('search_tickets'), `tools: ${tools.join(', ')}`];
});

check('B25', 'Help centre in the customer menu is a dead end', async () => {
  const { page } = await as('dana@customer.test');
  await page.getByRole('link', { name: 'Help centre' }).click();
  const text = await page.locator('body').textContent();
  return [text.trim() === 'Not found', `page shows: "${text.trim()}"`];
});

check('D01', 'Sign-up lands in the portal, logged in', async () => {
  const { page } = await visitor();
  await page.goto(`${BASE}/signup.html`);
  await page.getByLabel('Your name').fill('Fay New');
  await page.getByLabel('Email').fill('fay@customer.test');
  await page.getByLabel('Password').fill('faypassword1');
  await page.getByRole('button', { name: 'Create account' }).click();
  await page.waitForURL(/portal/);
  await page.locator('#empty').waitFor();
  return [true, 'portal with the empty-state message'];
});

check('D02', 'Customer portal never shows internal notes', async () => {
  const { page } = await as('dana@customer.test');
  await page.getByRole('link', { name: 'Refund not received' }).click();
  await page.locator('#thread .bubble').nth(1).waitFor();
  const leaked = await page.getByText('Legacy plan').count();
  return [leaked === 0, `internal note visible: ${leaked > 0}`];
});

check('D03', 'Agents cannot open Team', async () => {
  const { page, context } = await as('alice@helpline.test');
  await page.goto(`${BASE}/team.html`);
  await page.getByText('You do not have access to this page.').waitFor();
  const res = await context.request.get(`${BASE}/api/team`);
  return [res.status() === 403, `API status ${res.status()}`];
});

check('D04', 'Bulk "assign to me" changes exactly the ticked tickets', async () => {
  const { page } = await as('alice@helpline.test');
  await page.getByRole('link', { name: 'Inbox' }).click();
  for (const id of [3, 6]) await page.getByLabel(`Select ticket ${id}`, { exact: true }).check();
  await page.getByRole('button', { name: 'Assign selected to me' }).click();
  await msg(page, '2 ticket(s) assigned to you.');
  const mine = db("SELECT t.id FROM tickets t JOIN users u ON u.id = t.assignee_id WHERE u.email = 'alice@helpline.test' AND t.status = 'open'").map((t) => t.id);
  return [mine.length === 9 && mine.includes(3) && mine.includes(6), `Alice's open tickets: ${mine.join(', ')}`];
});

check('D05', 'Deactivated agent cannot log in', async () => {
  const mira = await as('mira@helpline.test');
  await mira.page.getByRole('link', { name: 'Team' }).click();
  await mira.page.getByRole('row', { name: /Bob Tanaka/ }).getByRole('button', { name: 'Deactivate' }).click();
  await msg(mira.page, 'deactivated');
  const { page } = await visitor();
  await page.goto(BASE);
  await page.getByLabel('Email').fill('bob@helpline.test');
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Log in' }).click();
  await msg(page, 'deactivated');
  return [true, 'login refused with a message'];
});

check('D06', 'Canned reply is added to what was typed', async () => {
  const { page } = await as('alice@helpline.test');
  await page.goto(`${BASE}/ticket.html?id=2`);
  await page.getByLabel('Reply', { exact: true }).fill('Hello Dana,');
  await page.getByLabel('Insert a canned reply').selectOption({ label: 'Refund sent' });
  const value = await page.getByLabel('Reply', { exact: true }).inputValue();
  return [value.startsWith('Hello Dana,') && value.includes('Your refund has been sent'), JSON.stringify(value.slice(0, 50))];
});

check('D07', 'Send emails the customer and shows in their portal', async () => {
  const { page } = await as('alice@helpline.test');
  await page.goto(`${BASE}/ticket.html?id=2`);
  await page.getByLabel('Reply', { exact: true }).fill('NORMAL-SEND-TEXT');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await msg(page, 'Reply sent');
  const mail = await waitMail((m) => m.to === 'dana@customer.test' && m.body.includes('NORMAL-SEND-TEXT'));
  return [Boolean(mail), mail ? mail.subject : 'no mail'];
});

check('D08', "Customer closes own ticket; cannot write to someone else's", async () => {
  const dana = await as('dana@customer.test');
  await dana.page.getByRole('link', { name: 'Refund not received' }).click();
  await dana.page.getByRole('button', { name: 'Close ticket' }).click();
  await msg(dana.page, 'Ticket closed.');
  const eli = await as('eli@customer.test');
  const post = await eli.context.request.post(`${BASE}/api/tickets/2/messages`, { data: { body: 'hi' } });
  const patch = await eli.context.request.patch(`${BASE}/api/tickets/2`, { data: { status: 'closed' } });
  const status = one('SELECT status FROM tickets WHERE id = 1').status;
  return [status === 'closed' && post.status() === 404 && patch.status() === 404, `own close: ${status}; other reply ${post.status()}, other close ${patch.status()}`];
});

check('D09', 'MCP set_status and assign_ticket work', async () => {
  const client = mcp();
  await client.call('set_status', { ticket_id: 3, status: 'closed' });
  await client.call('assign_ticket', { ticket_id: 6, agent_email: 'bob@helpline.test' });
  client.close();
  const t3 = one('SELECT status, closed_at FROM tickets WHERE id = 3');
  const t6 = one("SELECT u.email FROM tickets t JOIN users u ON u.id = t.assignee_id WHERE t.id = 6");
  return [t3.status === 'closed' && t3.closed_at && t6.email === 'bob@helpline.test', `#3 ${t3.status}, #6 -> ${t6.email}`];
});

check('D10', 'Invitation link works once', async () => {
  const { page } = await as('mira@helpline.test');
  await page.getByRole('link', { name: 'Team' }).click();
  await page.getByLabel('Email').fill('carl@helpline.test');
  await page.getByRole('button', { name: 'Send invitation' }).click();
  const mail = await waitMail((m) => m.to === 'carl@helpline.test');
  const link = mail.body.match(/http\S+accept\.html\?token=[a-f0-9]+/)[0];
  const first = await visitor();
  await first.page.goto(link);
  await first.page.getByLabel('Your name').fill('Carl Agent');
  await first.page.getByLabel('Choose a password').fill('carlpassword1');
  await first.page.getByRole('button', { name: 'Join' }).click();
  await first.page.waitForURL(/dashboard/);
  const second = await visitor();
  await second.page.goto(link);
  await second.page.getByText('invalid or was already used').waitFor();
  return [true, 'joined as agent; second use refused'];
});

check('D11', 'Admin export is a correct CSV', async () => {
  const { context } = await as('mira@helpline.test');
  const text = await (await context.request.get(`${BASE}/api/export.csv`)).text();
  const lines = text.trim().split('\n');
  return [lines.length === 33 && lines[0].startsWith('id,subject'), `${lines.length - 1} rows`];
});

// These two stop the worker, so they run last.
check('B23', 'Contact form accepts an invalid email address', async () => {
  const { page } = await visitor();
  await page.goto(`${BASE}/contact.html`);
  await page.getByLabel('Your name').fill('Typo Person');
  await page.getByLabel('Email').fill('typo at example');
  await page.getByLabel('Subject').fill('Bad address');
  await page.getByLabel('How can we help?').fill('Hello');
  await page.getByRole('button', { name: 'Send' }).click();
  await page.locator('#msg:not(:empty)').waitFor();
  const text = await page.locator('#msg').textContent();
  return [/Thanks!/.test(text), `page says: "${text}"`];
});

check('B24', 'One undeliverable email stops all email', async () => {
  await sleep(1200);
  const { page } = await visitor();
  await page.goto(`${BASE}/forgot.html`);
  await page.getByLabel('Email').fill('dana@customer.test');
  await page.getByRole('button', { name: 'Send reset link' }).click();
  const mail = await waitMail((m) => m.to === 'dana@customer.test' && /Reset/.test(m.subject), 3000);
  const stopped = /\[dev\] worker stopped/.test(appLog);
  const queued = one('SELECT COUNT(*) AS n FROM outbox WHERE sent_at IS NULL').n;
  return [!mail && stopped, `reset mail arrived: ${Boolean(mail)}; worker stopped: ${stopped}; mail stuck in queue: ${queued}`];
});

(async () => {
  reset();
  app = spawn(NODE[0], [NODE[1], path.join(APP, 'dev.js')], { env });
  app.stdout.on('data', (d) => { appLog += d; });
  app.stderr.on('data', (d) => { appLog += d; });
  for (let i = 0; i < 50; i += 1) {
    try { if ((await fetch(`${BASE}/health`)).ok) break; } catch { /* not up yet */ }
    await sleep(100);
  }
  browser = await chromium.launch({ channel: process.env.VERIFY_CHANNEL || 'chrome' });

  let bad = 0;
  for (const item of checks) {
    if (item.id !== 'B24') reset();
    let holds = false;
    let seen;
    try {
      [holds, seen] = await item.fn();
    } catch (err) {
      seen = `check crashed: ${err.message.split('\n')[0]}`;
    }
    for (const context of browser.contexts()) await context.close();
    const expected = item.id.startsWith('B') ? 'problem present' : 'works';
    if (!holds) bad += 1;
    console.log(`${holds ? 'ok  ' : 'FAIL'} ${item.id} ${item.title}\n       ${holds ? expected : `expected: ${expected}`} | ${seen}`);
  }

  await browser.close();
  app.kill('SIGTERM');
  await sleep(400);
  fs.rmSync(tmp, { recursive: true, force: true });
  const planted = checks.filter((c) => c.id.startsWith('B')).length;
  console.log(`\n${planted} planted problems, ${checks.length - planted} working features checked; ${bad} did not match the answer key.`);
  process.exit(bad ? 1 : 0);
})();
