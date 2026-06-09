/* Бабло — комната доходов */
const Babla = (() => {
  let _loaded = false;

  async function load() {
    _loaded = true;
    const [repRes, ideasRes, expRes] = await Promise.allSettled([
      fetch('/babla/reports/latest'),
      fetch('/income/ideas'),
      fetch('/income/experiments'),
    ]);

    _renderReport(repRes.status === 'fulfilled' ? await repRes.value.json() : null);
    _renderIdeas(ideasRes.status === 'fulfilled' ? await ideasRes.value.json() : null);
    _renderExperiments(expRes.status === 'fulfilled' ? await expRes.value.json() : null);
  }

  function _renderReport(data) {
    const el = document.getElementById('babla-report');
    if (!el) return;
    const rep = data?.report;
    if (!rep) {
      el.innerHTML = '<div class="babla-empty">Отчётов ещё нет — нажмите ▶ Запустить</div>';
      return;
    }
    const analysis = rep.analysis || {};
    const ts = new Date(rep.checked_at).toLocaleString('ru-RU', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' });
    const rows = [
      { icon: '🔍', name: 'Охотник', key: 'hunter' },
      { icon: '🧮', name: 'Счетовод', key: 'accountant' },
      { icon: '🎯', name: 'Приоритизатор', key: 'prioritizer' },
    ];
    el.innerHTML = `
      <div class="babla-report-hdr">
        <span class="babla-report-ts">${ts}</span>
        <button class="btn-primary" style="padding:4px 12px;font-size:.68rem" onclick="Babla.run(this)">▶ Запустить</button>
      </div>
      ${rows.map(r => {
        const text = typeof analysis === 'string' ? analysis : (analysis[r.key] || analysis.summary || JSON.stringify(analysis));
        return `<div class="babla-agent-row">
          <span class="babla-agent-icon">${r.icon}</span>
          <div class="babla-agent-body">
            <div class="babla-agent-name">${r.name}</div>
            <div class="babla-agent-text">${_e(typeof text === 'string' ? text.slice(0, 400) : JSON.stringify(text).slice(0, 400))}</div>
          </div>
        </div>`;
      }).join('')}
    `;
  }

  let _ideasFilter = 'all';
  let _allIdeas = [];

  function _renderIdeas(data) {
    _allIdeas = data?.ideas || [];
    _applyIdeasFilter();
    const total = _allIdeas.length;
    const el = document.getElementById('babla-ideas-count');
    if (el) el.textContent = total ? `${total}` : '';
  }

  function _applyIdeasFilter() {
    const el = document.getElementById('babla-ideas-list');
    if (!el) return;
    const filtered = _ideasFilter === 'all' ? _allIdeas : _allIdeas.filter(i => i.status === _ideasFilter);
    if (!filtered.length) {
      el.innerHTML = '<div class="babla-empty">Нет идей в этой категории</div>';
      return;
    }
    el.innerHTML = filtered.map(i => `
      <div class="babla-idea-card ${_statusClass(i.status)}">
        <div class="babla-idea-hdr">
          <span class="babla-idea-title">${_e(i.title)}</span>
          <span class="babla-idea-status">${_statusLabel(i.status)}</span>
        </div>
        ${i.description ? `<div class="babla-idea-desc">${_e(i.description.slice(0, 200))}</div>` : ''}
        ${i.expected_revenue ? `<div class="babla-idea-rev">💰 ${_e(i.expected_revenue)}</div>` : ''}
      </div>
    `).join('');
  }

  function filterIdeas(btn, status) {
    document.querySelectorAll('.babla-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    _ideasFilter = status;
    _applyIdeasFilter();
  }

  function _renderExperiments(data) {
    const all = data?.experiments || [];
    const groups = { testing: [], done: [], failed: [], other: [] };
    all.forEach(e => {
      const g = groups[e.status] ? e.status : 'other';
      groups[g].push(e);
    });

    const render = (id, items) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (!items.length) { el.innerHTML = '<div class="babla-exp-empty">—</div>'; return; }
      el.innerHTML = items.map(e => `
        <div class="babla-exp-card">
          <div class="babla-exp-title">${_e(e.title)}</div>
          ${e.hypothesis ? `<div class="babla-exp-hyp">${_e(e.hypothesis.slice(0,150))}</div>` : ''}
          ${e.result ? `<div class="babla-exp-result">→ ${_e(e.result.slice(0,150))}</div>` : ''}
        </div>
      `).join('');
    };

    render('babla-exp-testing', groups.testing);
    render('babla-exp-done', groups.done);
    render('babla-exp-failed', groups.failed);

    const totalEl = document.getElementById('babla-exp-count');
    if (totalEl) totalEl.textContent = all.length ? `${all.length}` : '';
  }

  async function run(btn) {
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Запускаю...'; }
    try {
      await fetch('/babla/run', { method: 'POST' });
      if (btn) { btn.textContent = '✅ Запущен'; setTimeout(() => { btn.textContent = '▶ Запустить'; btn.disabled = false; }, 3000); }
    } catch {
      if (btn) { btn.textContent = '❌ Ошибка'; btn.disabled = false; }
    }
  }

  function _statusClass(s) {
    return { idea: 'status-idea', testing: 'status-testing', done: 'status-done', archived: 'status-archived' }[s] || '';
  }

  function _statusLabel(s) {
    return { idea: '💡 Новая', testing: '🔬 В работе', done: '✅ Готово', archived: '📦 Архив' }[s] || s || '—';
  }

  function _e(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  return { load, run, filterIdeas };
})();
