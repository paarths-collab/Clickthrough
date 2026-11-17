const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { db, now, getSetting, setSetting, queueMail, baseUrl } = require('./db');
const { hashPassword, verifyPassword, isEmail, newToken, csvRow, STATUSES, PRIORITIES } = require('./lib');

const PORT = Number(process.env.PORT || 4280);
const PUBLIC = path.join(__dirname, 'public');
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
};
const DAY = 24 * 60 * 60 * 1000;

function json(res, status, data) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', (chunk) => { raw += chunk; });
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch { resolve({}); }
    });
  });
}

function cookies(req) {
  const out = {};
  for (const part of (req.headers.cookie || '').split(';')) {
    const [key, ...rest] = part.trim().split('=');
    if (key) out[key] = rest.join('=');
  }
  return out;
}

function currentUser(req) {
  const sid = cookies(req).sid;
  if (!sid) return null;
  return db.prepare(
    'SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ? AND u.active = 1'
  ).get(sid) || null;
}

function startSession(res, userId) {
  const token = newToken();
  db.prepare('INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)').run(token, userId, now());
  res.setHeader('Set-Cookie', `sid=${token}; HttpOnly; Path=/; SameSite=Lax`);
}

const publicUser = (u) => ({ id: u.id, email: u.email, name: u.name, role: u.role });
const isStaff = (u) => u.role === 'agent' || u.role === 'admin';
const clean = (value) => (typeof value === 'string' ? value.trim() : '');

const TICKET_SELECT = `
  SELECT t.id, t.subject, t.description, t.priority, t.status, t.assignee_id, t.customer_id,
         t.created_at, t.updated_at, t.closed_at,
         c.name AS customer_name, c.email AS customer_email, a.name AS assignee_name
  FROM tickets t
  LEFT JOIN users c ON c.id = t.customer_id
  LEFT JOIN users a ON a.id = t.assignee_id`;

function notifyCustomer(ticket, text) {
  const customer = db.prepare('SELECT email FROM users WHERE id = ?').get(ticket.customer_id);
  if (!customer) return;
  queueMail(
    customer.email,
    `New reply on "${ticket.subject}"`,
    `${text}\n\nOpen your ticket: ${baseUrl()}/portal-ticket.html?id=${ticket.id}`
  );
}

function setStatus(ticket, status, actor) {
  const t = now();
  db.prepare('UPDATE tickets SET status = ?, closed_at = ?, updated_at = ? WHERE id = ?')
    .run(status, status === 'closed' ? t : null, t, ticket.id);
  if (status === 'closed' && ticket.status !== 'closed' && isStaff(actor)) {
    const customer = db.prepare('SELECT email FROM users WHERE id = ?').get(ticket.customer_id);
    if (customer) {
      queueMail(
        customer.email,
        `Your ticket was closed: "${ticket.subject}"`,
        `We have closed this ticket. Reply to it if you still need help.\n\nOpen your ticket: ${baseUrl()}/portal-ticket.html?id=${ticket.id}`
      );
    }
  }
}

