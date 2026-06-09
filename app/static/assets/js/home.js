/* WYRD HQ — Home Dashboard v2 */

let _homeTimer = null;
let _homeClockTimer = null;

async function loadHome() {
  _renderClock();
  const [agRes, evRes, bsRes, coRes] = await Promise.allSettled([
    fetch('/civilization/agents').then(r => r.ok ? r.json() : null),
    fetch('/events?limit=20').then(r => r.ok ? r.json() : null),
    fetch('/bs/stats').then(r => r.ok ? r.json() : null),
    fetch('/council/sessions?limit=1').then(r => r.ok ? r.json() : null),
  ]);

  const agents  = agRes.value?.agents || [];
  const events  = Array.isArray(evRes.value) ? evRes.value : (evRes.value?.events || []);
  const bsStats = bsRes.value || null;
  const council = coRes.value || null;

  _renderPulseStats(agents, bsStats);
  _renderAgentGrid(agents);
  _renderEventsBlock(events, council);
  _renderProduction(bsStats);
}

function _renderClock() {
  const el = document.getElementById('home-clock');
  if (!el) return;
  const now = new Date();
  const msk = new Date(now.getTime() + (now.getTimezoneOffset() + 180) * 60000);
  el.textContent = msk.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) + ' МСК';
}

function _agentAge(a) {
  if (!a.last_pulse) return Infinity;
  const ts = a.last_pulse.endsWith('Z') ? a.last_pulse : a.last_pulse + 'Z';
  return Date.now() - new Date(ts).getTime();
}

function _agentColor(age) {
  if (age < 1200000) return 'var(--status-alive)';
  if (age < 3600000) return 'var(--status-idle)';
  return 'var(--status-dead)';
}

function _renderPulseStats(agents, bsStats) {
  const liveCount = agents.filter(a => _agentAge(a) < 1200000).length;
  const el = document.getElementById('home-pulse-meta');
  if (!el) return;

  let chapStr = '—';
  if (bsStats?.books?.length) {
    const total = bsStats.books.reduce((s, b) => s + (b.chapter_count || 0), 0);
    chapStr = total + ' глав';
  }

  el.innerHTML = `
    <span class="hp-chip"><span style="color:var(--status-alive)">●</span> ${liveCount} агентов</span>
    <span class="hp-chip">📚 ${chapStr}</span>
  `;

  const sb = document.getElementById('sb-badge-live');
  if (sb) sb.textContent = liveCount;
}

function _renderAgentGrid(agents) {
  const el = document.getElementById('home-agent-grid');
  const countEl = document.getElementById('home-agents-count');
  if (!el) return;

  if (!agents.length) {
    el.innerHTML = '<span style="color:var(--text-secondary);font-size:.75rem">Нет агентов</span>';
    return;
  }

  const liveCount = agents.filter(a => _agentAge(a) < 1200000).length;
  if (countEl) countEl.textContent = liveCount + '/' + agents.length + ' live';

  el.innerHTML = agents.map(a => {
    const age   = _agentAge(a);
    const color = _agentColor(age);
    const name  = escHtml(a.name || a.id || '?');
    const role  = escHtml(a.role || '');
    const task  = escHtml(a.current_task || a.description || '');
    const tip   = name + (role ? ' · ' + role : '') + (task ? '\n' + task : '');
    const cls   = age < 1200000 ? 'agent-dot alive' : (age < 3600000 ? 'agent-dot idle' : 'agent-dot dead');
    return `<span class="${cls}" style="background:${color}" title="${tip}"></span>`;
  }).join('');
}

