const test = require('node:test');
const assert = require('node:assert');
const { hashPassword, verifyPassword, isEmail, csvRow, newToken } = require('../lib');

test('password hashes verify', () => {
  const hash = hashPassword('correct horse');
  assert.ok(verifyPassword('correct horse', hash));
  assert.ok(!verifyPassword('wrong', hash));
  assert.ok(!verifyPassword('anything', null));
});

test('hashes are salted', () => {
  assert.notStrictEqual(hashPassword('same'), hashPassword('same'));
});

test('email validation', () => {
  assert.ok(isEmail('dana@customer.test'));
  assert.ok(!isEmail('dana at customer'));
  assert.ok(!isEmail(''));
});

test('csv cells are quoted when needed', () => {
  assert.strictEqual(csvRow([1, 'plain', 'a, b', 'say "hi"']), '1,plain,"a, b","say ""hi"""');
});

test('tokens are unique', () => {
  assert.notStrictEqual(newToken(), newToken());
});
