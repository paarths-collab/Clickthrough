// Background worker: sends queued email and closes stale pending tickets.
const { db, now, getSetting, queueMail, baseUrl } = require('./db');
const { isEmail } = require('./lib');

const INTERVAL = Number(process.env.WORKER_INTERVAL_MS || 1500);
const DAY = 24 * 60 * 60 * 1000;

function deliver(mail) {
  if (!isEmail(mail.to_email)) throw new Error(`Cannot deliver mail ${mail.id}: bad recipient "${mail.to_email}"`);
  // Development transport: a mail counts as sent once it is marked sent.
  // The web app lists sent mail at /dev/mail.
  db.prepare('UPDATE outbox SET sent_at = ? WHERE id = ?').run(now(), mail.id);
}

function sendQueuedMail() {
  const queued = db.prepare('SELECT * FROM outbox WHERE sent_at IS NULL ORDER BY id').all();
  for (const mail of queued) deliver(mail);
  return queued.length;
}

function closeStaleTickets() {
  const days = Number(getSetting('auto_close_days')) || 7;
  const cutoff = now() - days * DAY;
  const stale = db.prepare("SELECT * FROM tickets WHERE status = 'pending' AND created_at < ?").all(cutoff);
  for (const ticket of stale) {
    const t = now();
    db.prepare("UPDATE tickets SET status = 'closed', closed_at = ?, updated_at = ? WHERE id = ?").run(t, t, ticket.id);
    const customer = db.prepare('SELECT email FROM users WHERE id = ?').get(ticket.customer_id);
    if (customer) {
      queueMail(customer.email, `Your ticket was closed: "${ticket.subject}"`,
        `We had no reply for ${days} days, so this ticket was closed automatically. Reply to it if you still need help.\n\nOpen your ticket: ${baseUrl()}/portal-ticket.html?id=${ticket.id}`);
    }
  }
  return stale.length;
}

function tick() {
  const sent = sendQueuedMail();
  const closed = closeStaleTickets();
  if (sent || closed) console.log(`[worker] sent ${sent} mail, auto-closed ${closed} ticket(s)`);
}

console.log(`Helpline worker running (every ${INTERVAL} ms)`);
setInterval(tick, INTERVAL);
