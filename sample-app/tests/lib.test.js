const test = require('node:test');
const assert = require('node:assert');
const { hashPassword, verifyPassword, isValidEmail } = require('../lib');

test('password hashes verify', () => {
  const stored = hashPassword('hunter2');
  assert.ok(verifyPassword('hunter2', stored));
  assert.ok(!verifyPassword('wrong', stored));
});

test('hashes are salted', () => {
  assert.notStrictEqual(hashPassword('a'), hashPassword('a'));
});

test('email validation', () => {
  assert.ok(isValidEmail('a@b.co'));
  assert.ok(!isValidEmail('nope'));
  assert.ok(!isValidEmail(''));
});
