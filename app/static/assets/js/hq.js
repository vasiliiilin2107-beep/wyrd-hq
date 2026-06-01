/* ─── STARFIELD ─────────────────────────────────────── */
function initStars(canvas) {
  const ctx = canvas.getContext('2d');
  let stars = [];
  let W, H, raf;

  function buildStars(w, h) {
    stars = [];
    const n = Math.floor((w * h) / 3200);
    for (let i = 0; i < n; i++) {
      const bright = Math.random() > 0.9;
      stars.push({
        x: Math.random() * w, y: Math.random() * h,
        r: bright ? Math.random() * 1.0 + 0.5 : Math.random() * 0.8 + 0.1,
        a: bright ? Math.random() * 0.5 + 0.3 : Math.random() * 0.35 + 0.05,
        twinkle: Math.random() > 0.65,
        ph: Math.random() * Math.PI * 2,
        sp: Math.random() * 0.5 + 0.2,
      });
    }
  }

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    buildStars(W, H);
  }

  function frame(t) {
    ctx.clearRect(0, 0, W, H);
    const ts = t * 0.001;
    stars.forEach(s => {
      const a = s.twinkle ? s.a * (0.55 + 0.45 * Math.sin(ts * s.sp + s.ph)) : s.a;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${a.toFixed(3)})`;
      ctx.fill();
    });
    raf = requestAnimationFrame(frame);
  }

  window.addEventListener('resize', resize);
  resize();
  raf = requestAnimationFrame(frame);
}

/* ─── CLOCK ─────────────────────────────────────────── */
function startClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  function tick() {
    const now = new Date();
    const msk = new Date(now.getTime() + (now.getTimezoneOffset() + 180) * 60000);
    el.textContent = msk.toLocaleTimeString('ru-RU', { hour12: false }) + ' МСК';
  }
  tick();
  setInterval(tick, 1000);
}

/* ─── TAB SWITCHING ─────────────────────────────────── */
const TAB_LABELS = {
  map:          'КАРТА МИРА',
  notes:        'ЗАМЕТКИ',
  tasks:        'ДОСКА ЗАДАЧ',
  build:        'СТРОЙКА',
  technik:      'ТЕХНИК',
  ideas:        'ИДЕИ',
  files:        'ФАЙЛЫ ТОМАСА',
  library:      'БИБЛИОТЕКА',
  constitution: 'КОНСТИТУЦИЯ',
  scribe:       'SCRIBE',
};

function setTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.nav-btn[data-tab]').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.style.display = 'flex';
  if (btn) btn.classList.add('active');
  const label = document.getElementById('tab-label');
  if (label) label.textContent = TAB_LABELS[name] || name.toUpperCase();

  if (name === 'map')     initMap();
  if (name === 'notes')   loadNotes();
  if (name === 'tasks')   loadTasks();
  if (name === 'technik') loadTechTasks();
  if (name === 'ideas')   loadIdeas();
}

/* ─── BRANCH COLORS ─────────────────────────────────── */
const BRANCH_COLORS = {
  studio:   '#8b5cf6',
  thomas:   '#3b82f6',
  'wyrd-hq':'#f59e0b',
  hq:       '#f59e0b',
  library:  '#10b981',
  analytics:'#f97316',
  finance:  '#ef4444',
};
function branchColor(name) {
  const key = name.toLowerCase().replace(/[\s-]/g, '');
  for (const [k,v] of Object.entries(BRANCH_COLORS)) {
    if (key.includes(k)) return v;
  }
  return '#6366f1';
}

/* ─── BRANCHES ──────────────────────────────────────── */
async function loadBranches() {
  const grid = document.getElementById('branches-grid');
  if (!grid) return;
  try {
    const res  = await fetch('/branches');
    const data = await res.json();
    const list = Array.isArray(data) ? data : data.branches || [];
    grid.innerHTML = '';
    if (!list.length) {
      grid.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Нет активных веток</div>';
      return;
    }
    list.forEach(b => {
      const color = branchColor(b.name || '');
      const lastSeen = b.last_seen ? timeAgo(b.last_seen) : '—';
      const card = document.createElement('div');
      card.className = 'branch-card';
      card.style.setProperty('--node-color', color);
      card.innerHTML = `
        <div class="branch-name">${(b.name || 'branch').toUpperCase()}</div>
        <div class="branch-status">
          <span class="dot" style="background:${color};box-shadow:0 0 6px ${color}"></span>
          ${b.status || 'online'}
        </div>
        <div class="branch-last">${lastSeen}</div>
      `;
      grid.appendChild(card);
    });
  } catch {
    if (grid) grid.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Нет связи с HQ API</div>';
  }
}

/* ─── ЖИВАЯ ЛЕНТА ────────────────────────────────────── */
const TECH_FEED_COLORS = { pending:'#f59e0b', running:'#3b82f6', done:'#10b981', failed:'#ef4444', waiting_approval:'#8b5cf6' };
const TECH_FEED_ICONS  = { pending:'⏳', running:'⚙️', done:'✅', failed:'❌', waiting_approval:'🔔' };
const IDEA_STATUS_COLORS = { idea:'#f59e0b', testing:'#3b82f6', active:'#10b981', archived:'#6b7280' };

async function loadEvents() {
  const feed = document.getElementById('event-feed');
  if (!feed) return;

  const items = [];

  try {
    const r = await fetch('/tech/tasks?limit=10');
    if (r.ok) {
      const tasks = await r.json();
      (Array.isArray(tasks) ? tasks : []).slice(0, 6).forEach(t => {
        items.push({
          icon:  TECH_FEED_ICONS[t.status]  || '🔧',
          color: TECH_FEED_COLORS[t.status] || '#6b7280',
          label: 'ТЕХНИК',
          text:  t.title,
          time:  t.updated_at || t.created_at,
        });
      });
    }
  } catch {}

  try {
    const r = await fetch('/income/ideas?limit=6');
    if (r.ok) {
      const d = await r.json();
      (d.ideas || []).slice(0, 4).forEach(i => {
        items.push({
          icon:  '💡',
          color: IDEA_STATUS_COLORS[i.status] || '#f59e0b',
          label: 'ИДЕЯ',
          text:  i.title,
          time:  i.updated_at || i.created_at,
        });
      });
    }
  } catch {}

  try {
    const r = await fetch('/library/recent?limit=6');
    if (r.ok) {
      const d = await r.json();
      (d.items || []).slice(0, 4).forEach(k => {
        items.push({
          icon:  '📚',
          color: '#10b981',
          label: k.category || 'world',
          text:  k.question,
          time:  null,
        });
      });
    }
  } catch {}

  try {
    const r = await fetch('/events?limit=20');
    if (r.ok) {
      const d = await r.json();
      const EVT = {
        agent_born:           {ic:'🐣', col:'#a855f7', lbl:'АГЕНТ'},
        agent_dna_rejected:   {ic:'❌', col:'#ef4444', lbl:'ДНК ОТКЛОНЕНА'},
        agent_passport_issued:{ic:'🎫', col:'#4a9eff', lbl:'ПАСПОРТ'},
        proposal_submitted:   {ic:'📝', col:'#f59e0b', lbl:'ПРЕДЛОЖЕНИЕ'},
        analytics_report:     {ic:'📊', col:'#ffaa00', lbl:'АНАЛИТИКА'},
        babla_report:         {ic:'💰', col:'#44ff44', lbl:'БАБЛО'},
        idea_report:          {ic:'💡', col:'#cc44ff', lbl:'ИДЕЙНЫЙ'},
      };
      (d.events || d || []).slice(0, 8).forEach(ev => {
        const cfg = EVT[ev.type];
        if (!cfg) return;
        const payload = ev.payload || {};
        const text = payload.name || payload.agent || payload.summary || ev.type;
        items.push({ icon: cfg.ic, color: cfg.col, label: cfg.lbl, text, time: ev.created_at });
      });
    }
  } catch {}

  items.sort((a, b) => {
    if (!a.time && !b.time) return 0;
    if (!a.time) return 1;
    if (!b.time) return -1;
    return new Date(b.time) - new Date(a.time);
  });

  if (!items.length) {
    feed.innerHTML = '<div class="feed-branch">Нет активности</div>';
    return;
  }

  feed.innerHTML = items.map(it => `
    <div class="feed-item">
      <div style="display:flex;align-items:center;gap:5px;margin-bottom:2px">
        <span style="font-size:.75rem">${it.icon}</span>
        <span class="feed-branch" style="color:${it.color};font-weight:700">${escHtml(it.label)}</span>
        ${it.time ? `<span class="feed-time" style="margin-left:auto">${timeAgo(it.time)}</span>` : ''}
      </div>
      <div class="feed-payload">${escHtml(it.text)}</div>
    </div>
  `).join('');
}

/* ─── WEBSOCKET ─────────────────────────────────────── */
function initWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data);
      if (data.type !== 'ping') loadEvents();
    } catch {}
  };
  ws.onclose = () => setTimeout(initWS, 3000);
}

/* ─── NOTES ─────────────────────────────────────────── */
async function loadNotes() {
  const list = document.getElementById('notes-list');
  if (!list) return;
  list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Загрузка...</div>';
  try {
    const res = await fetch('/notes');
    const notes = await res.json();
    renderNotes(notes);
  } catch {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
}

function renderNotes(notes) {
  const list = document.getElementById('notes-list');
  if (!list) return;
  list.innerHTML = '';
  if (!notes.length) {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:12px 0">Заметок пока нет</div>';
    return;
  }
  notes.forEach(n => {
    const item = document.createElement('div');
    item.className = 'note-item';
    item.dataset.id = n.id;
    const time = n.created_at ? new Date(n.created_at).toLocaleString('ru-RU', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' }) : '';
    item.innerHTML = `
      <div class="note-text">${escHtml(n.text)}</div>
      <div class="note-meta">
        <span class="note-time">${time}</span>
        <button class="note-del" onclick="deleteNote(${n.id})" title="Удалить">✕</button>
      </div>
    `;
    list.appendChild(item);
  });
}

async function addNote() {
  const input = document.getElementById('note-input');
  const text = input.value.trim();
  if (!text) return;
  try {
    const res = await fetch('/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const note = await res.json();
    input.value = '';
    await loadNotes();
  } catch { /* silent */ }
}

async function deleteNote(id) {
  try {
    await fetch(`/notes/${id}`, { method: 'DELETE' });
    const item = document.querySelector(`.note-item[data-id="${id}"]`);
    if (item) item.remove();
    const list = document.getElementById('notes-list');
    if (list && !list.children.length) {
      list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:12px 0">Заметок пока нет</div>';
    }
  } catch { /* silent */ }
}

/* ─── TASKS ─────────────────────────────────────────── */
const STATUS_ORDER = ['todo', 'in_progress', 'done'];

async function loadTasks() {
  ['todo','in_progress','done'].forEach(s => {
    const el = document.getElementById('cards-' + s);
    if (el) el.innerHTML = '';
  });
  try {
    const res = await fetch('/tasks');
    const tasks = await res.json();
    renderTasks(tasks);
  } catch { /* silent */ }
}

function renderTasks(tasks) {
  ['todo','in_progress','done'].forEach(s => {
    const el = document.getElementById('cards-' + s);
    if (el) el.innerHTML = '';
  });
  tasks.forEach(t => renderTaskCard(t));
}

function renderTaskCard(t) {
  const col = document.getElementById('cards-' + t.status);
  if (!col) return;
  const card = document.createElement('div');
  card.className = 'task-card';
  card.dataset.id = t.id;
  card.dataset.status = t.status;

  const idx = STATUS_ORDER.indexOf(t.status);
  const canLeft  = idx > 0;
  const canRight = idx < STATUS_ORDER.length - 1;

  card.innerHTML = `
    <div class="task-title">${escHtml(t.title)}</div>
    <div class="task-actions">
      <button class="task-btn" onclick="moveTask(${t.id},'${STATUS_ORDER[idx-1]}')" ${canLeft ? '' : 'disabled'} title="Назад">←</button>
      <button class="task-btn task-btn-del" onclick="deleteTask(${t.id})" title="Удалить">✕</button>
      <button class="task-btn" onclick="moveTask(${t.id},'${STATUS_ORDER[idx+1]}')" ${canRight ? '' : 'disabled'} title="Вперёд">→</button>
    </div>
  `;
  col.appendChild(card);
}

function showTaskInput(status) {
  const form = document.getElementById('add-form-' + status);
  if (form) { form.style.display = 'block'; }
  const input = document.getElementById('task-input-' + status);
  if (input) { input.focus(); }
}

function hideTaskInput(status) {
  const form = document.getElementById('add-form-' + status);
  if (form) form.style.display = 'none';
  const input = document.getElementById('task-input-' + status);
  if (input) input.value = '';
}

function taskInputKey(e, status) {
  if (e.key === 'Enter') addTask(status);
  if (e.key === 'Escape') hideTaskInput(status);
}

async function addTask(status) {
  const input = document.getElementById('task-input-' + status);
  const title = input ? input.value.trim() : '';
  if (!title) return;
  try {
    const res = await fetch('/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, status }),
    });
    const task = await res.json();
    hideTaskInput(status);
    renderTaskCard(task);
  } catch { /* silent */ }
}

async function moveTask(id, newStatus) {
  if (!newStatus) return;
  try {
    const res = await fetch(`/tasks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
    const task = await res.json();
    const old = document.querySelector(`.task-card[data-id="${id}"]`);
    if (old) old.remove();
    renderTaskCard(task);
  } catch { /* silent */ }
}

