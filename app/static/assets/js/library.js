/* ── Библиотека Room v3 ──────────────────────────────────── */

let _libReaders = [];
let _libSearchTimer = null;
let _libRecentItems = [];
let _libSearchItems = [];
let _libExpandedId = null;
let _libExpandedSearchId = null;

function loadLibrary() { loadLibraryRoom(); }

async function loadLibraryRoom() {
  await Promise.all([loadLibStats(), loadLibReaders(), loadLibRecent()]);
}

// ── Статистика / Категории ──────────────────────────────

async function loadLibStats() {
  const grid = document.getElementById('lib-cats-grid');
  const meta = document.getElementById('lib-knowledge-meta');
  if (!grid) return;
  try {
    const r = await fetch('/library/stats');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    const total = d.total || 0;
    const cats = d.by_category || [];
    const max = cats.reduce((m, c) => Math.max(m, c.count), 1);

    _libUpdateChip('lib-total-chip', `${total} знаний`);
    _libUpdateChip('lib-cats-chip', `${cats.length} категорий`);

    grid.innerHTML = cats.map(c => {
      const pct = Math.round((c.count / max) * 100);
      return `<div class="lib-cat-row">
        <span class="lib-cat-name">${_eH(c.category)}</span>
        <div class="lib-cat-bar-track"><div class="lib-cat-bar-fill" style="width:${pct}%"></div></div>
        <span class="lib-cat-count">${c.count}</span>
      </div>`;
    }).join('') || '<div class="lib-empty">Нет данных</div>';

    if (meta) {
      const synth = d.syntheses_count != null ? `Синтезов: ${d.syntheses_count}` : '';
      const janitor = d.janitor_last_run ? `Мусорщик: ${_libAgo(d.janitor_last_run)}` : '';
      meta.innerHTML = [synth, janitor].filter(Boolean).map(t =>
        `<span>${t}</span>`
      ).join('');
    }
  } catch {
    grid.innerHTML = '<div class="lib-empty">Статистика недоступна</div>';
  }
}

// ── Читатели ─────────────────────────────────────────────

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
    _libUpdateChip('lib-rdrs-chip', `${_libReaders.length} читателей`);
    _renderReaders(_libReaders);
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}

function _renderReaders(readers) {
  const el = document.getElementById('lib-readers-list');
  if (!el) return;
  if (!readers.length) {
    el.innerHTML = '<div class="lib-empty">Читателей нет</div>';
    return;
  }
  el.innerHTML = readers.map(r => {
    const topics = (r.topics || []).slice(0, 3).join(', ');
    const extra = r.topics?.length > 3 ? ` +${r.topics.length - 3}` : '';
    const lastRun = r.last_run ? _libAgo(r.last_run) : 'никогда';
    const dotClass = r.enabled ? 'status-dot alive' : 'status-dot paused';
    return `<div class="lib-reader-row">
      <span class="${dotClass}" style="flex-shrink:0"></span>
      <div class="lib-reader-info">
        <div class="lib-reader-name">${_eH(r.name)}</div>
        <div class="lib-reader-topics">${_eH(topics)}${extra}</div>
      </div>
      <div class="lib-reader-meta">
        <span class="badge blue">${_eH(r.category)}</span>
        <span class="lib-reader-run">${lastRun}</span>
      </div>
    </div>`;
  }).join('');
}

function libReadersFilter(val) {
  const q = val.trim().toLowerCase();
  const filtered = q
    ? _libReaders.filter(r =>
        r.name.toLowerCase().includes(q) ||
        (r.topics || []).some(t => t.toLowerCase().includes(q))
      )
    : _libReaders;
  _renderReaders(filtered);
}

