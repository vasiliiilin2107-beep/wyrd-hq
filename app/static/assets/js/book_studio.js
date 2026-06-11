/* WYRD Book Studio v9 — ядро: состояние, fetch, действия, хелперы.
   Рендер (галерея + страница книги): book_studio_gallery.js */

let _bsSlug = null, _bsBookTab = 'chapters', _bsFilter = 'all';
let _bsStats = null, _bsBooks = [], _bsChapters = [], _bsArc = null;
let _bsConductor = null, _bsPanels = null, _bsIdeas = null, _bsMetrics = null;
const _BS_GOOD = 7.5, _BS_OK = 6.5;
const _FN_COL = {открытие:'#60a5fa',конфликт:'var(--status-dead)',поворот:'var(--color-agents)',пик:'var(--color-studio)',развязка:'var(--status-alive)',setup:'#60a5fa'};

async function _bsFetch(p) {
  const r = await fetch(p, {signal: AbortSignal.timeout(12000)});
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function _bsPost(p, payload, timeoutMs) {
  const opts = {method:'POST', signal: AbortSignal.timeout(timeoutMs || 30000)};
  if (payload) { opts.headers = {'Content-Type':'application/json'}; opts.body = JSON.stringify(payload); }
  const r = await fetch(p, opts);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Роутер: галерея ↔ страница книги ──────────────────────────
async function loadBookStudio() {
  const sEl = document.getElementById('bs-stats');
  if (sEl && !_bsStats) sEl.innerHTML = _bsSkeleton(4);
  try {
    _bsStats = await _bsFetch('/bs/stats');
    _bsBooks = _bsStats.books || [];
    if (!_bsSlug) {
      if (!_bsIdeas) _bsIdeas = await _bsFetch('/bs/analyst/ideas').catch(() => null);
      bsRenderGallery();
      return;
    }
    const [chs, arc] = await Promise.all([
      _bsFetch(`/bs/books/${_bsSlug}/chapters`),
      _bsFetch(`/bs/books/${_bsSlug}/arc`).catch(() => null)
    ]);
    _bsChapters = chs;
    _bsArc = arc;
    bsRenderBookPage();
    if (_bsBookTab === 'team') _loadTeamData();
  } catch (e) {
    const bEl = document.getElementById('bs-book-body');
    if (sEl) sEl.innerHTML = '';
    if (bEl) bEl.innerHTML = `<div class="bs-error">⚠ ${e.message} <button class="wyrd-btn wyrd-btn-sm" style="margin-left:8px" onclick="loadBookStudio()">↺</button></div>`;
  }
}

async function _loadTeamData() {
  const [cond, panels, ideas] = await Promise.allSettled([
    _bsFetch(`/bs/books/${_bsSlug}/conductor`).catch(() => null),
    _bsFetch(`/bs/books/${_bsSlug}/panels`).catch(() => null),
    _bsFetch('/bs/analyst/ideas').catch(() => null),
  ]);
  _bsConductor = cond.value;
  _bsPanels = panels.value;
  _bsIdeas = ideas.value;
  bsRenderBookPage();
}

function _bsIdeasList() {
  return Array.isArray(_bsIdeas) ? _bsIdeas : (_bsIdeas?.ideas || []);
}

// ── Создание книги из идеи Аналитика ──────────────────────────
async function bsCreateBook(i) {
  const idea = _bsIdeasList()[i];
  if (!idea) return;
  const title = idea.title || idea.idea || 'Без названия';
  const slug = _bsSlugify(title);
  if (!confirm(`Создать книгу «${title}»?\nslug: ${slug}`)) return;
  try {
    const lore = [idea.hook || idea.description || '', idea.why_it_works || ''].filter(Boolean).join('\n\n');
    await _bsPost('/bs/books', {slug, title, genre: idea.genre || 'xianxia_comedy', lore});
    showToast(`✅ «${title}» создана`);
    _bsSlug = slug;
    if (confirm('Запустить подготовку: Story Bible + 10 арок × 20 глав? (~3-5 мин)')) bsPrepareBook(slug);
    loadBookStudio();
  } catch (e) { showToast('❌ ' + e.message); }
}

async function bsPrepareBook(slug) {
  const s = slug || _bsSlug;
  try {
    const d = await _bsPost(`/bs/studio/prepare/${s}`);
    showToast(d.ok ? '📐 Подготовка пошла: Bible + 10 арок (~3-5 мин)' : '❌ ' + (d.detail || 'Ошибка'));
  } catch (e) { showToast('❌ ' + e.message); }
}

// ── Действия ──────────────────────────────────────────────────
async function bsGenerate(slug) {
  const s = slug || _bsSlug;
  try {
    const d = await _bsPost(`/bs/books/${s}/generate`, {book_slug: s, target_words: 2000}, 60000);
    showToast(d.ok ? `✅ Глава ${d.queued_chapter} в очереди` : '❌ Ошибка');
    if (d.ok) setTimeout(() => loadBookStudio(), 4000);
  } catch (e) { showToast('❌ ' + e.message); }
}

async function bsPublish(slug, num) {
  if (!confirm(`Опубликовать главу ${num} на Rulate?`)) return;
  try {
    const d = await _bsPost(`/bs/books/${slug}/publish/${num}`, null, 60000);
    showToast(d.ok ? `✅ Глава ${num} на Rulate` : '❌ Ошибка');
    document.getElementById('bs-ch-ov')?.remove();
    if (d.ok) setTimeout(() => loadBookStudio(), 2000);
  } catch (e) { showToast('❌ ' + e.message); }
}

async function bsPublishAll(slug) {
  const s = slug || _bsSlug, toPublish = _bsChapters.filter(c => !c.published && (c.score||0) >= _BS_OK).sort((a,b) => a.number-b.number);
  if (!toPublish.length) { showToast('Нет глав для публикации'); return; }
  if (!confirm(`Опубликовать ${toPublish.length} глав?`)) return;
  let ok = 0, err = 0;
  for (const c of toPublish) {
    try { const d = await _bsPost(`/bs/books/${s}/publish/${c.number}`, null, 60000); if (d.ok) ok++; else err++; }
    catch { err++; }
    await new Promise(res => setTimeout(res, 600));
  }
  showToast(`✅ ${ok}${err ? ' | ❌ ' + err : ''}`);
  loadBookStudio();
}

async function bsLoadArc(n) {
  try {
    _bsArc = await _bsFetch(`/bs/books/${_bsSlug}/arc?arc=${n}`);
    bsRenderBookPage();
  } catch (e) { showToast('❌ ' + e.message); }
}

async function bsLoadMetrics(slug) {
  showToast('Загружаю метрики...');
  try { _bsMetrics = await _bsFetch(`/bs/books/${slug}/rulate_metrics`); bsRenderBookPage(); }
  catch (e) { showToast('Ошибка: ' + e.message); }
}

async function bsRunConductor(slug) {
  showToast('Дирижёр анализирует... (~30 сек)');
  try {
    _bsConductor = await _bsPost(`/bs/books/${slug}/conductor`, null, 90000);
    bsRenderBookPage(); showToast('✅ Директивы готовы');
  } catch (e) { showToast('❌ ' + e.message); }
}

async function bsRunScout() {
  showToast('Разведка запущена...');
  try {
    await fetch('/bs/scout/all', {method:'POST', signal: AbortSignal.timeout(90000)}).catch(() => {});
    _bsIdeas = await _bsFetch('/bs/analyst/ideas').catch(() => null);
    bsRenderBookPage(); showToast('✅ Разведка завершена');
  } catch (e) { showToast('Разведка: ' + e.message); }
}

// ── Просмотр главы (оверлей) ──────────────────────────────────
async function openBsChapter(slug, num) {
  let ov = document.getElementById('bs-ch-ov');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'bs-ch-ov';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:8000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
    ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = `<div style="color:var(--text-secondary)">Загрузка...</div>`;
  try {
    const ch = await _bsFetch(`/bs/books/${slug}/chapters/${num}`);
    const sc = ch.score || 0;
    const pubBtn = !ch.published ? `<div style="padding:12px 20px;border-top:1px solid var(--border-dim)">
      <button class="wyrd-btn wyrd-btn-sm" onclick="bsPublish('${slug}',${ch.number})">📤 Опубликовать на Rulate</button></div>` : '';
    ov.innerHTML = `<div style="width:min(740px,96vw);max-height:90vh;background:var(--bg-base);border:1px solid var(--border-base);border-radius:var(--r-xl);display:flex;flex-direction:column;box-shadow:var(--shadow-md)">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border-dim)">
        <div>
          <div class="stat-card-label" style="margin-bottom:4px">ГЛАВА ${ch.number}</div>
          <div style="font-size:.95rem;font-weight:700">${ch.title}</div>
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <div style="text-align:center">
            <div style="font-size:1.4rem;font-weight:900;color:${_scoreColor(sc)}">${sc.toFixed(1)}</div>
            <div class="stat-card-label">ОЦЕНКА</div>
          </div>
          <div style="font-size:.7rem;color:${ch.published ? 'var(--status-alive)' : 'var(--text-secondary)'}">${ch.published ? '✅ Rulate' : '⬜ черн.'}</div>
          <button onclick="document.getElementById('bs-ch-ov').remove()"
            style="background:none;border:1px solid var(--border-base);color:var(--text-secondary);border-radius:var(--r-md);padding:5px 12px;cursor:pointer">✕</button>
        </div>
      </div>
      <div style="overflow-y:auto;padding:20px 24px;font-size:.85rem;line-height:2;white-space:pre-wrap">${ch.content || ''}</div>
      ${pubBtn}
    </div>`;
  } catch (e) { ov.innerHTML = `<div style="color:var(--status-dead);padding:20px">${e.message}</div>`; }
}

// ── Хелперы ───────────────────────────────────────────────────
const _BS_TR = {а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'zh',з:'z',и:'i',й:'y',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'h',ц:'ts',ч:'ch',ш:'sh',щ:'sch',ъ:'',ы:'y',ь:'',э:'e',ю:'yu',я:'ya'};
function _bsSlugify(t) {
  return (t||'').toLowerCase().split('').map(c => _BS_TR[c] !== undefined ? _BS_TR[c] : c).join('')
    .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 30) || 'book';
}
function _scoreColor(s) { return s >= _BS_GOOD ? 'var(--status-alive)' : s >= _BS_OK ? 'var(--color-studio)' : 'var(--status-dead)'; }
function _scoreTrend(s) { if (s.length < 3) return '—'; const d = s[s.length-1] - s[s.length-3]; return d > 0.3 ? '↑' : d < -0.3 ? '↓' : '→'; }
function _scoreBar(s) {
  const col = _scoreColor(s), pct = Math.min(100, Math.round(s*10));
  return `<div style="flex:1;background:var(--bg-raised);border-radius:var(--r-full);height:6px;max-width:120px">
    <div style="width:${pct}%;height:100%;background:${col};border-radius:var(--r-full);box-shadow:0 0 6px ${col}88"></div></div>`;
}
function _sparkline(scores) {
  if (scores.length < 2) return '';
  const W = 60, H = 20, pad = 2, min = Math.min(...scores), max = Math.max(...scores), range = max-min || 1;
  const pts = scores.map((s,i) => { const x = pad+(i/(scores.length-1))*(W-pad*2), y = H-pad-((s-min)/range)*(H-pad*2); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(' ');
  const last = scores[scores.length-1], col = _scoreColor(last), [lx,ly] = pts.split(' ').pop().split(',');
  return `<svg width="${W}" height="${H}" style="opacity:.7;vertical-align:middle"><polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${lx}" cy="${ly}" r="2.5" fill="${col}"/></svg>`;
}
function _bsSkeleton(n) {
  return `<div style="display:grid;grid-template-columns:repeat(${n},1fr);gap:10px">${Array.from({length:n}, () => `<div class="ds-skeleton" style="height:72px;border-radius:var(--r-md)"></div>`).join('')}</div>`;
}

setInterval(loadBookStudio, 60000);
