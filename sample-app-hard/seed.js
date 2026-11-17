// Puts the database back to a known state. Safe to run while the app is up.
const { db, now, DEFAULT_SETTINGS } = require('./db');
const { hashPassword } = require('./lib');

const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;
const PASSWORD = 'helpline123';

for (const table of ['sessions', 'messages', 'tickets', 'invites', 'resets', 'canned', 'settings', 'outbox', 'users']) {
  db.exec(`DELETE FROM ${table}`);
}
db.exec("DELETE FROM sqlite_sequence WHERE name IN ('users', 'tickets', 'messages', 'canned', 'outbox')");

const addUser = db.prepare('INSERT INTO users (email, name, password_hash, role, api_token) VALUES (?, ?, ?, ?, ?)');
const people = [
  ['mira@helpline.test', 'Mira Okafor', 'admin', 'hl_admin_mira_4d1f9c2a7b'],
  ['alice@helpline.test', 'Alice Brandt', 'agent', 'hl_agent_alice_8e3b6a1d0c'],
  ['bob@helpline.test', 'Bob Tanaka', 'agent', 'hl_agent_bob_2c7f5e9a4b'],
  ['dana@customer.test', 'Dana Whitfield', 'customer', null],
  ['eli@customer.test', 'Eli Navarro', 'customer', null],
];
const ids = {};
for (const [email, name, role, token] of people) {
  ids[email.split('@')[0]] = Number(addUser.run(email, name, hashPassword(PASSWORD), role, token).lastInsertRowid);
}

for (const [key, value] of Object.entries(DEFAULT_SETTINGS)) {
  db.prepare('INSERT INTO settings (key, value) VALUES (?, ?)').run(key, value);
}

const canned = [
  ['Asking for details', 'Thanks for getting in touch. Could you send us a screenshot and the exact time this happened?'],
  ['Refund sent', 'Your refund has been sent. It can take up to five working days to reach your account.'],
  ['Closing after fix', 'This should now be fixed. I will close the ticket; reply here if it happens again.'],
];
for (const [title, body] of canned) db.prepare('INSERT INTO canned (title, body) VALUES (?, ?)').run(title, body);

