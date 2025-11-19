const startButton = document.getElementById('start-session');
const stopButton = document.getElementById('stop-session');
const indicator = document.getElementById('session-indicator');
const sessionLabel = document.getElementById('session-label');
const commandForm = document.getElementById('command-form');
const commandInput = document.getElementById('command-input');
const logList = document.getElementById('log-list');
const renderTarget = document.getElementById('render-target');

const logTemplate = document.getElementById('log-entry-template');

const sessionLogs = new Map();
let currentSessionId = null;
let socket;

init();

function init() {
  bindEvents();
  connectSocket();
}

function bindEvents() {
  startButton.addEventListener('click', async () => {
    const res = await fetch('/api/session/start', { method: 'POST' });
    const data = await res.json();
    currentSessionId = data.sessionId;
    sessionLogs.set(currentSessionId, []);
    updateSessionUi(true);
    logList.innerHTML = '';
    renderTarget.innerHTML = '<div class="render-placeholder">Waiting for automation output…</div>';
  });

  stopButton.addEventListener('click', async () => {
    if (!currentSessionId) return;
    await fetch(`/api/session/${currentSessionId}/stop`, { method: 'POST' });
    updateSessionUi(false);
    currentSessionId = null;
  });

  commandForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (!currentSessionId) return;
    const value = commandInput.value.trim();
    if (!value) return;
    commandInput.value = '';
    await fetch(`/api/session/${currentSessionId}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: value })
    });
  });
}

function connectSocket() {
  socket = new WebSocket(getWsUrl());
  socket.addEventListener('message', event => {
    const payload = JSON.parse(event.data);
    if (payload.event === 'log') {
      handleLog(payload.data.sessionId, payload.data.entry);
    }
  });
  socket.addEventListener('close', () => {
    setTimeout(connectSocket, 1000);
  });
}

function handleLog(sessionId, entry) {
  if (!sessionLogs.has(sessionId)) {
    sessionLogs.set(sessionId, []);
  }
  const logs = sessionLogs.get(sessionId);
  logs.push(entry);
  if (sessionId === currentSessionId) {
    appendLog(entry);
    if (entry.render) {
      renderPreview(entry.render);
    }
  }
}

function appendLog(entry) {
  const node = logTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(entry.type);
  node.querySelector('.log-role').textContent = formatRole(entry);
  node.querySelector('.log-time').textContent = new Date(entry.timestamp || Date.now()).toLocaleTimeString();
  node.querySelector('.log-content').textContent = entry.content;

  if (entry.action) {
    const actionEl = node.querySelector('.log-action');
    actionEl.textContent = entry.action;
    actionEl.classList.remove('hidden');
  }

  logList.appendChild(node);
  logList.scrollTop = logList.scrollHeight;
}

function renderPreview(render) {
  if (render.type === 'html') {
    const iframe = document.createElement('iframe');
    iframe.className = 'render-html';
    iframe.setAttribute('sandbox', 'allow-same-origin');
    iframe.srcdoc = render.html;
    renderTarget.innerHTML = '';
    renderTarget.appendChild(iframe);
  } else if (render.type === 'screenshot') {
    const img = document.createElement('img');
    img.className = 'render-screenshot';
    img.src = render.url;
    img.alt = render.description || 'Screenshot';
    renderTarget.innerHTML = '';
    renderTarget.appendChild(img);
  }
}

function formatRole(entry) {
  switch (entry.type) {
    case 'user':
      return 'User';
    case 'ai':
      return 'AI Assistant';
    case 'browser':
      return 'Browser Action';
    case 'system':
      return 'System';
    default:
      return entry.type;
  }
}

function updateSessionUi(active) {
  if (active) {
    indicator.textContent = 'Session active';
    indicator.style.background = '#bbf7d0';
    sessionLabel.textContent = `Session: ${currentSessionId}`;
  } else {
    indicator.textContent = 'No session';
    indicator.style.background = '#e2e8f0';
    sessionLabel.textContent = 'No active session';
  }
  startButton.disabled = active;
  stopButton.disabled = !active;
}

function getWsUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/ws`;
}