async function deleteTask(id) {
  try {
    await fetch(`/tasks/${id}`, { method: 'DELETE' });
    const card = document.querySelector(`.task-card[data-id="${id}"]`);
    if (card) card.remove();
  } catch { /* silent */ }
}

/* ─── HELPERS ───────────────────────────────────────── */
function timeAgo(isoStr) {
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
  if (diff < 60)    return 'только что';
  if (diff < 3600)  return `${Math.floor(diff/60)} мин назад`;
  if (diff < 86400) return `${Math.floor(diff/3600)} ч назад`;
  return `${Math.floor(diff/86400)} д назад`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/\n/g,'<br>');
}

/* ─── TOPBAR STATS ──────────────────────────────────── */
async function loadTopbarStats() {
  try {
    const r = await fetch('/civilization/agents');
    if (r.ok) {
      const d = await r.json();
      const agents = d.agents || [];
      const now = Date.now();
      const live = agents.filter(a => {
        if (a.status !== 'active') return false;
        const ms = a.last_pulse ? now - new Date(a.last_pulse+'Z').getTime() : Infinity;
        return ms < 600000;
      }).length;
      const el = document.getElementById('stat-live');
      if (el) el.textContent = live;
    }
  } catch {}
  try {
    const r = await fetch('/tech/tasks?status=running&limit=50');
    if (r.ok) {
      const d = await r.json();
      const tasks = Array.isArray(d) ? d : (d.tasks || []);
      const el = document.getElementById('stat-tasks');
      if (el) el.textContent = tasks.length;
    }
  } catch {}
  try {
    const r = await fetch('/flags?type=risk&status=active');
    if (r.ok) {
      const risks = await r.json();
      const count = Array.isArray(risks) ? risks.length : 0;
      const el = document.getElementById('stat-risks');
      if (el) el.textContent = count;
      const wrap = document.getElementById('stat-risks-wrap');
      if (wrap) wrap.style.color = count > 0 ? 'var(--red)' : '';
    }
  } catch {}
}

