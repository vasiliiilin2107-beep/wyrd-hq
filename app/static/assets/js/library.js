/* ── Вкладка 📚 Библиотека ─────────────────────────────── */

let _libReaders = [];
let _libSearchTimer = null;
let _libRecentItems = [];
let _libSearchItems = [];
let _libExpandedId = null;
let _libExpandedSearchId = null;

async function loadLibrary() {
  await Promise.all([loadLibStats(), loadLibReaders(), loadLibRecent()]);
}

// ── Статистика ──────────────────────────────────────────

async function loadLibStats() {
  const el = document.getElementById('lib-stats');
  if (!el) return;
  try {
    const r = await fetch('/library/stats');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    el.innerHTML = `
      <div class="lib-stat-box">
        <div class="lib-stat-num">${d.total || 0}</div>
        <div class="lib-stat-label">знаний</div>
      </div>
      ${(d.by_category || []).slice(0, 4).map(c =>
        `<div class="lib-stat-box">
          <div class="lib-stat-num">${c.count}</div>
          <div class="lib-stat-label">${c.category}</div>
        </div>`
      ).join('')}`;
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Статистика недоступна</div>`;
  }
}

// ── Читатели ────────────────────────────────────────────

async function loadLibReaders() {
  const el = document.getElementById('lib-readers-list');
  if (!el) return;
  el.innerHTML = '<div class="lib-empty">Загрузка...</div>';
  try {
    const r = await fetch('/library/readers');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    _libReaders = d.readers || [];
    const cnt = document.getElementById('lib-readers-count');
    if (cnt) cnt.textContent = `(${_libReaders.length})`;
    renderReaders(_libReaders);
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}

function renderReaders(readers) {
  const el = document.getElementById('lib-readers-list');
  if (!el) return;
  if (!readers.length) {
    el.innerHTML = '<div class="lib-empty">Читателей пока нет</div>';
    return;
  }
  el.innerHTML = readers.map(r => {
    const topics = (r.topics || []).slice(0, 3).join(', ');
    const extra = (r.topics || []).length > 3 ? ` +${r.topics.length - 3}` : '';
    const lastRun = r.last_run ? _ago(r.last_run) : 'никогда';
    const dot = r.enabled ? 'lib-dot-on' : 'lib-dot-off';
    return `<div class="lib-reader-row">
      <span class="lib-dot ${dot}"></span>
      <div class="lib-reader-info">
        <div class="lib-reader-name">${escLibHtml(r.name)}</div>
        <div class="lib-reader-topics">${escLibHtml(topics)}${extra}</div>
      </div>
      <div class="lib-reader-meta">
        <span class="lib-badge">${r.category}</span>
        <span class="lib-reader-run">каждые ${r.interval_hours}ч</span>
        <span class="lib-reader-run">${lastRun}</span>
      </div>
    </div>`;
  }).join('');
}

function libReadersFilter(val) {
  const q = val.trim().toLowerCase();
  const filtered = q
    ? _libReaders.filter(r => r.name.toLowerCase().includes(q) || (r.topics || []).some(t => t.toLowerCase().includes(q)))
    : _libReaders;
  renderReaders(filtered);
}

// ── Последние знания ────────────────────────────────────

async function loadLibRecent() {
  const el = document.getElementById('lib-recent-list');
  if (!el) return;
  el.innerHTML = '<div class="lib-empty">Загрузка...</div>';
  try {
    const r = await fetch('/library/recent?limit=20');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    _libRecentItems = d.items || [];
    renderRecent(_libRecentItems);
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}

function renderRecent(items) {
  const el = document.getElementById('lib-recent-list');
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<div class="lib-empty">Знаний пока нет</div>';
    return;
  }
  el.innerHTML = items.map((item, idx) => {
    const exp = item.expires_at ? `до ${item.expires_at.slice(0, 10)}` : 'static';
    const isOpen = _libExpandedId === idx;
    const answerHtml = isOpen && item.answer
      ? `<div class="lib-k-answer-full">${escLibHtml(item.answer)}</div>` : '';
    const arrow = isOpen ? '▾' : '▸';
    return `<div class="lib-knowledge-row lib-k-clickable" onclick="libToggleItem(${idx})">
      <div class="lib-k-header">
        <span class="lib-k-arrow">${arrow}</span>
        <span class="lib-k-question">${escLibHtml(item.question || '')}</span>
      </div>
      ${answerHtml}
      <div class="lib-k-meta">
        <span class="lib-badge">${item.category}</span>
        <span class="lib-badge lib-badge-ns">${item.namespace || 'public'}</span>
        <span class="lib-k-src">${escLibHtml(item.source || '')}</span>
        <span class="lib-k-ttl">${exp}</span>
        <span class="lib-k-hits">🔁 ${item.request_count || 0}</span>
      </div>
    </div>`;
  }).join('');
}

async function libToggleItem(idx) {
  if (_libExpandedId === idx) {
    _libExpandedId = null;
    renderRecent(_libRecentItems);
    return;
  }
  _libExpandedId = idx;
  const item = _libRecentItems[idx];
  if (item && !item.answer && item.id) {
    try {
      const r = await fetch(`/library/knowledge/${item.id}`);
      if (r.ok) {
        const d = await r.json();
        item.answer = d.answer || '(нет текста)';
      }
    } catch { item.answer = '(ошибка загрузки)'; }
  }
  renderRecent(_libRecentItems);
}

// ── Поиск ───────────────────────────────────────────────

function libSearchInput(val) {
  clearTimeout(_libSearchTimer);
  if (val.trim().length < 2) {
    const el = document.getElementById('lib-search-results');
    if (el) el.innerHTML = '';
    return;
  }
  _libSearchTimer = setTimeout(() => runLibSearch(val.trim()), 400);
}

async function runLibSearch(q) {
  const el = document.getElementById('lib-search-results');
  if (!el) return;
  el.innerHTML = '<div class="lib-empty">Ищу...</div>';
  try {
    const r = await fetch(`/library/search?q=${encodeURIComponent(q)}&limit=10`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    _libSearchItems = d.results || [];
    _libExpandedSearchId = null;
    renderSearchResults(_libSearchItems);
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}

function renderSearchResults(results) {
  const el = document.getElementById('lib-search-results');
  if (!el) return;
  if (!results.length) {
    el.innerHTML = '<div class="lib-empty">Ничего не найдено</div>';
    return;
  }
  el.innerHTML = results.map((item, idx) => {
    const score = item.score ? ` ${(item.score * 100).toFixed(0)}%` : '';
    const isOpen = _libExpandedSearchId === idx;
    const arrow = isOpen ? '▾' : '▸';
    const answerHtml = isOpen && item.answer
      ? `<div class="lib-k-answer-full">${escLibHtml(item.answer)}</div>` : '';
    return `<div class="lib-knowledge-row lib-search-row lib-k-clickable" onclick="libToggleSearch(${idx})">
      <div class="lib-k-header">
        <span class="lib-k-arrow">${arrow}</span>
        <span class="lib-k-question">${escLibHtml(item.question || item.text || '')}</span>
        ${score ? `<span class="lib-k-score">${score}</span>` : ''}
      </div>
      ${answerHtml}
      <div class="lib-k-meta">
        <span class="lib-badge">${item.category || ''}</span>
        <span class="lib-k-src">${escLibHtml(item.source || '')}</span>
      </div>
    </div>`;
  }).join('');
}

async function libToggleSearch(idx) {
  if (_libExpandedSearchId === idx) {
    _libExpandedSearchId = null;
    renderSearchResults(_libSearchItems);
    return;
  }
  _libExpandedSearchId = idx;
  const item = _libSearchItems[idx];
  if (item && !item.answer && item.id) {
    try {
      const r = await fetch(`/library/knowledge/${item.id}`);
      if (r.ok) {
        const d = await r.json();
        item.answer = d.answer || '(нет текста)';
      }
    } catch { item.answer = '(ошибка загрузки)'; }
  }
  renderSearchResults(_libSearchItems);
}

// ── Helpers ─────────────────────────────────────────────

function _ago(iso) {
  const d = new Date(iso);
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diff < 60) return `${diff}с назад`;
  if (diff < 3600) return `${Math.floor(diff / 60)}м назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}ч назад`;
  return `${Math.floor(diff / 86400)}д назад`;
}

function escLibHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
