/* world.js v2 — вкладка 🌍 Мир */

const World = (() => {
  function _e(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function _timeAgo(iso) {
    const diff = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (diff < 60)  return diff + 'с';
    if (diff < 3600) return Math.floor(diff/60) + 'м';
    if (diff < 86400) return Math.floor(diff/3600) + 'ч';
    return Math.floor(diff/86400) + 'д';
  }

  function _renderServices(services) {
    const el = document.getElementById('world-services-grid');
    if (!el) return;
    if (!services.length) { el.innerHTML = '<div class="world-empty">Нет данных</div>'; return; }

    const statusColor = { online: 'var(--status-alive)', error: 'var(--status-dead)', offline: 'var(--status-dead)' };
    const statusLabel = { online: 'online', error: 'ошибка', offline: 'offline' };

    el.innerHTML = services.map(s => `
      <div class="world-svc-card">
        <span class="status-dot" style="background:${statusColor[s.status] || 'var(--status-paused)'}"></span>
        <span class="world-svc-name">${_e(s.name)}</span>
        <span class="world-svc-status ${s.status === 'online' ? 'text-alive' : 'text-dead'}">${statusLabel[s.status] || s.status}</span>
        <span class="world-svc-ms">${s.ms}мс</span>
      </div>
    `).join('') + `
      <div class="world-svc-card world-svc-pause">
        <span class="status-dot" style="background:var(--status-paused)"></span>
        <span class="world-svc-name">Нейроцех</span>
        <span class="world-svc-status" style="color:var(--status-paused)">пауза</span>
        <span class="world-svc-ms">~июль</span>
      </div>`;
  }

  function _renderBrief(events) {
    const el = document.getElementById('world-brief-list');
    if (!el) return;
    if (!events.length) { el.innerHTML = '<div class="world-empty">Нет событий</div>'; return; }
    el.innerHTML = events.map(ev => `
      <div class="world-brief-row">
        <span class="world-brief-agent">${_e(ev.agent)}</span>
        <span class="world-brief-type badge">${_e(ev.type)}</span>
        <span class="world-brief-text">${_e(ev.summary || '—')}</span>
        <span class="world-brief-time">${_timeAgo(ev.time)}</span>
      </div>
    `).join('');
  }

  function _renderAnalytics(report) {
    const el = document.getElementById('world-analytics-block');
    if (!el) return;
    if (!report) { el.innerHTML = '<div class="world-empty">Отчёт не найден — запусти аналитику</div>'; return; }

    const date = new Date(report.checked_at).toLocaleDateString('ru', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
    const analysis = report.analysis || '';

    const sections = { observation: '', conclusion: '', proposal: '' };
    const lines = analysis.split('\n');
    let cur = '';
    for (const line of lines) {
      const l = line.toLowerCase();
      if (l.includes('наблюден') || l.includes('observation')) { cur = 'observation'; continue; }
      if (l.includes('вывод') || l.includes('conclusion'))     { cur = 'conclusion';  continue; }
      if (l.includes('предложен') || l.includes('proposal'))   { cur = 'proposal';    continue; }
      if (cur && line.trim()) sections[cur] += line.trim() + ' ';
    }
    if (!sections.observation && !sections.conclusion && !sections.proposal) {
      sections.observation = analysis.slice(0, 300);
    }

    el.innerHTML = `
      <div class="world-analytics-date">Отчёт от ${_e(date)}</div>
      ${sections.observation ? `<div class="world-analytics-section"><span class="world-analytics-label">НАБЛЮДЕНИЕ</span><p>${_e(sections.observation)}</p></div>` : ''}
      ${sections.conclusion  ? `<div class="world-analytics-section"><span class="world-analytics-label">ВЫВОД</span><p>${_e(sections.conclusion)}</p></div>` : ''}
      ${sections.proposal    ? `<div class="world-analytics-section"><span class="world-analytics-label">ПРЕДЛОЖЕНИЕ</span><p>${_e(sections.proposal)}</p></div>` : ''}
    `;
  }

  function _renderDispatchers() {
    const el = document.getElementById('world-dispatchers');
    if (!el) return;
    const items = [
      { name: 'Book Studio',   desc: 'Диспетчер книг',       status: 'future' },
      { name: 'HQ',            desc: 'Диспетчер штаба',      status: 'future' },
      { name: 'Библиотека',    desc: 'Диспетчер знаний',     status: 'future' },
      { name: 'Нейроцех',      desc: 'Диспетчер контента',   status: 'future' },
    ];
    el.innerHTML = items.map(d => `
      <div class="world-disp-card">
        <span class="status-dot" style="background:var(--status-paused)"></span>
        <div>
          <div class="world-disp-name">${_e(d.name)}</div>
          <div class="world-disp-desc">${_e(d.desc)}</div>
        </div>
        <span class="badge" style="margin-left:auto;color:var(--text-muted)">план</span>
      </div>
    `).join('');
  }

  async function load() {
    const svcEl = document.getElementById('world-services-grid');
    const briefEl = document.getElementById('world-brief-list');
    const analytEl = document.getElementById('world-analytics-block');
    if (svcEl)   svcEl.innerHTML   = '<div class="world-empty">Пингую сервисы...</div>';
    if (briefEl) briefEl.innerHTML = '<div class="world-empty">Загрузка...</div>';
    if (analytEl) analytEl.innerHTML = '<div class="world-empty">Загрузка...</div>';

    _renderDispatchers();

    const [health, brief, analytics] = await Promise.allSettled([
      fetch('/hq-world/health').then(r => r.json()),
      fetch('/hq-world/brief').then(r => r.json()),
      fetch('/analytics/reports/latest').then(r => r.json()),
    ]);

    _renderServices(health.status === 'fulfilled' ? (health.value.services || []) : []);
    _renderBrief(brief.status === 'fulfilled' ? (brief.value.events || []) : []);
    _renderAnalytics(analytics.status === 'fulfilled' ? (analytics.value.report || null) : null);
  }

  async function runAnalytics(btn) {
    if (btn) { btn.disabled = true; btn.textContent = '...'; }
    try {
      await fetch('/analytics/run', { method: 'POST' });
      setTimeout(() => load(), 3000);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '▶ Запустить'; }
    }
  }

  return { load, runAnalytics };
})();

function loadWorld() { World.load(); }
function worldRunAnalytics(btn) { World.runAnalytics(btn); }

// Совместимость с паспортами — старые функции-заглушки
function selectWorldDept() {}
function selectWorldAgent() {}
function showWorldModal() {}
