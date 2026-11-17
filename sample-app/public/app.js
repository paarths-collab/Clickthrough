// Shared helpers for every signed-in page.
async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  return res;
}

async function requireLogin() {
  const res = await api('GET', '/api/me');
  if (res.status === 401) { location.href = '/'; return new Promise(() => {}); }
  return res.json();
}

const NAV = [
  ['Dashboard', '/dashboard.html'],
  ['Projects', '/projects.html'],
  ['My Tasks', '/my-tasks.html'],
  ['Reports', '/reports.html'],
  ['Settings', '/settings.html'],
];

function renderSidebar(user) {
  const el = document.getElementById('sidebar');
  el.innerHTML = '<h1>Tasklet</h1>' + NAV.map(([label, href]) =>
    `<a href="${href}" class="${location.pathname === href ? 'active' : ''}">${label}</a>`
  ).join('') + `<div class="who">Signed in as <strong id="who-name"></strong><br>
    <button id="logout">Log out</button></div>`;
  document.getElementById('who-name').textContent = user.name;
  document.getElementById('logout').onclick = async () => {
    await api('POST', '/api/logout');
    location.href = '/';
  };
}

function esc(text) {
  const span = document.createElement('span');
  span.textContent = text;
  return span.innerHTML;
}

async function boot() {
  const user = await requireLogin();
  renderSidebar(user);
  return user;
}