/* ─── TOAST ─────────────────────────────────────────── */
function showToast(type, text, color) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  const now = new Date();
  const msk = new Date(now.getTime() + (now.getTimezoneOffset() + 180) * 60000);
  const time = msk.toLocaleTimeString('ru-RU', {hour:'2-digit',minute:'2-digit'}) + ' МСК';
  toast.innerHTML = `
    <div class="toast-type" style="color:${color||'var(--text-dim)'}">${escHtml(type)}</div>
    <div class="toast-text">${escHtml(text)}</div>
    <div class="toast-time">${time}</div>
  `;
  toast.onclick = () => toast.remove();
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 8000);
}

/* ─── AGENT PANEL ────────────────────────────────────── */
const STATUS_COLORS = {
  live:    '#10b981',
  pause:   '#f59e0b',
  ready:   '#3b82f6',
  pending: '#f97316',
  ghost:   '#6b7280',
};
const STATUS_LABELS = {
  live: 'LIVE', pause: 'ПАУЗА', ready: 'ГОТОВ', pending: 'СТРОИТСЯ', ghost: 'НЕ СОЗДАН',
};
const ROOM_NAMES = {
  hq:'ШТАБ HQ', lib:'БИБЛИОТЕКА', anlt:'АНАЛИТИКА', tech:'ТЕХНИК',
  babla:'ОТДЕЛ БАБЛА', ideyny:'ИДЕЙНЫЙ', proekt:'ПРОЕКТНЫЙ', prod:'ПРОИЗВОДСТВО',
  build:'СТРОИТЕЛЬСТВО', audit:'АУДИТ',
};

