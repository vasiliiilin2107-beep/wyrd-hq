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

/* ─── EVENTS ────────────────────────────────────────── */
let lastEventId = null;

async function loadEvents(initial = false) {
  const feed = document.getElementById('event-feed');
  if (!feed) return;
  try {
    const res  = await fetch('/events?limit=30');
    const data = await res.json();
    const list = Array.isArray(data) ? data : data.events || [];
    if (initial) {
      feed.innerHTML = '';
      if (!list.length) {
        feed.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem;padding:12px 0">Событий пока нет</div>';
        return;
      }
      list.slice().reverse().forEach(e => appendEvent(feed, e, false));
      if (list.length) lastEventId = list[0].id;
    } else {
      const newEvents = list.filter(e => !lastEventId || e.id > lastEventId);
      if (newEvents.length) {
        lastEventId = newEvents[0].id;
        newEvents.slice().reverse().forEach(e => appendEvent(feed, e, true));
        while (feed.children.length > 50) feed.removeChild(feed.lastChild);
      }
    }
  } catch { /* silent */ }
}

function appendEvent(feed, e, prepend) {
  const type = e.type || 'info';
  const branch = e.branch_name || e.branch || '—';
  const payload = e.payload ? JSON.stringify(e.payload).slice(0, 120) : '';
  const time = e.created_at ? new Date(e.created_at).toLocaleTimeString('ru-RU', { hour12: false }) : '';

  const item = document.createElement('div');
  item.className = 'feed-item';
  item.innerHTML = `
    <div class="feed-type type-${type.replace(/\./g,'_').replace(/-/g,'_')}">${type.toUpperCase()}</div>
    <div class="feed-branch">${branch}</div>
    ${payload ? `<div class="feed-payload">${payload}</div>` : ''}
    <div class="feed-time">${time}</div>
  `;
  if (prepend) feed.insertBefore(item, feed.firstChild);
  else feed.appendChild(item);
}

/* ─── WEBSOCKET ─────────────────────────────────────── */
function initWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data);
      if (data.type === 'ping') return;
      const feed = document.getElementById('event-feed');
      if (feed) appendEvent(feed, data, true);
    } catch { /* ignore */ }
  };
  ws.onclose = () => setTimeout(initWS, 3000);
}

/* ─── HELPERS ───────────────────────────────────────── */
function timeAgo(isoStr) {
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
  if (diff < 60)    return 'только что';
  if (diff < 3600)  return `${Math.floor(diff/60)} мин назад`;
  if (diff < 86400) return `${Math.floor(diff/3600)} ч назад`;
  return `${Math.floor(diff/86400)} д назад`;
}

/* ─── INIT ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('starfield');
  if (canvas) initStars(canvas);

  startClock();
  loadBranches();
  loadEvents(true);
  initWS();

  // Поллинг как резерв
  setInterval(() => loadEvents(false), 8000);
  setInterval(() => loadBranches(), 30000);
});
