/* WYRD HQ — Home Dashboard */

let _homeTimer = null;

async function loadHome() {
  renderHomeDate();
  await Promise.all([loadHomeStats(), loadHomeFeed(), loadHomeBsMini(), loadHomeAgentsMini()]);
}

function renderHomeDate() {
  const el = document.getElementById('home-date');
  if (!el) return;
  const now = new Date();
  const msk = new Date(now.getTime() + (now.getTimezoneOffset() + 180) * 60000);
  el.textContent = msk.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' });
}

async function loadHomeStats() {
  const el = document.getElementById('home-stats');
  if (!el) return;

  el.innerHTML = [
    { id: 'hs-live',  val: '—', label: 'LIVE АГЕНТОВ',  color: '#10b981' },
    { id: 'hs-tasks', val: '—', label: 'ЗАДАЧ В РАБОТЕ', color: '#3b82f6' },
    { id: 'hs-lib',   val: '—', label: 'ЗАПИСЕЙ В БИБ.', color: '#f59e0b' },
    { id: 'hs-risks', val: '0', label: 'РИСКОВ',          color: '#ef4444' },
  ].map(s => `
    <div class="home-stat-card" style="--stat-color:${s.color}">
      <div class="home-stat-val" id="${s.id}">${s.val}</div>
      <div class="home-stat-label">${s.label}</div>
    </div>
  `).join('');

  try {
    const r = await fetch('/civilization/agents');
    if (r.ok) {
      const d = await r.json();
      const now = Date.now();
      const live = (d.agents || []).filter(a => {
        if (!a.last_pulse) return false;
        return now - new Date(a.last_pulse.endsWith('Z') ? a.last_pulse : a.last_pulse + 'Z').getTime() < 1200000;
      }).length;
      const e = document.getElementById('hs-live');
      if (e) e.textContent = live;
    }
  } catch {}

  try {
    const r = await fetch('/tech/tasks?status=running&limit=50');
    if (r.ok) {
      const d = await r.json();
      const e = document.getElementById('hs-tasks');
      if (e) e.textContent = (Array.isArray(d) ? d : (d.tasks || [])).length;
    }
  } catch {}

  try {
    const r = await fetch('/library/readers');
    if (r.ok) {
      const d = await r.json();
      const total = (d.readers || d || []).reduce((s, x) => s + (x.total_records || 0), 0);
      const e = document.getElementById('hs-lib');
      if (e && total > 0) e.textContent = total + '+';
    }
  } catch {}

  try {
    const r = await fetch('/flags?type=risk&status=active');
    if (r.ok) {
      const risks = await r.json();
      const count = Array.isArray(risks) ? risks.length : 0;
      const e = document.getElementById('hs-risks');
      if (e) { e.textContent = count; e.style.color = count > 0 ? 'var(--red)' : ''; }
    }
  } catch {}
}