function mailPage() {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const rows = db.prepare('SELECT * FROM outbox WHERE sent_at IS NOT NULL ORDER BY id DESC').all();
  const items = rows.map((m) => {
    const body = esc(m.body).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1">$1</a>');
    return `<article class="mail"><p><strong>To:</strong> <span class="to">${esc(m.to_email)}</span><br>
<strong>Subject:</strong> <span class="subject">${esc(m.subject)}</span><br>
<small>${new Date(m.sent_at).toISOString()}</small></p><pre>${body}</pre></article>`;
  }).join('\n');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Sent mail - Helpline (development)</title>
<link rel="stylesheet" href="/style.css"></head><body class="plain"><main>
<h1>Sent mail</h1><p class="muted">Development only. Nothing is really emailed; mail the worker has sent is listed here, newest first.</p>
${items || '<p id="empty">No mail has been sent yet.</p>'}</main></body></html>`;
}

function serveStatic(res, pathname) {
  const name = pathname === '/' ? '/index.html' : pathname;
  const file = path.normalize(path.join(PUBLIC, name));
  if (!file.startsWith(PUBLIC) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('Not found');
  }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  res.end(fs.readFileSync(file));
}

async function handle(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const p = url.pathname;
  const method = req.method;
  const query = Object.fromEntries(url.searchParams);
  let m;

  if (p === '/health') return json(res, 200, { ok: true });
  if (method === 'GET' && p === '/dev/mail') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(mailPage());
  }
  if (!p.startsWith('/api/')) return serveStatic(res, p);

  const body = method === 'GET' ? {} : await readBody(req);

  // ---- no login needed ----------------------------------------------------
  if (method === 'GET' && p === '/api/brand') {
    return json(res, 200, { company_name: getSetting('company_name') });
  }

  if (method === 'POST' && p === '/api/signup') {
    const email = clean(body.email).toLowerCase();
    const name = clean(body.name);
    if (!name) return json(res, 400, { error: 'Name is required.' });
    if (!isEmail(email)) return json(res, 400, { error: 'Enter a valid email address.' });
    if (clean(body.password).length < 8) return json(res, 400, { error: 'Password must be at least 8 characters.' });
    const existing = db.prepare('SELECT id, password_hash FROM users WHERE email = ?').get(email);
    if (existing && existing.password_hash) return json(res, 409, { error: 'That email is already registered.' });
    let id;
    if (existing) {
      db.prepare('UPDATE users SET name = ?, password_hash = ? WHERE id = ?').run(name, hashPassword(body.password), existing.id);
      id = existing.id;
    } else {
      id = Number(db.prepare("INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, 'customer')")
        .run(email, name, hashPassword(body.password)).lastInsertRowid);
    }
    startSession(res, id);
    return json(res, 201, { id, email, name, role: 'customer' });
  }

  if (method === 'POST' && p === '/api/login') {
    const user = db.prepare('SELECT * FROM users WHERE email = ?').get(clean(body.email).toLowerCase());
    if (!user || !verifyPassword(body.password || '', user.password_hash)) {
      return json(res, 401, { error: 'Wrong email or password.' });
    }
    if (!user.active) return json(res, 403, { error: 'This account has been deactivated.' });
    startSession(res, user.id);
    return json(res, 200, publicUser(user));
  }

  if (method === 'POST' && p === '/api/logout') {
    const sid = cookies(req).sid;
    if (sid) db.prepare('DELETE FROM sessions WHERE token = ?').run(sid);
    res.setHeader('Set-Cookie', 'sid=; HttpOnly; Path=/; Max-Age=0');
    return json(res, 200, { ok: true });
  }

  if (method === 'POST' && p === '/api/forgot') {
    const user = db.prepare('SELECT * FROM users WHERE email = ? AND active = 1').get(clean(body.email).toLowerCase());
    if (user) {
      const token = newToken();
      db.prepare('INSERT INTO resets (token, user_id, created_at) VALUES (?, ?, ?)').run(token, user.id, now());
      queueMail(user.email, 'Reset your Helpline password',
        `Someone asked to reset the password for this account.\n\nChoose a new password: ${baseUrl()}/reset.html?token=${token}\n\nThe link works once and expires after one hour.`);
    }
    return json(res, 200, { ok: true });
  }

  if (method === 'POST' && p === '/api/reset') {
    const reset = db.prepare('SELECT * FROM resets WHERE token = ?').get(clean(body.token));
    if (!reset || reset.used_at || now() - reset.created_at > 60 * 60 * 1000) {
      return json(res, 400, { error: 'This link is invalid or has expired.' });
    }
    if (clean(body.password).length < 8) return json(res, 400, { error: 'Password must be at least 8 characters.' });
    db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(hashPassword(body.password), reset.user_id);
    db.prepare('UPDATE resets SET used_at = ? WHERE token = ?').run(now(), reset.token);
    db.prepare('DELETE FROM sessions WHERE user_id = ?').run(reset.user_id);
    return json(res, 200, { ok: true });
  }

  if (method === 'POST' && p === '/api/contact') {
    const email = clean(body.email).toLowerCase();
    const subject = clean(body.subject);
    if (!email) return json(res, 400, { error: 'Email is required.' });
    if (!subject) return json(res, 400, { error: 'Subject is required.' });
    let customer = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
    if (!customer) {
      const id = Number(db.prepare("INSERT INTO users (email, name, role) VALUES (?, ?, 'customer')")
        .run(email, clean(body.name) || email).lastInsertRowid);
      customer = { id, email };
    }
    const t = now();
    const id = Number(db.prepare(
      'INSERT INTO tickets (customer_id, subject, description, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
    ).run(customer.id, subject, clean(body.description), 'normal', 'open', t, t).lastInsertRowid);
    queueMail(email, `We received your request: "${subject}"`,
      `Thanks for getting in touch. Your reference is #${id}.\n\nCreate an account with this email address to follow your ticket: ${baseUrl()}/signup.html`);
    return json(res, 201, { id });
  }

  if (method === 'GET' && (m = p.match(/^\/api\/invites\/([a-f0-9]+)$/))) {
    const invite = db.prepare('SELECT email, role, accepted_at FROM invites WHERE token = ?').get(m[1]);
    if (!invite || invite.accepted_at) return json(res, 404, { error: 'This invitation is invalid or was already used.' });
    return json(res, 200, { email: invite.email, role: invite.role });
  }

  if (method === 'POST' && p === '/api/invites/accept') {
    const invite = db.prepare('SELECT * FROM invites WHERE token = ?').get(clean(body.token));
    if (!invite || invite.accepted_at) return json(res, 400, { error: 'This invitation is invalid or was already used.' });
    if (!clean(body.name)) return json(res, 400, { error: 'Name is required.' });
    if (clean(body.password).length < 8) return json(res, 400, { error: 'Password must be at least 8 characters.' });
    if (db.prepare('SELECT id FROM users WHERE email = ?').get(invite.email)) {
      return json(res, 409, { error: 'That email already has an account.' });
    }
    const id = Number(db.prepare('INSERT INTO users (email, name, password_hash, role, api_token) VALUES (?, ?, ?, ?, ?)')
      .run(invite.email, clean(body.name), hashPassword(body.password), invite.role, newToken()).lastInsertRowid);
    db.prepare('UPDATE invites SET accepted_at = ? WHERE token = ?').run(now(), invite.token);
    startSession(res, id);
    return json(res, 201, { id, email: invite.email, name: clean(body.name), role: invite.role });
  }

  // ---- logged in ----------------------------------------------------------
  const user = currentUser(req);
  if (!user) return json(res, 401, { error: 'Please log in.' });

  if (method === 'GET' && p === '/api/me') return json(res, 200, publicUser(user));

  if (method === 'GET' && p === '/api/tickets') {
    if (user.role === 'customer') {
      const tickets = db.prepare(`${TICKET_SELECT} WHERE t.customer_id = ? ORDER BY t.updated_at DESC`).all(user.id);
      return json(res, 200, { tickets, total: tickets.length });
    }
    const where = [];
    const args = [];
    if (query.status) { where.push('t.status = ?'); args.push(query.status); }
    if (query.assignee === 'me') { where.push('t.assignee_id = ?'); args.push(user.id); }
    else if (query.assignee === 'none') where.push('t.assignee_id IS NULL');
    else if (query.assignee) { where.push('t.assignee_id = ?'); args.push(Number(query.assignee)); }
    if (query.q) {
      where.push('(instr(t.subject, ?) > 0 OR instr(t.description, ?) > 0)');
      args.push(query.q, query.q);
    }
    const filter = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const limit = Math.min(Number(query.limit) || 25, 100);
    const page = Math.max(Number(query.page) || 1, 1);
    const order = query.sort === 'oldest' ? 'ASC' : 'DESC';
    const total = db.prepare(`SELECT COUNT(*) AS n FROM tickets t ${filter}`).get(...args).n;
    const tickets = db.prepare(`${TICKET_SELECT} ${filter} ORDER BY t.updated_at ${order}, t.id ${order} LIMIT ? OFFSET ?`)
      .all(...args, limit, (page - 1) * limit);
    return json(res, 200, { tickets, total });
  }

  if (method === 'POST' && p === '/api/tickets') {
    if (user.role !== 'customer') return json(res, 403, { error: 'Only customers open tickets here.' });
    const subject = clean(body.subject);
    const description = clean(body.description);
    if (!subject) return json(res, 400, { error: 'Subject is required.' });
    if (!description) return json(res, 400, { error: 'Please describe the problem.' });
    const priority = ['low', 'normal', 'high'].includes(body.priority) ? body.priority : 'normal';
    const t = now();
    const id = Number(db.prepare(
      'INSERT INTO tickets (customer_id, subject, description, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
    ).run(user.id, subject, description, priority, 'open', t, t).lastInsertRowid);
    return json(res, 201, { id });
  }

  if (method === 'GET' && (m = p.match(/^\/api\/tickets\/(\d+)$/))) {
    const ticket = db.prepare('SELECT * FROM tickets WHERE id = ?').get(Number(m[1]));
    if (!ticket) return json(res, 404, { error: 'Ticket not found.' });
    const customer = db.prepare('SELECT name, email FROM users WHERE id = ?').get(ticket.customer_id);
    const assignee = ticket.assignee_id
      ? db.prepare('SELECT id, name FROM users WHERE id = ?').get(ticket.assignee_id)
      : null;
    let messages = db.prepare(`
      SELECT m.id, m.body, m.internal, m.created_at, u.name AS author_name, u.role AS author_role
      FROM messages m JOIN users u ON u.id = m.author_id
      WHERE m.ticket_id = ? ORDER BY m.id`).all(ticket.id);
    if (user.role === 'customer') messages = messages.filter((msg) => !msg.internal);
    return json(res, 200, {
      ...ticket,
      customer: { name: customer.name, email: customer.email },
      assignee: assignee || null,
      messages,
    });
  }

  if (method === 'POST' && (m = p.match(/^\/api\/tickets\/(\d+)\/messages$/))) {
    const ticket = db.prepare('SELECT * FROM tickets WHERE id = ?').get(Number(m[1]));
    if (!ticket) return json(res, 404, { error: 'Ticket not found.' });
    if (user.role === 'customer' && ticket.customer_id !== user.id) return json(res, 404, { error: 'Ticket not found.' });
    const text = clean(body.body);
    if (!text) return json(res, 400, { error: 'Write a message first.' });
    const internal = isStaff(user) && body.internal ? 1 : 0;
    const t = now();
    const id = Number(db.prepare('INSERT INTO messages (ticket_id, author_id, body, internal, created_at) VALUES (?, ?, ?, ?, ?)')
      .run(ticket.id, user.id, text, internal, t).lastInsertRowid);
    db.prepare('UPDATE tickets SET updated_at = ? WHERE id = ?').run(t, ticket.id);
    if (user.role === 'customer') {
      const assignee = ticket.assignee_id
        ? db.prepare('SELECT email FROM users WHERE id = ? AND active = 1').get(ticket.assignee_id)
        : null;
      if (assignee) {
        queueMail(assignee.email, `Customer replied on "${ticket.subject}"`,
          `${text}\n\nOpen the ticket: ${baseUrl()}/ticket.html?id=${ticket.id}`);
      }
    } else {
      notifyCustomer(ticket, text);
    }
    return json(res, 201, { id });
  }

  if (method === 'PATCH' && (m = p.match(/^\/api\/tickets\/(\d+)$/))) {
    const ticket = db.prepare('SELECT * FROM tickets WHERE id = ?').get(Number(m[1]));
    if (!ticket) return json(res, 404, { error: 'Ticket not found.' });
    if (user.role === 'customer') {
      if (ticket.customer_id !== user.id) return json(res, 404, { error: 'Ticket not found.' });
      if (!['open', 'closed'].includes(body.status)) return json(res, 400, { error: 'You can only close or reopen a ticket.' });
      setStatus(ticket, body.status, user);
      return json(res, 200, { ok: true });
    }
    if (body.status !== undefined) {
      if (!STATUSES.includes(body.status)) return json(res, 400, { error: 'Unknown status.' });
      setStatus(ticket, body.status, user);
    }
    if (body.priority !== undefined) {
      if (!PRIORITIES.includes(body.priority)) return json(res, 400, { error: 'Unknown priority.' });
      db.prepare('UPDATE tickets SET priority = ?, updated_at = ? WHERE id = ?').run(body.priority, now(), ticket.id);
    }
    if (body.assignee_id !== undefined) {
      const assigneeId = body.assignee_id === null || body.assignee_id === '' ? null : Number(body.assignee_id);
      let agent = null;
      if (assigneeId !== null) {
        agent = db.prepare("SELECT id, email FROM users WHERE id = ? AND active = 1 AND role IN ('agent', 'admin')").get(assigneeId);
        if (!agent) return json(res, 400, { error: 'That person cannot be assigned tickets.' });
      }
      db.prepare('UPDATE tickets SET assignee_id = ?, updated_at = ? WHERE id = ?').run(assigneeId, now(), ticket.id);
      if (agent && agent.id !== user.id && agent.id !== ticket.assignee_id) {
        queueMail(agent.email, `Ticket assigned to you: "${ticket.subject}"`,
          `${user.name} assigned this ticket to you.\n\nOpen the ticket: ${baseUrl()}/ticket.html?id=${ticket.id}`);
      }
    }
    return json(res, 200, { ok: true });
  }

  if (method === 'GET' && p === '/api/export.csv') {
    const rows = db.prepare(`${TICKET_SELECT} ORDER BY t.id`).all();
    const lines = [csvRow(['id', 'subject', 'customer', 'customer_email', 'status', 'priority', 'assignee', 'created', 'updated'])];
    for (const t of rows) {
      lines.push(csvRow([t.id, t.subject, t.customer_name, t.customer_email, t.status, t.priority, t.assignee_name,
        new Date(t.created_at).toISOString(), new Date(t.updated_at).toISOString()]));
    }
    res.writeHead(200, {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': 'attachment; filename="tickets.csv"',
    });
    return res.end(lines.join('\n') + '\n');
  }

  // ---- staff --------------------------------------------------------------
  if (!isStaff(user)) return json(res, 403, { error: 'Staff only.' });

  if (method === 'GET' && p === '/api/stats') {
    const count = (sql, ...args) => db.prepare(`SELECT COUNT(*) AS n FROM tickets WHERE ${sql}`).get(...args).n;
    return json(res, 200, {
      open: count("status = 'open'"),
      unassigned: count('assignee_id IS NULL'),
      mine: count("status = 'open' AND assignee_id = ?", user.id),
      closed_this_week: count("status = 'closed' AND closed_at > ?", now() - 7 * DAY),
    });
  }

  if (method === 'GET' && p === '/api/agents') {
    return json(res, 200, db.prepare("SELECT id, name FROM users WHERE active = 1 AND role IN ('agent', 'admin') ORDER BY name").all());
  }

  if (method === 'POST' && (m = p.match(/^\/api\/tickets\/(\d+)\/reply-and-close$/))) {
    const ticket = db.prepare('SELECT * FROM tickets WHERE id = ?').get(Number(m[1]));
    if (!ticket) return json(res, 404, { error: 'Ticket not found.' });
    const text = clean(body.body);
    if (!text) return json(res, 400, { error: 'Write a message first.' });
    const t = now();
    db.prepare('INSERT INTO messages (ticket_id, author_id, body, internal, created_at) VALUES (?, ?, ?, 0, ?)')
      .run(ticket.id, user.id, text, t);
    db.prepare("UPDATE tickets SET status = 'closed', closed_at = ?, updated_at = ? WHERE id = ?").run(t, t, ticket.id);
    return json(res, 200, { ok: true });
  }

  if (method === 'POST' && p === '/api/tickets/bulk') {
    const ids = Array.isArray(body.ids) ? body.ids : [];
    if (!ids.length) return json(res, 400, { error: 'Select at least one ticket.' });
    const t = now();
    if (body.action === 'close') {
      const close = db.prepare("UPDATE tickets SET status = 'closed', closed_at = ?, updated_at = ? WHERE id = ?");
      for (const id in ids) close.run(t, t, Number(id));
      return json(res, 200, { updated: ids.length });
    }
    if (body.action === 'assign_me') {
      const assign = db.prepare('UPDATE tickets SET assignee_id = ?, updated_at = ? WHERE id = ?');
      for (const id of ids) assign.run(user.id, t, Number(id));
      return json(res, 200, { updated: ids.length });
    }
    return json(res, 400, { error: 'Unknown action.' });
  }

  if (method === 'GET' && p === '/api/canned') {
    return json(res, 200, db.prepare('SELECT * FROM canned ORDER BY title').all());
  }

  if (method === 'GET' && p === '/api/token') return json(res, 200, { token: user.api_token });

  if (method === 'GET' && p === '/api/settings') {
    return json(res, 200, {
      company_name: getSetting('company_name'),
      auto_close_days: Number(getSetting('auto_close_days')),
      notify_customer_on_reply: getSetting('notify_customer_on_reply') === '1',
    });
  }

  if (method === 'PUT' && p === '/api/settings') {
    const name = clean(body.company_name);
    const days = Number(body.auto_close_days);
    if (!name) return json(res, 400, { error: 'Company name is required.' });
    if (!Number.isInteger(days) || days < 1 || days > 365) {
      return json(res, 400, { error: 'Auto-close must be a whole number of days between 1 and 365.' });
    }
    setSetting('company_name', name);
    setSetting('auto_close_days', days);
    setSetting('notify_customer_on_reply', body.notify_customer_on_reply ? '1' : '0');
    return json(res, 200, { ok: true });
  }

  // ---- admin --------------------------------------------------------------
  if (user.role !== 'admin') return json(res, 403, { error: 'Admins only.' });

  if (method === 'GET' && p === '/api/team') {
    return json(res, 200, {
      members: db.prepare("SELECT id, name, email, role, active FROM users WHERE role IN ('agent', 'admin') ORDER BY name").all(),
      invites: db.prepare('SELECT email, role, created_at FROM invites WHERE accepted_at IS NULL ORDER BY created_at DESC').all(),
    });
  }

  if (method === 'POST' && p === '/api/invites') {
    const email = clean(body.email).toLowerCase();
    if (!isEmail(email)) return json(res, 400, { error: 'Enter a valid email address.' });
    if (db.prepare('SELECT id FROM users WHERE email = ?').get(email)) {
      return json(res, 409, { error: 'That email already has an account.' });
    }
    const role = body.role === 'admin' ? 'admin' : 'agent';
    const token = newToken();
    db.prepare('INSERT INTO invites (token, email, role, invited_by, created_at) VALUES (?, ?, ?, ?, ?)')
      .run(token, email, role, user.id, now());
    queueMail(email, `${user.name} invited you to ${getSetting('company_name')}`,
      `You have been invited to join the support team.\n\nAccept the invitation: ${baseUrl()}/accept.html?token=${token}`);
    return json(res, 201, { ok: true });
  }

  if (method === 'POST' && (m = p.match(/^\/api\/team\/(\d+)\/deactivate$/))) {
    const target = db.prepare("SELECT * FROM users WHERE id = ? AND role IN ('agent', 'admin')").get(Number(m[1]));
    if (!target) return json(res, 404, { error: 'Team member not found.' });
    if (target.id === user.id) return json(res, 400, { error: 'You cannot deactivate yourself.' });
    db.prepare('UPDATE users SET active = 0 WHERE id = ?').run(target.id);
    db.prepare('DELETE FROM sessions WHERE user_id = ?').run(target.id);
    return json(res, 200, { ok: true });
  }

  if (method === 'POST' && p === '/api/canned') {
    if (!clean(body.title) || !clean(body.body)) return json(res, 400, { error: 'Title and text are both required.' });
    const id = Number(db.prepare('INSERT INTO canned (title, body) VALUES (?, ?)').run(clean(body.title), clean(body.body)).lastInsertRowid);
    return json(res, 201, { id });
  }

  if ((m = p.match(/^\/api\/canned\/(\d+)$/))) {
    const id = Number(m[1]);
    if (!db.prepare('SELECT id FROM canned WHERE id = ?').get(id)) return json(res, 404, { error: 'Canned reply not found.' });
    if (method === 'PUT') {
      if (!clean(body.title) || !clean(body.body)) return json(res, 400, { error: 'Title and text are both required.' });
      db.prepare('UPDATE canned SET title = ?, body = ? WHERE id = ?').run(clean(body.title), clean(body.body), id);
      return json(res, 200, { ok: true });
    }
    if (method === 'DELETE') {
      db.prepare('DELETE FROM canned WHERE id = ?').run(id);
      return json(res, 200, { ok: true });
    }
  }

  return json(res, 404, { error: 'Not found.' });
}

http.createServer((req, res) => {
  handle(req, res).catch((err) => {
    console.error(`[error] ${req.method} ${req.url}: ${err.stack || err.message}`);
    if (!res.headersSent) json(res, 500, { error: 'Internal error' });
  });
}).listen(PORT, () => console.log(`Helpline web running at http://localhost:${PORT}`));
