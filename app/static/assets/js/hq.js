/* ─── STARFIELD ─────────────────────────────────────── */
function initStars(canvas) {
  const ctx = canvas.getContext('2d');
  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    drawStars(ctx, canvas.width, canvas.height);
  }
  window.addEventListener('resize', resize);
  resize();
}
function drawStars(ctx, w, h) {
  ctx.clearRect(0, 0, w, h);
  for (let i = 0; i < Math.floor((w * h) / 4000); i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const r = Math.random() * 1.2 + 0.2;
    const a = Math.random() * 0.5 + 0.1;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,${a})`;
    ctx.fill();
  }
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
          label: k.category || 'library',
          text:  k.question,
          time:  null,
        });
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

/* ─── INIT ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('starfield');
  if (canvas) initStars(canvas);

  startClock();
  loadBranches();
  loadEvents();
  initMap();
  initWS();

  setInterval(() => loadEvents(), 60000);
  setInterval(() => loadBranches(), 30000);
});