async function loadHomeFeed() {
  const el = document.getElementById('home-feed');
  if (!el) return;
  const items = [];

  try {
    const r = await fetch('/tech/tasks?limit=8');
    if (r.ok) {
      const tasks = await r.json();
      const IC = { pending:'⏳', running:'⚙️', done:'✅', failed:'❌', waiting_approval:'🔔' };
      const CL = { pending:'#f59e0b', running:'#3b82f6', done:'#10b981', failed:'#ef4444', waiting_approval:'#8b5cf6' };
      (Array.isArray(tasks) ? tasks : []).slice(0, 5).forEach(t => {
        items.push({ icon: IC[t.status] || '🔧', label: 'ТЕХНИК', color: CL[t.status] || '#6b7280', text: t.title, time: t.updated_at || t.created_at });
      });
    }
  } catch {}

  try {
    const r = await fetch('/events?limit=15');
    if (r.ok) {
      const d = await r.json();
      const EVT = {
        agent_born:            { ic:'🐣', col:'#a855f7', lbl:'АГЕНТ' },
        analytics_report:      { ic:'📊', col:'#f97316', lbl:'АНАЛИТИКА' },
        babla_report:          { ic:'💰', col:'#10b981', lbl:'БАБЛО' },
        idea_report:           { ic:'💡', col:'#cc44ff', lbl:'ИДЕЯ' },
        agent_passport_issued: { ic:'🎫', col:'#3b82f6', lbl:'ПАСПОРТ' },
        proposal_submitted:    { ic:'📝', col:'#f59e0b', lbl:'ПРЕДЛОЖЕНИЕ' },
      };
      (d.events || d || []).slice(0, 6).forEach(ev => {
        const cfg = EVT[ev.type]; if (!cfg) return;
        const p = ev.payload || {};
        items.push({ icon: cfg.ic, label: cfg.lbl, color: cfg.col, text: String(p.name || p.summary || p.agent || ev.type), time: ev.created_at });
      });
    }
  } catch {}

  items.sort((a, b) => {
    if (!a.time && !b.time) return 0;
    if (!a.time) return 1; if (!b.time) return -1;
    return new Date(b.time) - new Date(a.time);
  });

  if (!items.length) { el.innerHTML = '<div style="color:var(--text-dim);font-size:.75rem">Активности нет</div>'; return; }

  el.innerHTML = items.slice(0, 12).map(it => `
    <div class="home-feed-item">
      <div class="home-feed-item-icon">${it.icon}</div>
      <div class="home-feed-item-body">
        <div class="home-feed-item-label" style="color:${it.color}">${escHtml(it.label)}</div>
        <div class="home-feed-item-text">${escHtml(it.text)}</div>
      </div>
      ${it.time ? `<div class="home-feed-item-time">${timeAgo(it.time)}</div>` : ''}
    </div>
  `).join('');
}

async function loadHomeBsMini() {
  const el = document.getElementById('home-bs-mini');
  if (!el) return;
  try {
    const d = await fetch('/bs/stats').then(r => { if (!r.ok) throw new Error(); return r.json(); });
    const books = d.books || [];
    if (!books.length) { el.innerHTML = '<div style="color:var(--text-dim)">Нет книг</div>'; return; }
    const b = books[0];
    el.innerHTML = `
      <div style="font-size:.85rem;font-weight:600;margin-bottom:5px">${escHtml(b.title || '—')}</div>
      <div style="font-size:.72rem;color:var(--text-dim)">
        Глав: <b style="color:var(--text)">${b.chapter_count || '—'}</b>
        · Score: <b style="color:var(--gold)">${b.avg_score ? b.avg_score.toFixed(1) : '—'}</b>
      </div>
    `;
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.72rem">Нет данных</div>';
  }
}

async function loadHomeAgentsMini() {
  const el = document.getElementById('home-agents-mini');
  if (!el) return;
  try {
    const d = await fetch('/civilization/agents').then(r => { if (!r.ok) throw new Error(); return r.json(); });
    const agents = d.agents || [];
    const now = Date.now();
    const live = agents.filter(a => {
      if (!a.last_pulse) return false;
      return now - new Date(a.last_pulse.endsWith('Z') ? a.last_pulse : a.last_pulse + 'Z').getTime() < 1200000;
    });
    el.innerHTML = `
      <div style="margin-bottom:8px;font-size:.72rem;color:var(--text-dim)">
        <span style="color:var(--green);font-weight:700">${live.length}</span> live
        · <span>${agents.length - live.length}</span> offline
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center">
        ${live.slice(0, 10).map(a => `<span title="${escHtml(a.name || '')}" style="font-size:1.1rem;cursor:default">${a.emoji || '🤖'}</span>`).join('')}
        ${live.length > 10 ? `<span style="font-size:.7rem;color:var(--text-dim)">+${live.length - 10}</span>` : ''}
      </div>
    `;
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.72rem">Нет данных</div>';
  }
}

function startHomeUpdates() {
  if (_homeTimer) clearInterval(_homeTimer);
  _homeTimer = setInterval(loadHome, 30000);
}

function stopHomeUpdates() {
  if (_homeTimer) { clearInterval(_homeTimer); _homeTimer = null; }
}
