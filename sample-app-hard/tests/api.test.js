// API tests: start the web app on a spare port with its own database.
const test = require('node:test');
const assert = require('node:assert');
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const root = path.join(__dirname, '..');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'helpline-test-'));
const PORT = String(4300 + Math.floor(Math.random() * 500));
const env = { ...process.env, PORT, HELPLINE_DB: path.join(dir, 'test.db') };
const base = `http://localhost:${PORT}`;
const node = [process.execPath, '--disable-warning=ExperimentalWarning'];
let server;

async function call(method, url, body, cookie) {
  const res = await fetch(base + url, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(cookie ? { Cookie: cookie } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* no body */ }
  return { status: res.status, data, cookie: (res.headers.get('set-cookie') || '').split(';')[0] };
}

async function login(email) {
  const res = await call('POST', '/api/login', { email, password: 'helpline123' });
  assert.strictEqual(res.status, 200);
  return res.cookie;
}

test.before(async () => {
  spawnSync(node[0], [node[1], path.join(root, 'seed.js')], { env });
  server = spawn(node[0], [node[1], path.join(root, 'server.js')], { env, stdio: 'ignore' });
  for (let i = 0; i < 50; i += 1) {
    try { if ((await fetch(`${base}/health`)).ok) return; } catch { /* not up yet */ }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('server did not start');
});

test.after(() => {
  server.kill();
  fs.rmSync(dir, { recursive: true, force: true });
});

test('health', async () => {
  assert.strictEqual((await call('GET', '/health')).status, 200);
});

test('login rejects a wrong password', async () => {
  const res = await call('POST', '/api/login', { email: 'alice@helpline.test', password: 'nope' });
  assert.strictEqual(res.status, 401);
});

test('customer opens a ticket and sees it', async () => {
  const dana = await login('dana@customer.test');
  const created = await call('POST', '/api/tickets', { subject: 'Test', description: 'Body', priority: 'high' }, dana);
  assert.strictEqual(created.status, 201);
  const list = await call('GET', '/api/tickets', null, dana);
  assert.ok(list.data.tickets.some((t) => t.id === created.data.id && t.priority === 'high'));
});

test('contact form creates a ticket', async () => {
  const res = await call('POST', '/api/contact', {
    name: 'Sam', email: 'sam@example.com', subject: 'Hello', description: 'A question',
  });
  assert.strictEqual(res.status, 201);
});

test('agent replies and closes', async () => {
  const alice = await login('alice@helpline.test');
  const reply = await call('POST', '/api/tickets/2/messages', { body: 'On it.' }, alice);
  assert.strictEqual(reply.status, 201);
  const closed = await call('PATCH', '/api/tickets/2', { status: 'closed' }, alice);
  assert.strictEqual(closed.status, 200);
  const ticket = await call('GET', '/api/tickets/2', null, alice);
  assert.strictEqual(ticket.data.status, 'closed');
  assert.ok(ticket.data.messages.some((m) => m.body === 'On it.'));
});

test('customers do not see internal notes', async () => {
  const dana = await login('dana@customer.test');
  const ticket = await call('GET', '/api/tickets/1', null, dana);
  assert.ok(ticket.data.messages.every((m) => !m.internal));
});

test('stats and inbox filters answer', async () => {
  const alice = await login('alice@helpline.test');
  const stats = await call('GET', '/api/stats', null, alice);
  assert.ok(stats.data.open > 0);
  const inbox = await call('GET', '/api/tickets?status=pending', null, alice);
  assert.ok(inbox.data.tickets.every((t) => t.status === 'pending'));
});

test('only admins manage the team', async () => {
  const alice = await login('alice@helpline.test');
  assert.strictEqual((await call('GET', '/api/team', null, alice)).status, 403);
  const mira = await login('mira@helpline.test');
  assert.strictEqual((await call('GET', '/api/team', null, mira)).status, 200);
});

test('admin saves settings', async () => {
  const mira = await login('mira@helpline.test');
  const res = await call('PUT', '/api/settings', { company_name: 'Helpline', auto_close_days: 7, notify_customer_on_reply: true }, mira);
  assert.strictEqual(res.status, 200);
});