let _currentAgent = null;

function openAgentPanel(agent) {
  _currentAgent = agent;
  const panel = document.getElementById('agent-panel');
  if (!panel) return;

  document.getElementById('ap-emoji').textContent  = agent.emoji || '🤖';
  document.getElementById('ap-name').textContent   = agent.name  || 'Агент';
  document.getElementById('ap-desc').textContent   = agent.desc  || '—';

  const color = STATUS_COLORS[agent.status] || '#6b7280';
  const label = STATUS_LABELS[agent.status] || agent.status?.toUpperCase() || '—';
  document.getElementById('ap-status-dot').style.background = color;
  document.getElementById('ap-status-dot').style.boxShadow  = `0 0 6px ${color}`;
  document.getElementById('ap-status-label').textContent    = label;
  document.getElementById('ap-status-label').style.color    = color;
  document.getElementById('ap-room').textContent = agent.room ? ('· ' + (ROOM_NAMES[agent.room] || agent.room)) : '';

  const triggerBtn = document.getElementById('ap-trigger-btn');
  if (triggerBtn) triggerBtn.textContent = agent.status === 'live' ? '⏸ Остановить' : '▶ Запустить';

  document.getElementById('ap-tasks').innerHTML  = '<div class="ap-desc" style="color:var(--text-dim)">Загрузка...</div>';
  document.getElementById('ap-events').innerHTML = '<div class="ap-desc" style="color:var(--text-dim)">Загрузка...</div>';

  panel.classList.add('open');

  loadAgentTasks(agent);
  loadAgentEvents(agent);
}

