const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const file = process.env.HELPLINE_DB || path.join(__dirname, 'helpline.db');
const db = new DatabaseSync(file);
db.exec('PRAGMA journal_mode = WAL');
db.exec('PRAGMA busy_timeout = 4000');

db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  password_hash TEXT,
  role TEXT NOT NULL CHECK (role IN ('customer', 'agent', 'admin')),
  active INTEGER NOT NULL DEFAULT 1,
  api_token TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  customer_id INTEGER,
  subject TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  priority TEXT NOT NULL DEFAULT 'normal',
  status TEXT NOT NULL DEFAULT 'open',
  assignee_id INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  closed_at INTEGER
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  author_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  internal INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
  token TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  role TEXT NOT NULL,
  invited_by INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  accepted_at INTEGER
);
CREATE TABLE IF NOT EXISTS resets (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE TABLE IF NOT EXISTS canned (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  to_email TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  sent_at INTEGER
);
`);

const DEFAULT_SETTINGS = {
  company_name: 'Helpline',
  auto_close_days: '7',
  notify_customer_on_reply: '1',
};

function now() {
  return Date.now();
}

function getSetting(key) {
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(key);
  return row ? row.value : DEFAULT_SETTINGS[key];
}

function setSetting(key, value) {
  db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value')
    .run(key, String(value));
}

function queueMail(to, subject, body) {
  db.prepare('INSERT INTO outbox (to_email, subject, body, created_at) VALUES (?, ?, ?, ?)')
    .run(to, subject, body, now());
}

function baseUrl() {
  return process.env.BASE_URL || `http://localhost:${process.env.PORT || 4280}`;
}

module.exports = { db, now, getSetting, setSetting, queueMail, baseUrl, DEFAULT_SETTINGS };
