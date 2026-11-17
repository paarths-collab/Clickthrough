// Shared helpers for every page.
const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch { /* no body */ }
  return { ok: res.ok, status: res.status, data };
}

function when(ms) {
  return ms ? new Date(ms).toLocaleString() : '';
}

function say(id, text, kind) {
  const el = $(id);
  el.textContent = text;
  el.className = `msg ${kind || ''}`;
}

const param = (name) => new URLSearchParams(location.search).get(name);
const badge = (text) => `<span class="badge ${esc(text)}">${esc(text)}</span>`;

const NAV = {
  customer: [
    ['My tickets', '/portal.html'],
    ['New ticket', '/new-ticket.html'],
    ['Help centre', '/help.html'],
  ],
  agent: [
    ['Dashboard', '/dashboard.html'],
    ['Inbox', '/inbox.html'],
    ['Canned replies', '/canned.html'],
    ['API token', '/token.html'],
  ],
  admin: [
    ['Dashboard', '/dashboard.html'],
    ['Inbox', '/inbox.html'],
    ['Canned replies', '/canned.html'],
    ['API token', '/token.html'],
    ['Team', '/team.html'],
    ['Settings', '/settings.html'],
    ['Export tickets', '/api/export.csv'],
  ],
};

// Loads the logged-in user, draws the sidebar, and checks the page is for them.
async function boot(roles) {
  const me = await api('GET', '/api/me');
  if (!me.ok) {
    location.href = '/';
    return new Promise(() => {});
  }
  const user = me.data;
  const brand = await api('GET', '/api/brand');
  const links = NAV[user.role].map(([label, href]) =>
    `<a href="${href}" class="${location.pathname === href ? 'here' : ''}">${label}</a>`).join('');
  $('sidebar').innerHTML = `<h2>${esc(brand.data.company_name || 'Helpline')}</h2><nav>${links}
    <button class="link" id="logout">Log out</button></nav>
    <p class="who">Signed in as ${esc(user.name)}<br><span class="muted">${esc(user.role)}</span></p>`;
  $('logout').addEventListener('click', async () => {
    await api('POST', '/api/logout');
    location.href = '/';
  });
  if (roles && !roles.includes(user.role)) {
    document.querySelector('main').innerHTML = '<h1>No access</h1><p>You do not have access to this page.</p>';
    return new Promise(() => {});
  }
  return user;
}

function homeFor(user) {
  return user.role === 'customer' ? '/portal.html' : '/dashboard.html';
}
