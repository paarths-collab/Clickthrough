// Helpline MCP server (stdio, newline-delimited JSON-RPC 2.0).
// Lets an AI assistant work the support inbox on behalf of one agent.
// Set HELPLINE_TOKEN to that agent's API token (web app > API token).
const readline = require('node:readline');
const { db, now, queueMail, baseUrl } = require('./db');
const { STATUSES, PRIORITIES } = require('./lib');

const TOOLS = [
  {
    name: 'list_tickets',
    description: 'List tickets, newest activity first. Optionally filter by status and by the assigned agent.',
    inputSchema: {
      type: 'object',
      properties: {
        status: { type: 'string', enum: STATUSES, description: 'Only tickets with this status.' },
        assignee_email: { type: 'string', description: 'Only tickets assigned to this agent.' },
      },
    },
  },
  {
    name: 'get_ticket',
    description: 'Get one ticket with its full conversation, including internal notes.',
    inputSchema: { type: 'object', properties: { id: { type: 'integer' } }, required: ['id'] },
  },
  {
    name: 'create_ticket',
    description: 'Open a ticket on behalf of a customer. If the customer has no account yet, one is created.',
    inputSchema: {
      type: 'object',
      properties: {
        customer_email: { type: 'string' },
        subject: { type: 'string' },
        description: { type: 'string' },
        priority: { type: 'string', enum: PRIORITIES },
      },
      required: ['customer_email', 'subject', 'description'],
    },
  },
  {
    name: 'add_reply',
    description: 'Add a reply to a ticket. Set internal to true for a note only the team can see; otherwise the customer sees it and is emailed.',
    inputSchema: {
      type: 'object',
      properties: {
        ticket_id: { type: 'integer' },
        body: { type: 'string' },
        internal: { type: 'boolean', description: 'true = internal note, never shown to the customer.' },
      },
      required: ['ticket_id', 'body'],
    },
  },
  {
    name: 'set_status',
    description: 'Change the status of a ticket.',
    inputSchema: {
      type: 'object',
      properties: { ticket_id: { type: 'integer' }, status: { type: 'string', enum: STATUSES } },
      required: ['ticket_id', 'status'],
    },
  },
  {
    name: 'assign_ticket',
    description: 'Assign a ticket to an agent, by the agent email address.',
    inputSchema: {
      type: 'object',
      properties: { ticket_id: { type: 'integer' }, agent_email: { type: 'string' } },
      required: ['ticket_id', 'agent_email'],
    },
  },
];

function actor() {
  const token = process.env.HELPLINE_TOKEN;
  if (!token) throw new Error('HELPLINE_TOKEN is not set. Use an agent API token from the web app.');
  const user = db.prepare("SELECT * FROM users WHERE api_token = ? AND active = 1 AND role IN ('agent', 'admin')").get(token);
  if (!user) throw new Error('HELPLINE_TOKEN does not match an active agent.');
  return user;
}

function getTicket(id) {
  const ticket = db.prepare('SELECT * FROM tickets WHERE id = ?').get(Number(id));
  if (!ticket) throw new Error(`Ticket ${id} not found.`);
  return ticket;
}

const SUMMARY = `
  SELECT t.id, t.subject, t.status, t.priority, c.email AS customer_email, a.email AS assignee_email, t.updated_at
  FROM tickets t LEFT JOIN users c ON c.id = t.customer_id LEFT JOIN users a ON a.id = t.assignee_id`;