// subject, description, customer, status, assignee, priority, created (days ago)
const tickets = [
  ['Refund not received', 'You promised to return the money for order 8841 two weeks ago. Nothing has arrived.', 'dana', 'open', 'alice', 'high', 35],
  ['Invoice shows the wrong company name', 'The PDF for March lists "Acme Ltd". We are "Acme Holdings Ltd".', 'dana', 'open', 'alice', 'urgent', 3],
  ['Export to CSV fails', 'Clicking the button gives a blank file.', 'eli', 'open', null, 'normal', 2],
  ['Cannot add a second user', 'The Add user button is greyed out although our plan allows five seats.', 'dana', 'open', 'bob', 'normal', 6],
  ['App is slow on Monday mornings', 'Every Monday between 9 and 10 the dashboard takes a minute to load.', 'eli', 'open', 'bob', 'low', 28],
  ['Wrong time zone on reports', 'Reports show UTC. We are in Lisbon.', 'dana', 'open', null, 'normal', 1],
  ['Password reset email never arrives', 'I asked three times. I checked the spam folder.', 'eli', 'open', 'alice', 'high', 1],
  ['Charged twice in April', 'Two payments of 49.00 on the 3rd. Please return one.', 'dana', 'open', 'alice', 'urgent', 4],
  ['How do I change the billing contact?', 'Our finance person changed. Where is the setting?', 'eli', 'open', null, 'low', 5],
  ['Mobile app logs me out', 'On Android it signs me out every time I switch apps.', 'dana', 'open', 'bob', 'normal', 22],
  ['Search does not find archived projects', 'Archived items used to appear when I ticked the box.', 'eli', 'open', 'alice', 'normal', 9],
  ['Need a copy of our contract', 'Please send the signed agreement from last year.', 'dana', 'open', null, 'low', 8],
  ['Webhook deliveries are delayed', 'Events arrive 20 minutes late since Tuesday.', 'eli', 'open', 'bob', 'high', 2],
  ['Typo on the pricing page', 'It says "anual" instead of "annual".', 'dana', 'open', 'alice', 'low', 12],
  ['Two-factor codes rejected', 'The code from my authenticator is refused about half the time.', 'eli', 'open', 'alice', 'high', 3],
  ['Cancel my subscription', 'Please cancel at the end of this billing period.', 'dana', 'open', null, 'normal', 1],
  ['Import stuck at 80%', 'A spreadsheet with 4,000 rows never finishes importing.', 'eli', 'open', 'bob', 'normal', 15],
  ['Waiting for your screenshot', 'The chart on the overview page is empty for me.', 'dana', 'pending', 'alice', 'normal', 3],
  ['Is there a student discount?', 'I am using this for a university project.', 'eli', 'pending', 'alice', 'low', 2],
  ['Delivery address change', 'We moved offices. New address attached in the next message.', 'dana', 'pending', 'bob', 'normal', 4],
  ['Login page shows an error', 'A red banner said "Something went wrong". It works again now.', 'eli', 'closed', 'alice', 'normal', 40],
  ['Thank you', 'Just wanted to say the new editor is great.', 'dana', 'closed', null, 'low', 30],
  ['Wrong currency on invoice', 'Billed in USD, we agreed EUR.', 'eli', 'closed', 'bob', 'high', 26],
  ['Add our logo to reports', 'Is white-labelling possible?', 'dana', 'closed', 'alice', 'low', 21],
  ['Account locked after five tries', 'I mistyped my password. Please unlock.', 'eli', 'closed', null, 'high', 18],
  ['Data export for audit', 'We need every record from 2024 as a file.', 'dana', 'closed', 'bob', 'normal', 16],
  ['Change of account owner', 'Please move ownership to my colleague.', 'eli', 'closed', 'alice', 'normal', 14],
  ['Duplicate notifications', 'I get every email twice.', 'dana', 'closed', null, 'normal', 11],
  ['Feature request: dark mode', 'Would love a dark theme.', 'eli', 'closed', 'bob', 'low', 10],
  ['Receipt for expenses', 'Please send a receipt for the January payment.', 'dana', 'closed', 'alice', 'low', 6],
  ['Cannot upload files over 10 MB', 'The upload stops with no message.', 'eli', 'closed', null, 'normal', 5],
  ['Trial extension', 'Could we have one more week to evaluate?', 'dana', 'closed', 'bob', 'normal', 2],
];

const addTicket = db.prepare(`
  INSERT INTO tickets (customer_id, subject, description, priority, status, assignee_id, created_at, updated_at, closed_at)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`);
const base = now();
tickets.forEach(([subject, description, customer, status, assignee, priority, daysAgo], index) => {
  const created = base - daysAgo * DAY;
  const updated = Math.max(created, base - (index + 1) * 2 * HOUR);
  addTicket.run(ids[customer], subject, description, priority, status, assignee ? ids[assignee] : null,
    created, updated, status === 'closed' ? updated : null);
});

const addMessage = db.prepare('INSERT INTO messages (ticket_id, author_id, body, internal, created_at) VALUES (?, ?, ?, ?, ?)');
addMessage.run(1, ids.alice, 'Sorry about the wait. I am checking with our payments team and will come back to you today.', 0, base - 20 * HOUR);
addMessage.run(1, ids.alice, 'Legacy plan. Finance says no second refund without approval from Mira.', 1, base - 19 * HOUR);
addMessage.run(1, ids.dana, 'Thank you. The order number is 8841 in case that helps.', 0, base - 18 * HOUR);
addMessage.run(8, ids.alice, 'I can see both payments. One will be returned within five working days.', 0, base - 30 * HOUR);
addMessage.run(18, ids.alice, 'Could you send a screenshot of the empty chart?', 0, base - 40 * HOUR);
addMessage.run(21, ids.alice, 'This was a short outage on our side. It is resolved.', 0, base - 39 * DAY);
addMessage.run(23, ids.bob, 'Corrected invoice sent in EUR.', 0, base - 25 * DAY);
addMessage.run(23, ids.bob, 'Customer has a custom contract - check with sales before changing prices.', 1, base - 25 * DAY);

console.log(`Seeded: ${people.length} users, ${tickets.length} tickets, ${canned.length} canned replies.`);
console.log(`Every seeded account has the password "${PASSWORD}".`);
