// Starts the web app and the background worker together.
const { spawn } = require('node:child_process');
const path = require('node:path');

const children = [];
for (const [name, file] of [['web', 'server.js'], ['worker', 'worker.js']]) {
  const child = spawn(process.execPath, ['--disable-warning=ExperimentalWarning', path.join(__dirname, file)], {
    stdio: 'inherit',
    env: process.env,
  });
  child.on('exit', (code, signal) => console.log(`[dev] ${name} stopped (${signal || code})`));
  children.push(child);
}

function stop() {
  for (const child of children) child.kill('SIGTERM');
  setTimeout(() => process.exit(0), 200);
}
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