function closeAgentPanel() {
  const panel = document.getElementById('agent-panel');
  if (panel) panel.classList.remove('open');
  _currentAgent = null;
}

async function loadAgentTasks(agent) {
  const el = document.getElementById('ap-tasks');
  if (!el) return;
  try {
    const r = await fetch(`/tech/tasks?limit=5`);
    if (!r.ok) throw new Error();
    const tasks = await r.json();
    const list = (Array.isArray(tasks) ? tasks : (tasks.tasks || []))
      .filter(t => t.description?.toLowerCase().includes(agent.name.toLowerCase()) ||
                   t.title?.toLowerCase().includes(agent.name.toLowerCase()))
      .slice(0, 3);
    if (!list.length) {
      el.innerHTML = '<div class="ap-desc" style="color:var(--text-dim)">Задач нет</div>';
      return;
    }
    const STATUS_IC = {pending:'⏳',running:'⚙️',done:'✅',failed:'❌',waiting_approval:'🔔'};
    el.innerHTML = list.map(t => `
      <div class="ap-task-row">
        <div class="ap-task-title">${STATUS_IC[t.status]||'•'} ${escHtml(t.title)}</div>
        <div class="ap-task-meta">${t.status} · ${t.created_at ? timeAgo(t.created_at) : ''}</div>
      </div>
    `).join('');
  } catch {
    el.innerHTML = '<div class="ap-desc" style="color:var(--text-dim)">Нет данных</div>';
  }
}

