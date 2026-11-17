// Wipes the database and loads demo data. Safe to run while the server is up.
const db = require('./db');
const { hashPassword } = require('./lib');

db.exec(`
  DELETE FROM invites; DELETE FROM tasks; DELETE FROM projects;
  DELETE FROM sessions; DELETE FROM users;
  DELETE FROM sqlite_sequence;
`);

const addUser = db.prepare('INSERT INTO users (email, name, password) VALUES (?, ?, ?)');
const addProject = db.prepare('INSERT INTO projects (owner_id, name) VALUES (?, ?)');
const addTask = db.prepare('INSERT INTO tasks (project_id, title, done) VALUES (?, ?, ?)');

const pw = hashPassword('password123');
const alice = addUser.run('alice@example.com', 'Alice', pw).lastInsertRowid;
const bob = addUser.run('bob@example.com', 'Bob', pw).lastInsertRowid;
addUser.run('carol@example.com', 'Carol', pw);

const website = addProject.run(alice, 'Website relaunch').lastInsertRowid;
const hiring = addProject.run(alice, 'Hiring').lastInsertRowid;
const secret = addProject.run(bob, 'Bob private plans').lastInsertRowid;

addTask.run(website, 'Write homepage copy', 0);
addTask.run(website, 'Pick a colour palette', 1);
addTask.run(website, 'Book photographer', 0);
addTask.run(hiring, 'Post the job ad', 0);
addTask.run(secret, 'Negotiate my raise', 0);

console.log('Seeded: 3 users, 3 projects, 5 tasks.');
