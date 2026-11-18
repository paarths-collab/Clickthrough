---
max_turns: 8
runs: 2
allowed_tools: [Read, Glob, Grep, Skill]
---

We cannot start this app for testing (it needs a database we don't have). Audit this one user flow anyway and give your finding: "a user adds a task from the dashboard quick-add box and expects to see it in the chosen project".

dashboard.html, the quick-add form handler:
```js
const res = await fetch('/api/tasks', { method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({ title: titleInput.value, projectId: Number(projectSelect.value) }) });
if (res.ok) showToast('Task added!');
```

server.js:
```js
if (route === 'POST /api/tasks') {
  if (!body.title || !body.title.trim()) return json(res, 400, { error: 'Title is required.' });
  const info = db.prepare('INSERT INTO tasks (project_id, title) VALUES (?, ?)').run(body.project_id ?? null, body.title.trim());
  return json(res, 201, { id: Number(info.lastInsertRowid) });
}
```