async function loadAgentEvents(agent) {
  const el = document.getElementById('ap-events');
  if (!el) return;
  try {
    const branch = agent.db || agent.id;
    const r = await fetch(`/events?branch=${encodeURIComponent(branch)}&limit=5`);
    if (!r.ok) throw new Error();
    const d = await r.json();
    const events = (d.events || d || []).slice(0, 4);
    if (!events.length) {
      el.innerHTML = '<div class="ap-desc" style="color:var(--text-dim)">Событий нет</div>';
      return;
    }
    el.innerHTML = events.map(ev => {
      const payload = ev.payload || {};
      const text = payload.summary || payload.name || payload.task || ev.type;
      return `
        <div class="ap-event-row">
          <div class="ap-event-type" style="color:var(--text-dim)">${escHtml(ev.type)}</div>
          <div class="ap-event-text">${escHtml(String(text).slice(0,120))}</div>
          ${ev.created_at ? `<div class="ap-event-time">${timeAgo(ev.created_at)}</div>` : ''}
        </div>
      `;
    }).join('');
  } catch {
    el.innerHTML = '<div class="ap-desc" style="color:var(--text-dim)">Нет данных</div>';
  }
}

async function apCreateTask() {
  if (!_currentAgent) return;
  const title = prompt(`Задача для Техника по агенту ${_currentAgent.name}:`);
  if (!title) return;
  try {
    await fetch('/tech/tasks', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({title, description:`Агент: ${_currentAgent.name}`, created_by:'hq_panel', priority:5}),
    });
    showToast('ТЕХНИК', `Задача создана: ${title}`, '#f59e0b');
    loadAgentTasks(_currentAgent);
  } catch {}
}

async function apTrigger() {
  if (!_currentAgent) return;
  showToast('ДЕЙСТВИЕ', `Команда агенту ${_currentAgent.name} отправлена`, '#3b82f6');
}

/* ─── postMessage FROM MAP ───────────────────────────── */
window.addEventListener('message', e => {
  if (e.data?.type === 'wyrd-agent-click') {
    openAgentPanel(e.data.agent);
  }
});

/* ─── WS TOASTS ─────────────────────────────────────── */
function initWSToasts() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data);
      if (data.type === 'ping') return;
      const payload = data.payload || {};
      const text = payload.summary || payload.name || payload.task || data.type;
      const COLORS = {
        agent_born:'#a855f7', analytics_report:'#f97316',
        babla_report:'#10b981', idea_report:'#8b5cf6',
        agent_passport_issued:'#3b82f6',
      };
      showToast((data.branch||'EVENT').toUpperCase(), String(text).slice(0,100), COLORS[data.type]||'var(--text-dim)');
      loadTopbarStats();
    } catch {}
  };
  ws.onclose = () => setTimeout(initWSToasts, 4000);
}

/* ─── INIT ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('starfield');
  if (canvas) initStars(canvas);

  startClock();
  initMap();
  initWSToasts();
  loadTopbarStats();

  setInterval(loadTopbarStats, 30000);
});