function _renderEventsBlock(events, council) {
  const el = document.getElementById('home-events-block');
  if (!el) return;

  const SHOW_TYPES = ['analytics_report','babla_report','idea_report','agent_born',
    'council_verdict','book_chapter_scored','book_chapter_published','proposal_submitted'];
  const ICONS = {
    analytics_report:'📊', babla_report:'💰', idea_report:'💡', agent_born:'🐣',
    council_verdict:'🧠', book_chapter_scored:'📖', book_chapter_published:'📤', proposal_submitted:'📝',
  };

  const filtered = events.filter(e => SHOW_TYPES.includes(e.type)).slice(0, 4);
  const evHTML = filtered.length
    ? filtered.map(e => {
        const p = e.payload || {};
        const text = p.summary || p.name || p.agent || e.type;
        return `<div class="home-ev-row">
          <span class="home-ev-icon">${ICONS[e.type] || '•'}</span>
          <span class="home-ev-text">${escHtml(String(text))}</span>
          <span class="home-ev-time">${e.created_at ? timeAgo(e.created_at) : ''}</span>
        </div>`;
      }).join('')
    : '<div class="home-ev-empty">Активности нет</div>';

  let councilHTML = '';
  if (council?.sessions?.length) {
    const s = council.sessions[0];
    const idea = s.idea || '';
    if (idea) {
      councilHTML = `<div class="home-council-block">
        <div class="home-section-label">СОВЕТ</div>
        <div class="home-council-text">${escHtml(idea.slice(0, 100))}${idea.length > 100 ? '…' : ''}</div>
      </div>`;
    }
  }

  el.innerHTML = evHTML + councilHTML;
}

function _renderProduction(bsStats) {
  const el = document.getElementById('home-production');
  if (!el) return;

  if (!bsStats?.books?.length) {
    el.innerHTML = '<div class="home-ev-empty">Нет данных</div>';
    return;
  }

  const booksHTML = bsStats.books.map(b => {
    const score  = b.avg_score ? b.avg_score.toFixed(1) : '—';
    const pct    = Math.min(100, ((b.avg_score || 0) / 10) * 100);
    const pipe   = b.pipeline_enabled !== false
      ? '<span style="color:var(--status-alive)">▶ живёт</span>'
      : '<span style="color:var(--status-paused)">⏸ пауза</span>';
    return `<div class="home-book-card">
      <div class="home-book-title">${escHtml(b.title || '—')}</div>
      <div class="home-book-nums">
        <span class="ds-mono" style="color:var(--text-primary)">${b.chapter_count || 0}</span>
        <span class="home-book-label">гл</span>
        <span class="ds-mono" style="color:var(--gold-bright)">${score}</span>
        <span class="home-book-label">avg</span>
        <span class="home-book-label" style="margin-left:auto">${pipe}</span>
      </div>
      <div class="home-score-track"><div class="home-score-fill" style="width:${pct}%"></div></div>
      ${b.rulate_count ? `<div class="home-book-sub">${b.rulate_count} на Rulate</div>` : ''}
    </div>`;
  }).join('');

  el.innerHTML = booksHTML + `
    <div class="home-neiro-row">
      <span>🎬 Нейроцех</span>
      <span style="color:var(--status-paused)">● пауза ~6 июля</span>
    </div>`;
}

async function _homeRunAction(btn, fn) {
  const orig = btn.textContent;
  btn.textContent = '⏳'; btn.disabled = true;
  try {
    await fn();
    btn.textContent = '✅';
  } catch {
    btn.textContent = '❌';
  }
  setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 3000);
}

function homeRunScout(btn) {
  _homeRunAction(btn, () =>
    fetch('/bs/books/tolstyak/scout/all', { method: 'POST' }).then(r => { if (!r.ok) throw 0; })
  );
}

function homeRunConductor(btn) {
  _homeRunAction(btn, () =>
    fetch('/bs/books/tolstyak/conductor', { method: 'POST' }).then(r => { if (!r.ok) throw 0; })
  );
}

function startHomeUpdates() {
  if (_homeTimer)      clearInterval(_homeTimer);
  if (_homeClockTimer) clearInterval(_homeClockTimer);
  _homeTimer      = setInterval(loadHome, 60000);
  _homeClockTimer = setInterval(_renderClock, 30000);
}

function stopHomeUpdates() {
  if (_homeTimer)      { clearInterval(_homeTimer);      _homeTimer = null; }
  if (_homeClockTimer) { clearInterval(_homeClockTimer); _homeClockTimer = null; }
}
