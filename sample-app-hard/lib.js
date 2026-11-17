const crypto = require('node:crypto');

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 32).toString('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(password, stored) {
  if (!stored || !stored.includes(':')) return false;
  const [salt, hash] = stored.split(':');
  const candidate = crypto.scryptSync(password, salt, 32);
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), candidate);
}

function isEmail(value) {
  return typeof value === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function newToken() {
  return crypto.randomBytes(24).toString('hex');
}

function csvCell(value) {
  const text = value === null || value === undefined ? '' : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function csvRow(cells) {
  return cells.map(csvCell).join(',');
}

const STATUSES = ['open', 'pending', 'closed'];
const PRIORITIES = ['low', 'normal', 'high', 'urgent'];

module.exports = { hashPassword, verifyPassword, isEmail, newToken, csvCell, csvRow, STATUSES, PRIORITIES };
