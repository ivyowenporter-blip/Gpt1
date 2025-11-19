const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PUBLIC_DIR = path.join(__dirname, 'public');
const sessions = new Map();
const sockets = new Set();

function createServer() {
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const { pathname } = url;

    try {
      if (req.method === 'POST' && pathname === '/api/session/start') {
        return handleStartSession(req, res);
      }

      const stopMatch = pathname.match(/^\/api\/session\/([^/]+)\/stop$/);
      if (req.method === 'POST' && stopMatch) {
        return handleStopSession(res, stopMatch[1]);
      }

      const commandMatch = pathname.match(/^\/api\/session\/([^/]+)\/command$/);
      if (req.method === 'POST' && commandMatch) {
        return handleCommand(req, res, commandMatch[1]);
      }

      if (req.method === 'GET') {
        return serveStatic(res, pathname);
      }

      sendJson(res, 404, { error: 'Not found' });
    } catch (error) {
      console.error('Request handling error', error);
      sendJson(res, 500, { error: 'Internal server error' });
    }
  });

  server.on('upgrade', (req, socket) => {
    if (req.url !== '/ws') {
      socket.destroy();
      return;
    }
    acceptWebSocket(req, socket);
  });

  return server;
}

function handleStartSession(_req, res) {
  const sessionId = crypto.randomUUID();
  sessions.set(sessionId, { id: sessionId, active: true, logs: [] });
  sendJson(res, 200, { sessionId });
}

function handleStopSession(res, sessionId) {
  const session = sessions.get(sessionId);
  if (!session) {
    sendJson(res, 404, { error: 'Session not found' });
    return;
  }
  session.active = false;
  appendLog(sessionId, {
    id: crypto.randomUUID(),
    type: 'system',
    role: 'system',
    content: 'Session stopped.',
    timestamp: Date.now()
  });
  sendJson(res, 200, { ok: true });
}

async function handleCommand(req, res, sessionId) {
  const session = sessions.get(sessionId);
  if (!session || !session.active) {
    sendJson(res, 400, { error: 'Session is not active' });
    return;
  }

  const body = await readJson(req).catch(() => null);
  if (!body || typeof body.text !== 'string' || !body.text.trim()) {
    sendJson(res, 400, { error: 'Command text is required' });
    return;
  }

  const sanitized = body.text.trim();
  const userEntry = {
    id: crypto.randomUUID(),
    type: 'user',
    role: 'user',
    content: sanitized,
    timestamp: Date.now()
  };

  appendLog(sessionId, userEntry);
  simulateAutomation(sessionId, sanitized);
  sendJson(res, 200, { ok: true });
}

function simulateAutomation(sessionId, commandText) {
  const aiEntry = {
    id: crypto.randomUUID(),
    type: 'ai',
    role: 'assistant',
    content: `AI is processing: "${commandText}"`,
    timestamp: Date.now() + 300,
    render: {
      type: 'html',
      title: 'AI reasoning',
      html: `<div style="font-family:system-ui;padding:12px;background:#f6f8ff;border-radius:8px;">` +
        `<h4 style="margin:0 0 8px">Planned steps</h4>` +
        `<ol style="margin:0;padding-left:18px">` +
        `<li>Interpret: ${escapeHtml(commandText)}</li>` +
        '<li>Execute browser automation</li>' +
        '<li>Return summary & screenshot</li>' +
        '</ol></div>'
    }
  };

  const browserEntry = {
    id: crypto.randomUUID(),
    type: 'browser',
    role: 'browser',
    action: 'navigate',
    content: `Browser automation ran with context derived from "${commandText}"`,
    timestamp: Date.now() + 900,
    render: {
      type: 'screenshot',
      title: 'Mock browser output',
      url: '/assets/mock-screenshot.svg',
      description: 'Synthetic preview of the current page.'
    }
  };

  setTimeout(() => appendLog(sessionId, aiEntry), 400);
  setTimeout(() => appendLog(sessionId, browserEntry), 1000);
}

function appendLog(sessionId, entry) {
  const session = sessions.get(sessionId);
  if (!session) return;
  const enriched = {
    ...entry,
    sessionId,
    timestamp: entry.timestamp || Date.now()
  };
  session.logs.push(enriched);
  broadcast({ event: 'log', data: { sessionId, entry: enriched } });
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end', () => {
      try {
        const json = JSON.parse(Buffer.concat(chunks).toString() || '{}');
        resolve(json);
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body)
  });
  res.end(body);
}

function serveStatic(res, pathname) {
  const safePath = pathname === '/' ? '/index.html' : pathname;
  const filePath = path.join(PUBLIC_DIR, safePath);
  if (!filePath.startsWith(PUBLIC_DIR)) {
    sendJson(res, 403, { error: 'Forbidden' });
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      sendJson(res, 404, { error: 'Not found' });
      return;
    }

    const stream = fs.createReadStream(filePath);
    res.writeHead(200, { 'Content-Type': getMime(path.extname(filePath)) });
    stream.pipe(res);
  });
}

function getMime(ext) {
  const table = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png'
  };
  return table[ext] || 'application/octet-stream';
}

function acceptWebSocket(req, socket) {
  const key = req.headers['sec-websocket-key'];
  if (!key) {
    socket.destroy();
    return;
  }

  const acceptKey = crypto
    .createHash('sha1')
    .update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
    .digest('base64');

  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\n' +
      'Upgrade: websocket\r\n' +
      'Connection: Upgrade\r\n' +
      `Sec-WebSocket-Accept: ${acceptKey}\r\n` +
      '\r\n'
  );

  const client = { socket };
  sockets.add(client);

  socket.on('data', buffer => {
    const opcode = buffer[0] & 0x0f;
    if (opcode === 0x8) {
      socket.end();
    }
  });

  socket.on('close', () => sockets.delete(client));
  socket.on('error', () => sockets.delete(client));
}

function broadcast(message) {
  const payload = JSON.stringify(message);
  const frame = encodeFrame(payload);
  for (const client of sockets) {
    try {
      client.socket.write(frame);
    } catch (error) {
      sockets.delete(client);
    }
  }
}

function encodeFrame(data) {
  const payload = Buffer.from(data);
  const payloadLength = payload.length;
  let header;

  if (payloadLength < 126) {
    header = Buffer.alloc(2);
    header[0] = 0x81;
    header[1] = payloadLength;
  } else if (payloadLength < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x81;
    header[1] = 126;
    header.writeUInt16BE(payloadLength, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x81;
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(payloadLength), 2);
  }

  return Buffer.concat([header, payload]);
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

const server = createServer();
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
