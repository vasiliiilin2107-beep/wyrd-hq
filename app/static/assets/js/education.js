/* education.js — вкладка 👔 Профобразование Совета */

const EDU_AGENTS = [
  { id: 'strategist', name: 'Стратег', icon: '🧭', file: 'council_strategist', color: '#f59e0b' },
  { id: 'architect',  name: 'Архитектор', icon: '🏗️', file: 'council_architect',  color: '#3b82f6' },
  { id: 'cartographer', name: 'Картограф', icon: '🗺️', file: 'council_cartographer', color: '#10b981' },
];

let _eduReaders = [];
let _eduScores = {};

async function loadEducation() {
  await Promise.all([_loadEduReaders(), _loadEduScores()]);
  _renderEduAgents();
}

async function _loadEduReaders() {
  try {
    const r = await fetch('/library/readers');
    if (!r.ok) return;
    const data = await r.json();
    const readers = data.readers || data;
    _eduReaders = readers.filter(x => x.category === 'council');
    _renderEduReaders();
  } catch (e) {
    document.getElementById('edu-readers-list').innerHTML =
      '<div style="color:var(--text-dim);font-size:.65rem">Ошибка загрузки читателей</div>';
  }
}

async function _loadEduScores() {
  try {
    const r = await fetch('/education/scores');
    if (!r.ok) return;
    _eduScores = await r.json();
    document.getElementById('edu-factory-status').textContent =
      `| последний цикл: ${_eduScores.last_cycle || '—'}`;
  } catch (_) {}
}

function _renderEduAgents() {
  const el = document.getElementById('edu-agents-list');
  if (!el) return;

  el.innerHTML = EDU_AGENTS.map(a => {
    const s = _eduScores[a.file] || {};
    const score = s.best_score ?? '—';
    const ts = s.timestamp ? new Date(s.timestamp).toLocaleTimeString('ru', {hour:'2-digit',minute:'2-digit'}) : '—';
    const cycle = s.cycle ?? '—';
    const pct = typeof score === 'number' ? score : 0;
    const barColor = pct >= 95 ? '#10b981' : pct >= 85 ? '#f59e0b' : '#ef4444';
    const scoreLabel = pct >= 95 ? '🔥' : pct >= 85 ? '✓' : '↑';

    return `<div class="civ-agent-card" style="border-left:3px solid ${a.color}">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:1.2rem">${a.icon}</span>
        <div>
          <div style="font-size:.7rem;font-weight:700;letter-spacing:.1em">${a.name}</div>
          <div style="font-size:.55rem;color:var(--text-dim)">цикл ${cycle} | ${ts}</div>
        </div>
        <div style="margin-left:auto;display:flex;align-items:center;gap:8px">
          <button onclick="showPrompt('${a.id}')" style="font-size:.55rem;background:rgba(255,255,255,.07);border:1px solid var(--border);border-radius:6px;padding:2px 8px;cursor:pointer;color:var(--text-dim)">📋 Промпт</button>
          <span style="font-size:.8rem;font-weight:700;color:${barColor}">${scoreLabel} ${score}/100</span>
        </div>
      </div>
      <div style="background:rgba(0,0,0,.3);border-radius:4px;height:5px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${barColor};border-radius:4px;transition:width .4s"></div>
      </div>
    </div>`;
  }).join('');
}

function _renderEduReaders() {
  const el = document.getElementById('edu-readers-list');
  const cnt = document.getElementById('edu-readers-count');
  if (!el) return;
  if (cnt) cnt.textContent = `(${_eduReaders.length})`;

  if (!_eduReaders.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem">Читатели не найдены</div>';
    return;
  }

  el.innerHTML = _eduReaders.map(r => {
    const lastRun = r.last_run
      ? new Date(r.last_run).toLocaleString('ru', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})
      : 'не запускался';
    const dot = r.enabled ? '#10b981' : '#6b7280';
    const topics = (r.topics || []).slice(0, 2).map(t =>
      `<span style="font-size:.55rem;background:rgba(255,255,255,.06);border:1px solid var(--border);border-radius:6px;padding:2px 7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px;display:inline-block">${t.slice(0,55)}</span>`
    ).join('');

    return `<div class="civ-agent-card" style="margin-bottom:6px">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="width:7px;height:7px;border-radius:50%;background:${dot};flex-shrink:0"></span>
        <span style="font-size:.68rem;font-weight:600">${r.name}</span>
        <span style="font-size:.55rem;color:var(--text-dim);margin-left:auto">каждые ${r.interval_hours}ч | прогонов: ${r.runs}</span>
      </div>
      <div style="font-size:.55rem;color:var(--text-dim);margin:4px 0 6px 15px">последний: ${lastRun}</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;margin-left:15px">${topics}</div>
    </div>`;
  }).join('');
}

let _cachedPrompts = null;

async function showPrompt(agentId) {
  if (!_cachedPrompts) {
    try {
      const r = await fetch('/council/prompts');
      _cachedPrompts = await r.json();
    } catch(e) {
      alert('Ошибка загрузки промпта'); return;
    }
  }
  const data = _cachedPrompts[agentId];
  if (!data) { alert('Промпт не найден: ' + agentId); return; }
  _showEduModal(`${data.icon} Промпт: ${data.name}`, data.prompt);
}

function _showEduModal(title, text) {
  let m = document.getElementById('edu-prompt-modal');
  if (!m) {
    m = document.createElement('div');
    m.id = 'edu-prompt-modal';
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow-y:auto';
    m.addEventListener('click', function(e){ if(e.target===m) m.remove(); });
    document.body.appendChild(m);
  }
  m.innerHTML = `<div style="background:#1e293b;border:1px solid rgba(255,255,255,.12);border-radius:12px;width:100%;max-width:700px;padding:20px;margin:auto;position:relative">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div style="font-size:.8rem;font-weight:700;color:#f8fafc">${title}</div>
      <button onclick="document.getElementById('edu-prompt-modal').remove()" style="background:none;border:none;color:#94a3b8;cursor:pointer;font-size:1.3rem;line-height:1">✕</button>
    </div>
    <pre style="font-size:.6rem;line-height:1.8;color:#e2e8f0;white-space:pre-wrap;max-height:70vh;overflow-y:auto;font-family:monospace;margin:0">${text.replace(/</g,'&lt;')}</pre>
  </div>`;
}

async function applyCouncilPrompts() {
  if (!confirm('Применить промпты из фабрики к агентам Совета? Это создаст задачу Технику.')) return;
  try {
    const r = await fetch('/tech/tasks', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        title: 'Применить промпты Совета из фабрики',
        description: 'Прочитать /tmp/council_strategist.json, /tmp/council_architect.json, /tmp/council_cartographer.json из контейнера wyrd-technik. Вставить поля "prompt" из каждого файла в SYS_STRATEGIST, SYS_ARCHITECT, SYS_CARTOGRAPHER в /app/council_agent.py контейнера wyrd-hq. Сделать git commit и push.',
        priority: 8,
      })
    });
    if (r.ok) {
      alert('Задача создана Технику ✓');
    } else {
      alert('Ошибка: ' + r.status);
    }
  } catch (e) {
    alert('Ошибка: ' + e.message);
  }
}