async function libRunAll(btn) {
  btn.disabled = true;
  btn.textContent = '⏳';
  try {
    const r = await fetch('/library/readers/run-all', { method: 'POST' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    btn.textContent = '✅';
    setTimeout(() => { btn.textContent = '▶ Запустить всех'; btn.disabled = false; }, 3000);
    if (typeof showToast === 'function') showToast('Читатели запущены', 'success');
  } catch (e) {
    btn.textContent = '❌';
    if (typeof showToast === 'function') showToast(`Ошибка: ${e.message}`, 'error');
    setTimeout(() => { btn.textContent = '▶ Запустить всех'; btn.disabled = false; }, 3000);
  }
}

// ── Поток знаний ─────────────────────────────────────────

async function loadLibRecent() {
  const el = document.getElementById('lib-recent-list');
  if (!el) return;
  el.innerHTML = '<div class="lib-empty">Загрузка...</div>';
  try {
    const r = await fetch('/library/recent?limit=20');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    _libRecentItems = d.items || [];
    _renderRecent(_libRecentItems);
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}

function _renderRecent(items) {
  const el = document.getElementById('lib-recent-list');
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<div class="lib-empty">Знаний пока нет</div>';
    return;
  }
  el.innerHTML = items.map((item, idx) => {
    const isOpen = _libExpandedId === idx;
    const arrow = isOpen ? '▾' : '▸';
    const answerHtml = isOpen && item.answer
      ? `<div class="lib-k-answer-full">${_eH(item.answer)}</div>` : '';
    return `<div class="lib-knowledge-row lib-k-clickable" onclick="libToggleItem(${idx})">
      <div class="lib-k-header">
        <span class="lib-k-arrow">${arrow}</span>
        <span class="lib-k-question">${_eH(item.question || '')}</span>
      </div>
      ${answerHtml}
      <div class="lib-k-meta">
        <span class="badge blue">${_eH(item.category || '')}</span>
        <span class="lib-k-src">${_eH(item.source || '')}</span>
        <span class="lib-k-ttl">${item.expires_at ? item.expires_at.slice(0, 10) : 'static'}</span>
        <span class="lib-k-hits">🔁 ${item.request_count || 0}</span>
      </div>
    </div>`;
  }).join('');
}

async function libToggleItem(idx) {
  if (_libExpandedId === idx) { _libExpandedId = null; _renderRecent(_libRecentItems); return; }
  _libExpandedId = idx;
  const item = _libRecentItems[idx];
  if (item && !item.answer && item.id) {
    try {
      const r = await fetch(`/library/knowledge/${item.id}`);
      if (r.ok) { const d = await r.json(); item.answer = d.answer || '(нет текста)'; }
    } catch { item.answer = '(ошибка загрузки)'; }
  }
  _renderRecent(_libRecentItems);
}

// ── Поиск ────────────────────────────────────────────────

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
  if (!q?.trim()) return;
  const el = document.getElementById('lib-search-results');
  if (!el) return;
  el.innerHTML = '<div class="lib-empty">Ищу...</div>';
  try {
    const r = await fetch(`/library/search?q=${encodeURIComponent(q)}&limit=10`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    _libSearchItems = d.results || [];
    _libExpandedSearchId = null;
    _renderSearchResults(_libSearchItems);
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}

function _renderSearchResults(results) {
  const el = document.getElementById('lib-search-results');
  if (!el) return;
  if (!results.length) { el.innerHTML = '<div class="lib-empty">Ничего не найдено</div>'; return; }
  el.innerHTML = results.map((item, idx) => {
    const score = item.score ? ` ${(item.score * 100).toFixed(0)}%` : '';
    const isOpen = _libExpandedSearchId === idx;
    const arrow = isOpen ? '▾' : '▸';
    const answerHtml = isOpen && item.answer
      ? `<div class="lib-k-answer-full">${_eH(item.answer)}</div>` : '';
    return `<div class="lib-knowledge-row lib-k-clickable" onclick="libToggleSearch(${idx})">
      <div class="lib-k-header">
        <span class="lib-k-arrow">${arrow}</span>
        <span class="lib-k-question">${_eH(item.question || item.text || '')}</span>
        ${score ? `<span class="lib-k-score">${score}</span>` : ''}
      </div>
      ${answerHtml}
      <div class="lib-k-meta">
        <span class="badge blue">${_eH(item.category || '')}</span>
        <span class="lib-k-src">${_eH(item.source || '')}</span>
      </div>
    </div>`;
  }).join('');
}

async function libToggleSearch(idx) {
  if (_libExpandedSearchId === idx) { _libExpandedSearchId = null; _renderSearchResults(_libSearchItems); return; }
  _libExpandedSearchId = idx;
  const item = _libSearchItems[idx];
  if (item && !item.answer && item.id) {
    try {
      const r = await fetch(`/library/knowledge/${item.id}`);
      if (r.ok) { const d = await r.json(); item.answer = d.answer || '(нет текста)'; }
    } catch { item.answer = '(ошибка загрузки)'; }
  }
  _renderSearchResults(_libSearchItems);
}

// ── Helpers ──────────────────────────────────────────────

function _libAgo(iso) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}с назад`;
  if (diff < 3600) return `${Math.floor(diff / 60)}м назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}ч назад`;
  return `${Math.floor(diff / 86400)}д назад`;
}

function _eH(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function _libUpdateChip(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}