const HANDLERS = {
  list_tickets(args) {
    const where = [];
    const params = [];
    if (args.state) { where.push('t.status = ?'); params.push(args.state); }
    if (args.assignee_email) { where.push('a.email = ?'); params.push(args.assignee_email); }
    const filter = where.length ? `WHERE ${where.join(' AND ')}` : '';
    return db.prepare(`${SUMMARY} ${filter} ORDER BY t.updated_at DESC`).all(...params);
  },

  get_ticket(args) {
    const ticket = getTicket(args.id);
    const customer = db.prepare('SELECT name, email FROM users WHERE id = ?').get(ticket.customer_id) || null;
    const messages = db.prepare(`
      SELECT m.body, m.internal, m.created_at, u.name AS author
      FROM messages m JOIN users u ON u.id = m.author_id WHERE m.ticket_id = ? ORDER BY m.id`).all(ticket.id);
    return { ...ticket, customer, messages: messages.map((msg) => ({ ...msg, internal: Boolean(msg.internal) })) };
  },

  create_ticket(args) {
    if (!args.subject || !args.description) throw new Error('subject and description are required.');
    const priority = PRIORITIES.includes(args.priority) ? args.priority : 'normal';
    const customer = db.prepare('SELECT id FROM users WHERE email = ?').get(String(args.customer_email || '').toLowerCase());
    const t = now();
    const id = Number(db.prepare(
      'INSERT INTO tickets (customer_id, subject, description, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
    ).run(customer ? customer.id : null, args.subject, args.description, priority, 'open', t, t).lastInsertRowid);
    return { id, url: `${baseUrl()}/ticket.html?id=${id}` };
  },

  add_reply(args, user) {
    const ticket = getTicket(args.ticket_id);
    if (!args.body) throw new Error('body is required.');
    const internal = args.is_internal ? 1 : 0;
    const t = now();
    db.prepare('INSERT INTO messages (ticket_id, author_id, body, internal, created_at) VALUES (?, ?, ?, ?, ?)')
      .run(ticket.id, user.id, args.body, internal, t);
    db.prepare('UPDATE tickets SET updated_at = ? WHERE id = ?').run(t, ticket.id);
    if (!internal) {
      const customer = db.prepare('SELECT email FROM users WHERE id = ?').get(ticket.customer_id);
      if (customer) {
        queueMail(customer.email, `New reply on "${ticket.subject}"`,
          `${args.body}\n\nOpen your ticket: ${baseUrl()}/portal-ticket.html?id=${ticket.id}`);
      }
    }
    return { ok: true, internal: Boolean(internal) };
  },

  set_status(args) {
    const ticket = getTicket(args.ticket_id);
    if (!STATUSES.includes(args.status)) throw new Error(`status must be one of: ${STATUSES.join(', ')}`);
    const t = now();
    db.prepare('UPDATE tickets SET status = ?, closed_at = ?, updated_at = ? WHERE id = ?')
      .run(args.status, args.status === 'closed' ? t : null, t, ticket.id);
    return { ok: true, status: args.status };
  },

  assign_ticket(args) {
    const ticket = getTicket(args.ticket_id);
    const agent = db.prepare("SELECT id, email FROM users WHERE email = ? AND active = 1 AND role IN ('agent', 'admin')")
      .get(String(args.agent_email || '').toLowerCase());
    if (!agent) throw new Error(`No active agent with email ${args.agent_email}.`);
    db.prepare('UPDATE tickets SET assignee_id = ?, updated_at = ? WHERE id = ?').run(agent.id, now(), ticket.id);
    return { ok: true, assignee_email: agent.email };
  },
};

function send(message) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}

function handle(message) {
  const { id, method, params = {} } = message;
  if (id === undefined) return; // notification: nothing to answer
  if (method === 'initialize') {
    return send({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: params.protocolVersion || '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'helpline', version: '1.0.0' },
      },
    });
  }
  if (method === 'ping') return send({ jsonrpc: '2.0', id, result: {} });
  if (method === 'tools/list') return send({ jsonrpc: '2.0', id, result: { tools: TOOLS } });
  if (method === 'tools/call') {
    const tool = HANDLERS[params.name];
    if (!tool) return send({ jsonrpc: '2.0', id, error: { code: -32602, message: `Unknown tool: ${params.name}` } });
    try {
      const result = tool(params.arguments || {}, actor());
      return send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] } });
    } catch (err) {
      return send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: err.message }], isError: true } });
    }
  }
  return send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
}

readline.createInterface({ input: process.stdin }).on('line', (line) => {
  if (!line.trim()) return;
  let message;
  try { message = JSON.parse(line); } catch {
    return send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } });
  }
  handle(message);
});
