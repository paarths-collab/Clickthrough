const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const db = require('./db');
const { hashPassword, verifyPassword, isValidEmail } = require('./lib');

const PORT = Number(process.env.PORT || 4173);
const PUBLIC = path.join(__dirname, 'public');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };

function json(res, status, body, headers = {}) {
  res.writeHead(status, { 'Content-Type': 'application/json', ...headers });
  res.end(JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => (raw += chunk));
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch (err) { reject(err); }
    });
  });
}

function currentUser(req) {
  const match = /(?:^|;\s*)sid=([a-f0-9]+)/.exec(req.headers.cookie || '');
  if (!match) return null;
  return db.prepare(
    'SELECT u.id, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.sid = ?'
  ).get(match[1]) || null;
}

function startSession(userId) {
  const sid = crypto.randomBytes(16).toString('hex');
  db.prepare('INSERT INTO sessions (sid, user_id) VALUES (?, ?)').run(sid, userId);
  return { 'Set-Cookie': `sid=${sid}; Path=/; HttpOnly; SameSite=Lax` };
}

async function api(req, res, url) {
  const route = `${req.method} ${url.pathname}`;
  const body = ['POST', 'PUT', 'PATCH'].includes(req.method) ? await readBody(req) : {};

  // ---- accounts -----------------------------------------------------------
  if (route === 'POST /api/signup') {
    if (!isValidEmail(body.email)) return json(res, 400, { error: 'Enter a valid email.' });
    if (!body.password || body.password.length < 8) {
      return json(res, 400, { error: 'Password must be at least 8 characters.' });
    }
    if (db.prepare('SELECT id FROM users WHERE email = ?').get(body.email)) {
      return json(res, 409, { error: 'That email is already registered.' });
    }
    const info = db.prepare('INSERT INTO users (email, name, password) VALUES (?, ?, ?)')
      .run(body.email, body.name || body.email.split('@')[0], hashPassword(body.password));
    return json(res, 201, { id: Number(info.lastInsertRowid) });
  }

  if (route === 'POST /api/login') {
    const user = db.prepare('SELECT * FROM users WHERE email = ?').get(body.email || '');
    if (!user || !verifyPassword(body.password || '', user.password)) {
      return json(res, 401, { error: 'Wrong email or password.' });
    }
    return json(res, 200, { id: user.id, name: user.name }, startSession(user.id));
  }

  const user = currentUser(req);
  if (!user) return json(res, 401, { error: 'Not logged in.' });

  if (route === 'POST /api/logout') {
    db.prepare('DELETE FROM sessions WHERE user_id = ?').run(user.id);
    return json(res, 200, { ok: true }, { 'Set-Cookie': 'sid=; Path=/; Max-Age=0' });
  }

  if (route === 'GET /api/me') return json(res, 200, user);

  if (route === 'PUT /api/settings') {
    if (!body.name || !body.name.trim()) return json(res, 400, { error: 'Name is required.' });
    db.prepare('UPDATE users SET name = ? WHERE id = ?').run(user.id, body.name.trim());
    return json(res, 200, { ok: true, name: body.name.trim() });
  }

  // ---- projects -----------------------------------------------------------
  if (route === 'GET /api/projects') {
    const rows = db.prepare(`
      SELECT p.id, p.name,
        (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.done = 0) AS open_tasks
      FROM projects p WHERE p.owner_id = ? ORDER BY p.id`).all(user.id);
    return json(res, 200, { projects: rows });
  }

  if (route === 'POST /api/projects') {
    const info = db.prepare('INSERT INTO projects (owner_id, name) VALUES (?, ?)')
      .run(user.id, body.name);
    return json(res, 201, { id: Number(info.lastInsertRowid), name: body.name });
  }

  const projectTasks = /^\/api\/projects\/(\d+)\/tasks$/.exec(url.pathname);
  if (projectTasks && req.method === 'GET') {
    const project = db.prepare('SELECT id, name FROM projects WHERE id = ?').get(projectTasks[1]);
    if (!project) return json(res, 404, { error: 'Project not found.' });
    const tasks = db.prepare('SELECT id, title, done FROM tasks WHERE project_id = ? ORDER BY id')
      .all(project.id);
    return json(res, 200, { project, tasks });
  }

  // ---- tasks --------------------------------------------------------------
  if (route === 'POST /api/tasks') {
    if (!body.title || !body.title.trim()) return json(res, 400, { error: 'Title is required.' });
    const info = db.prepare('INSERT INTO tasks (project_id, title) VALUES (?, ?)')
      .run(body.project_id ?? null, body.title.trim());
    return json(res, 201, { id: Number(info.lastInsertRowid), title: body.title.trim() });
  }

  if (route === 'GET /api/my-tasks') {
    const rows = db.prepare(`
      SELECT t.id, t.title, t.done, p.name AS project
      FROM tasks t JOIN projects p ON p.id = t.project_id
      WHERE p.owner_id = ? ORDER BY t.done, t.id`).all(user.id);
    if (rows.length === 0) { res.writeHead(204); return res.end(); }
    return json(res, 200, { tasks: rows });
  }

  const taskById = /^\/api\/tasks\/(\d+)$/.exec(url.pathname);
  if (taskById) {
    const task = db.prepare(`
      SELECT t.id FROM tasks t JOIN projects p ON p.id = t.project_id
      WHERE t.id = ? AND p.owner_id = ?`).get(taskById[1], user.id);
    if (!task) return json(res, 404, { error: 'Task not found.' });
    if (req.method === 'PATCH') {
      db.prepare('UPDATE tasks SET done = ? WHERE id = ?').run(body.done ? 1 : 0, task.id);
      return json(res, 200, { ok: true });
    }
    if (req.method === 'DELETE') {
      db.prepare('DELETE FROM tasks WHERE id = ?').run(task.id);
      return json(res, 200, { ok: true });
    }
  }

  // ---- team ---------------------------------------------------------------
  if (route === 'GET /api/team') {
    const invites = db.prepare('SELECT email FROM invites WHERE inviter_id = ? ORDER BY id')
      .all(user.id);
    return json(res, 200, { invites });
  }

  if (route === 'POST /api/team/invite') {
    if (!isValidEmail(body.email)) return json(res, 400, { error: 'Enter a valid email.' });
    db.prepare('INSERT INTO invites (inviter_id, email) VALUES (?, ?)').run(user.id, body.email);
    return json(res, 201, { ok: true });
  }

  return json(res, 404, { error: 'Not found.' });
}

function serveStatic(res, url) {
  const name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
  const file = path.join(PUBLIC, path.normalize(name));
  if (!file.startsWith(PUBLIC) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    return res.end('Not found');
  }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}

http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  try {
    if (url.pathname === '/health') return json(res, 200, { ok: true });
    if (url.pathname.startsWith('/api/')) return await api(req, res, url);
    return serveStatic(res, url);
  } catch (err) {
    console.error(`[error] ${req.method} ${url.pathname}: ${err.message}`);
    return json(res, 500, { error: 'Internal error' });
  }
}).listen(PORT, () => console.log(`Tasklet running at http://localhost:${PORT}`));
