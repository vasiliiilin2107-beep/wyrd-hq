/* WYRD Book Studio v3 — Рабочий стол книги */

let _bsSlug = null, _bsBookTab = 'chapters', _bsFilter = 'all';
let _bsChapters = [], _bsArc = null, _bsScout = null;
const _BS_GOOD = 7.5, _BS_OK = 6.5;
const _FN_COL = {открытие:'#60a5fa',конфликт:'var(--red)',поворот:'var(--purple)',пик:'var(--amber)',развязка:'var(--green)',setup:'#60a5fa'};

async function _bsFetch(p) {
  const r = await fetch(p);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Main ─────────────────────────────────────────────────────
async function loadBookStudio() {
  const sEl = document.getElementById('bs-stats');
  if (sEl) sEl.innerHTML = '<div style="color:var(--text-dim);font-size:.8rem">Загрузка...</div>';
  try {
    const d = await _bsFetch('/bs/stats');
    _renderBsStats(d);
    const books = d.books || [];
    if (!books.length) return;
    if (!_bsSlug) _bsSlug = books[0].slug;
    if (d.scout) _bsScout = d.scout;
    const [chs, arc] = await Promise.all([
      _bsFetch(`/bs/books/${_bsSlug}/chapters`),
      _bsFetch(`/bs/books/${_bsSlug}/arc`).catch(() => null)
    ]);
    _bsChapters = chs;
    _bsArc = arc;
    _renderBookBody();
    if (_bsBookTab === 'plan' && _bsScout) _renderBsScout(_bsScout);
  } catch (e) {
    if (sEl) sEl.innerHTML = `<div style="color:var(--red);font-size:.8rem">Ошибка: ${e.message}</div>`;
  }
}

// ── Stats + book selector ─────────────────────────────────────
function _renderBsStats(d) {
  const books = d.books || [];
  const avg = books.length ? (books.reduce((s,b) => s+(b.avg_score||0), 0)/books.length).toFixed(1) : '—';
  const sEl = document.getElementById('bs-stats');
  if (sEl) sEl.innerHTML =
    _bsCard(d.total_chapters||0,'НАПИСАНО','var(--amber)','✍️') +
    _bsCard(d.total_published||0,'НА RULATE','var(--green)','📤') +
    _bsCard(books.length,'КНИГ','var(--purple)','📚') +
    _bsCard(avg,'СР. ОЦЕНКА',_scoreColor(parseFloat(avg)||0),'⭐');
  const tEl = document.getElementById('bs-book-tabs');
  if (tEl) tEl.innerHTML = books.map(b =>
    `<button class="wyrd-btn wyrd-btn-sm${_bsSlug===b.slug?'':' wyrd-btn-ghost'}" onclick="bsSelectBook('${b.slug}')">
      ${b.title.length>22?b.title.slice(0,22)+'…':b.title}
      <span style="color:var(--amber);margin-left:4px">${b.avg_score||'?'}</span>
      ${b.rulate_url?`<a href="${b.rulate_url}" target="_blank" onclick="event.stopPropagation()" style="margin-left:4px;color:var(--text-dim)">↗</a>`:''}
    </button>`).join('');
}

function _bsCard(v, label, color, icon) {
  return `<div style="background:var(--card);border:1px solid var(--border);border-top:3px solid ${color};border-radius:10px;padding:16px 18px;position:relative;overflow:hidden">
    <div style="font-size:2rem;font-weight:900;color:${color};letter-spacing:-1px;line-height:1">${v}</div>
    <div style="font-size:.65rem;color:var(--text-dim);margin-top:5px;letter-spacing:.1em">${label}</div>
    <div style="position:absolute;right:12px;top:12px;font-size:1.4rem;opacity:.15">${icon}</div>
  </div>`;
}

function bsSelectBook(slug) { _bsSlug = slug; _bsBookTab = 'chapters'; loadBookStudio(); }

// ── 3-Tab container ───────────────────────────────────────────
function _renderBookBody() {
  const el = document.getElementById('bs-book-body');
  if (!el) return;
  const nav = [['plan','📋 ПЛАН'],['chapters','✍️ ГЛАВЫ'],['control','🔍 КОНТРОЛЬ']].map(([t,lbl]) =>
    `<button onclick="bsBookTab('${t}')" style="padding:7px 20px;border-radius:7px;border:none;cursor:pointer;font-size:.78rem;font-weight:700;transition:all .15s;
      background:${_bsBookTab===t?'var(--amber)':'rgba(255,255,255,.07)'};
      color:${_bsBookTab===t?'#0d1117':'var(--text-dim)'}">${lbl}</button>`
  ).join('');
  const content = _bsBookTab==='plan' ? _buildPlanTab()
    : _bsBookTab==='chapters' ? _buildChaptersTab()
    : _buildControlTab();
  el.innerHTML = `<div style="display:flex;gap:6px;margin-bottom:16px">${nav}</div>${content}`;
}

function bsBookTab(t) {
  _bsBookTab = t;
  _renderBookBody();
  if (t==='plan' && _bsScout) _renderBsScout(_bsScout);
}

// ── ПЛАН tab ─────────────────────────────────────────────────
function _buildPlanTab() {
  const goals = _bsArc?.chapter_goals || [];
  if (!goals.length) return `
    <div style="text-align:center;padding:48px 20px;color:var(--text-dim)">
      <div style="font-size:3rem;margin-bottom:10px">📋</div>
      <div style="font-size:.9rem;color:var(--text);font-weight:700;margin-bottom:6px">Сценарий не построен</div>
      <div style="font-size:.75rem;margin-bottom:20px;max-width:340px;margin-inline:auto;line-height:1.6">
        Без сценария агент пишет наугад — слабые оценки это следствие. Построй арку — каждая глава получит цель.
      </div>
      <button class="wyrd-btn" onclick="bsBuildArc('${_bsSlug}')">📐 Построить арку</button>
    </div>`;

  const chMap = Object.fromEntries(_bsChapters.map(c => [c.number, c]));
  const written = _bsChapters.length, total = goals.length;
  const pct = Math.min(100, Math.round(written/total*100));

  const blocks = goals.map(g => {
    const ch = chMap[g.number], sc = ch?.score||0;
    const bg = ch ? _scoreColor(sc) : 'rgba(255,255,255,.08)';
    const fn = (g.arc_function||'').toLowerCase(), dot = _FN_COL[fn];
    return `<div onclick="${ch?`openBsChapter('${_bsSlug}',${g.number})`:''}"
      title="Гл.${g.number}${ch?' · '+sc.toFixed(1):' — не написана'} | ${(g.goal||'').slice(0,55)}"
      style="width:30px;height:34px;border-radius:5px;background:${bg};border:1px solid ${ch?'transparent':'rgba(255,255,255,.15)'};
             display:flex;flex-direction:column;align-items:center;justify-content:center;
             cursor:${ch?'pointer':'default'};transition:transform .1s;flex-shrink:0"
      onmouseenter="this.style.transform='scale(1.15)'" onmouseleave="this.style.transform='scale(1)'">
      <div style="font-size:.52rem;font-weight:700;color:${ch?'rgba(0,0,0,.75)':'rgba(255,255,255,.35)'}">${g.number}</div>
      ${dot?`<div style="width:6px;height:2px;border-radius:1px;background:${dot};margin-top:2px"></div>`:''}
    </div>`;
  }).join('');

  const rows = goals.map(g => {
    const ch = chMap[g.number], fn = (g.arc_function||'').toLowerCase();
    const col = _FN_COL[fn]||'var(--text-dim)';
    const badge = ch
      ? (ch.score>=_BS_OK
          ? `<span style="font-size:.62rem;color:var(--green)">✅ ${ch.score.toFixed(1)}</span>`
          : `<span style="font-size:.62rem;color:var(--red)">⚠️ ${ch.score.toFixed(1)}</span>`)
      : `<span style="font-size:.62rem;color:rgba(255,255,255,.2)">○</span>`;
    return `<div style="display:flex;gap:8px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04);align-items:flex-start">
      <div style="min-width:24px;height:18px;border-radius:3px;background:${col}22;border:1px solid ${col}44;display:flex;align-items:center;justify-content:center;font-size:.58rem;color:${col};font-weight:700;flex-shrink:0;margin-top:1px">${g.number}</div>
      <div style="flex:1;font-size:.73rem;color:var(--text);line-height:1.5">${g.goal||''}</div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px;flex-shrink:0">
        ${badge}
        ${fn?`<span style="font-size:.55rem;color:${col};text-transform:uppercase">${fn}</span>`:''}
      </div>
    </div>`;
  }).join('');

  return `<div style="display:grid;grid-template-columns:1fr 310px;gap:14px">
    <div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:12px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
          <div>
            <span style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em">📐 ${_bsArc?.arc_name||'Арка 1'}</span>
            <span style="margin-left:8px;font-size:.72rem;color:var(--amber);font-weight:700">${total} глав · ${written} написано</span>
          </div>
          <button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" onclick="bsBuildArc('${_bsSlug}')" title="Пересобрать арку">🔄</button>
        </div>
        <div style="background:rgba(255,255,255,.08);border-radius:4px;height:7px;margin-bottom:10px">
          <div style="width:${pct}%;height:100%;background:var(--amber);border-radius:4px;box-shadow:0 0 8px rgba(255,176,32,.35);transition:width .5s"></div>
        </div>
        <div style="font-size:.72rem;color:var(--text-dim);line-height:1.55;padding:8px 10px;background:rgba(255,255,255,.03);border-radius:6px;border-left:2px solid var(--amber);margin-bottom:14px">${_bsArc?.arc_summary||''}</div>
        <div style="display:flex;flex-wrap:wrap;gap:3px">${blocks}</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px">
        <div style="font-size:.62rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:10px">СЦЕНАРИЙ ГЛАВ</div>
        <div style="max-height:320px;overflow-y:auto">${rows}</div>
      </div>
    </div>
    <div>
      <div id="bs-scout" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:12px">
        <div style="color:var(--text-dim);font-size:.75rem">Загрузка разведки...</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px">
        <button class="wyrd-btn wyrd-btn-sm" style="width:100%" onclick="loadBsNextBook('${_bsSlug}')">🧠 Следующая книга</button>
        <div id="bs-next-book" style="margin-top:12px"></div>
      </div>
    </div>
  </div>`;
}

// ── ГЛАВЫ tab ─────────────────────────────────────────────────
function _buildChaptersTab() {
  const slug = _bsSlug, chs = _bsChapters;
  const scores = chs.map(c => c.score||0);
  const avg = scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : '—';
  const trend = _scoreTrend(scores);
  const tc = trend==='↑'?'var(--green)':trend==='↓'?'var(--red)':'var(--text-dim)';
  const toPublish = chs.filter(c => !c.published && (c.score||0)>=_BS_OK);
  const filtered = _bsApplyFilter(chs);
  const rows = [...filtered].reverse().map(c => _chapterRow(slug, c)).join('');
  const sp = _sparkline(scores.slice(-10));
  const filters = [['all','Все'],['pub','RULATE'],['draft','Черн.'],['good','≥7.5'],['ok','6.5–7.5']]
    .map(([f,l]) => `<button class="wyrd-btn wyrd-btn-sm${_bsFilter===f?'':' wyrd-btn-ghost'}" onclick="bsSetFilter('${f}')" style="padding:3px 8px">${l}</button>`).join('');
  return `<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:6px">
      <div>
        <span style="font-size:.7rem;color:var(--text-dim);letter-spacing:.08em">ГЛАВЫ</span>
        <span style="font-size:.75rem;color:var(--text);margin-left:8px"><b style="color:var(--amber)">${chs.length}</b> шт</span>
        <span style="font-size:.75rem;color:var(--text-dim);margin-left:8px">ср. <b style="color:${_scoreColor(parseFloat(avg)||0)}">${avg}</b>/10</span>
        <span style="font-size:.9rem;color:${tc};margin-left:8px;font-weight:700">${trend}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        ${sp}
        <button class="wyrd-btn wyrd-btn-sm" onclick="bsGenerate('${slug}')">＋ Глава</button>
        ${toPublish.length?`<button class="wyrd-btn wyrd-btn-sm" onclick="bsPublishAll('${slug}')" title="${toPublish.length} глав ≥${_BS_OK}">📤 Все (${toPublish.length})</button>`:''}
      </div>
    </div>
    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px">${filters}</div>
    ${filtered.length<chs.length?`<div style="font-size:.65rem;color:var(--text-dim);margin-bottom:6px">${filtered.length} из ${chs.length}</div>`:''}
    <div style="max-height:460px;overflow-y:auto;margin:0 -14px;padding:0 14px">${rows}</div>
  </div>`;
}

function _bsApplyFilter(chs) {
  if (_bsFilter==='pub') return chs.filter(c => c.published);
  if (_bsFilter==='draft') return chs.filter(c => !c.published);
  if (_bsFilter==='good') return chs.filter(c => (c.score||0)>=_BS_GOOD);
  if (_bsFilter==='ok') return chs.filter(c => (c.score||0)>=_BS_OK && (c.score||0)<_BS_GOOD);
  return chs;
}

function bsSetFilter(f) { _bsFilter = f; _renderBookBody(); }

// ── КОНТРОЛЬ tab ──────────────────────────────────────────────
function _buildControlTab() {
  const goals = _bsArc?.chapter_goals || [];
  if (!_bsChapters.length) return `<div style="text-align:center;padding:40px;color:var(--text-dim);font-size:.78rem">Глав пока нет</div>`;
  if (!goals.length) return `<div style="text-align:center;padding:32px;color:var(--text-dim)">
    <div style="font-size:1.5rem;margin-bottom:8px">🔍</div>
    <div style="font-size:.8rem;margin-bottom:12px">Сначала постройте сценарий в 📋 ПЛАН</div>
    <div style="font-size:.72rem">Контроль сверяет каждую главу с её целью из арки</div>
  </div>`;

  const goalMap = Object.fromEntries(goals.map(g => [g.number, g]));
  const rows = [..._bsChapters].sort((a,b) => b.number-a.number).map(c => {
    const g = goalMap[c.number], sc = c.score||0, col = _scoreColor(sc);
    const fn = (g?.arc_function||'').toLowerCase(), fnCol = _FN_COL[fn]||'var(--border)';
    const verdict = sc>=_BS_OK
      ? `<span style="color:var(--green);font-size:.68rem;font-weight:700">✅ ПРИНЯТО</span>`
      : `<span style="color:var(--red);font-size:.68rem;font-weight:700">❌ СЛАБО</span>`;
    const pubBadge = c.published
      ? `<span style="font-size:.6rem;background:rgba(74,255,136,.12);color:var(--green);border-radius:4px;padding:1px 6px">RULATE</span>`
      : `<span style="font-size:.6rem;background:rgba(255,255,255,.06);color:var(--text-dim);border-radius:4px;padding:1px 6px">черн.</span>`;
    return `<div style="padding:10px 12px;margin-bottom:8px;background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:8px;border-left:3px solid ${col}">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:${g?'8px':'0'}">
        <div style="min-width:28px;height:24px;border-radius:5px;background:${col}22;border:1px solid ${col}44;display:flex;align-items:center;justify-content:center;font-size:.62rem;color:${col};font-weight:700">${c.number}</div>
        <div style="flex:1;font-size:.78rem;color:var(--text);font-weight:600">${c.title}</div>
        <span style="font-size:1.1rem;font-weight:900;color:${col}">${sc.toFixed(1)}</span>
        ${verdict}
        ${pubBadge}
      </div>
      ${g?`<div style="font-size:.7rem;color:var(--text-dim);line-height:1.5;padding:5px 8px;background:rgba(255,255,255,.03);border-radius:5px;border-left:2px solid ${fnCol}">🎯 ${g.goal}${fn?` <span style="color:${fnCol};text-transform:uppercase;font-size:.6rem">[${fn}]</span>`:''}</div>`:''}
    </div>`;
  }).join('');

  const ok = _bsChapters.filter(c => (c.score||0)>=_BS_OK).length;
  const bad = _bsChapters.length - ok;
  return `<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border)">
      <span style="font-size:.62rem;color:var(--text-dim);letter-spacing:.08em">🔍 КОНТРОЛЬ КАЧЕСТВА</span>
      <span style="font-size:.72rem;color:var(--green)">✅ Принято: ${ok}</span>
      <span style="font-size:.72rem;color:var(--red)">❌ Слабых: ${bad}</span>
    </div>
    <div style="max-height:520px;overflow-y:auto">${rows}</div>
  </div>`;
}

// ── Chapter row ───────────────────────────────────────────────
function _chapterRow(slug, c) {
  const sc = c.score||0, col = _scoreColor(sc);
  const pubBadge = c.published
    ? `<span style="font-size:.6rem;background:rgba(74,255,136,.12);color:var(--green);border-radius:4px;padding:1px 5px">RULATE</span>`
    : `<span style="font-size:.6rem;background:rgba(255,255,255,.06);color:var(--text-dim);border-radius:4px;padding:1px 5px">черн.</span>`;
  return `<div class="bs-ch-row" onclick="openBsChapter('${slug}',${c.number})"
    style="display:flex;align-items:center;gap:10px;padding:9px 10px;margin:0 -10px;border-radius:8px;cursor:pointer;transition:background .15s;border-bottom:1px solid rgba(255,255,255,.04)"
    onmouseenter="this.style.background='rgba(255,255,255,.06)'" onmouseleave="this.style.background='transparent'">
    <div style="min-width:28px;height:28px;border-radius:6px;background:rgba(255,255,255,.07);display:flex;align-items:center;justify-content:center;font-size:.65rem;color:var(--text-dim);font-weight:700;flex-shrink:0">${c.number}</div>
    <div style="flex:1;min-width:0">
      <div style="font-size:.78rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px">${c.title}</div>
      <div style="display:flex;align-items:center;gap:8px">${_scoreBar(sc)}${pubBadge}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;display:flex;align-items:center;gap:6px">
      <div style="font-size:.9rem;font-weight:800;color:${col}">${sc.toFixed(1)}</div>
      <div style="color:var(--text-dim);font-size:.75rem;opacity:.5">›</div>
    </div>
  </div>`;
}

// ── Scout + next book ─────────────────────────────────────────
function _renderBsScout(scout) {
  const el = document.getElementById('bs-scout');
  if (!el || !scout) return;
  const chip = (t, col) => `<span style="display:inline-block;background:${col}22;color:${col};border:1px solid ${col}44;border-radius:4px;padding:2px 8px;font-size:.65rem;margin:2px">${t}</span>`;
  el.innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:10px">🔭 РАЗВЕДКА РЫНКА</div>
    <div style="margin-bottom:6px"><div style="font-size:.62rem;color:var(--text-dim);margin-bottom:4px">ТРЕНДЫ</div>${(scout.trending_genres||[]).map(g=>chip(g,'var(--green)')).join('')||'—'}</div>
    <div style="margin-bottom:6px"><div style="font-size:.62rem;color:var(--text-dim);margin-bottom:4px">МЕХАНИКИ</div>${(scout.top_mechanics||[]).map(m=>chip(m,'var(--purple)')).join('')||'—'}</div>
    <div><div style="font-size:.62rem;color:var(--text-dim);margin-bottom:4px">ИЗБЕГАТЬ</div>${(scout.avoid||[]).map(a=>chip(a,'var(--red)')).join('')||'—'}</div>`;
}

async function loadBsNextBook(slug) {
  const el = document.getElementById('bs-next-book');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.78rem">Анализирую рынок... (~20 сек)</div>';
  try {
    const d = await fetch(`/bs/books/${slug||_bsSlug}/next-book`, {method:'POST'}).then(r=>r.json());
    const ideas = d.ideas||[];
    if (!ideas.length) { el.innerHTML = `<div style="color:var(--text-dim);font-size:.75rem">${d.error||'Идеи не получены'}</div>`; return; }
    el.innerHTML = `<div style="font-size:.62rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:8px">💡 КОНЦЕПЦИИ</div>` +
      ideas.map((idea,i) => `<div style="background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin-bottom:8px"
        onmouseenter="this.style.borderColor='var(--amber)'" onmouseleave="this.style.borderColor='var(--border)'">
        <div style="font-size:.78rem;font-weight:700;color:var(--amber);margin-bottom:4px">${i+1}. ${idea.title||'Идея'}</div>
        <div style="font-size:.73rem;color:var(--text);line-height:1.55;margin-bottom:4px">${idea.hook||''}</div>
        ${idea.why_it_works?`<div style="font-size:.67rem;color:var(--green)">✓ ${idea.why_it_works}</div>`:''}
      </div>`).join('');
  } catch(e) { el.innerHTML = `<div style="color:var(--red);font-size:.75rem">${e.message}</div>`; }
}

// ── Arc build ─────────────────────────────────────────────────
async function bsBuildArc(slug) {
  const s = slug||_bsSlug;
  showToast('📐 Строим арку... (~30 сек)');
  try {
    await fetch(`/bs/books/${s}/arc`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({book_slug:s, arc_number:1, chapters_count:20})
    });
    _bsArc = await _bsFetch(`/bs/books/${s}/arc`).catch(()=>null);
    _renderBookBody();
    showToast('✅ Арка построена');
  } catch(e) { showToast('❌ '+e.message); }
}

// ── Chapter viewer ────────────────────────────────────────────
async function openBsChapter(slug, num) {
  let ov = document.getElementById('bs-ch-ov');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'bs-ch-ov';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:8000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
    ov.addEventListener('click', e => { if (e.target===ov) ov.remove(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = '<div style="color:var(--text-dim)">Загрузка...</div>';
  ov.style.display = 'flex';
  try {
    const ch = await _bsFetch(`/bs/books/${slug}/chapters/${num}`);
    const sc = ch.score||0;
    const pubBtn = !ch.published ? `<div style="padding:12px 20px;border-top:1px solid var(--border)">
      <button class="wyrd-btn wyrd-btn-sm" onclick="bsPublish('${slug}',${ch.number})">📤 Опубликовать на Rulate</button>
    </div>` : '';
    ov.innerHTML = `<div style="width:min(740px,96vw);max-height:90vh;background:#0d1117;border:1px solid var(--border);border-radius:14px;display:flex;flex-direction:column;box-shadow:0 24px 60px rgba(0,0,0,.6)">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)">
        <div>
          <div style="font-size:.6rem;color:var(--text-dim);letter-spacing:.1em;margin-bottom:4px">ГЛАВА ${ch.number}</div>
          <div style="font-size:.95rem;font-weight:700;color:var(--text)">${ch.title}</div>
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <div style="text-align:center">
            <div style="font-size:1.4rem;font-weight:900;color:${_scoreColor(sc)}">${sc.toFixed(1)}</div>
            <div style="font-size:.6rem;color:var(--text-dim)">ОЦЕНКА</div>
          </div>
          <div style="font-size:.7rem;color:${ch.published?'var(--green)':'var(--text-dim)'}">${ch.published?'✅ Rulate':'⬜ черн.'}</div>
          <button onclick="document.getElementById('bs-ch-ov').remove()"
            style="background:none;border:1px solid var(--border);color:var(--text-dim);border-radius:8px;padding:5px 12px;cursor:pointer;font-size:.85rem"
            onmouseenter="this.style.borderColor='var(--text)'" onmouseleave="this.style.borderColor='var(--border)'">✕</button>
        </div>
      </div>
      <div style="overflow-y:auto;padding:20px 24px;font-size:.85rem;line-height:2;color:var(--text);white-space:pre-wrap">${ch.content||''}</div>
      ${pubBtn}
    </div>`;
  } catch(e) { ov.innerHTML = `<div style="color:var(--red);padding:20px">${e.message}</div>`; }
}

// ── Actions ───────────────────────────────────────────────────
async function bsGenerate(slug) {
  const s = slug||_bsSlug;
  try {
    const r = await fetch(`/bs/books/${s}/generate`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({book_slug:s, target_words:2000})});
    const d = await r.json();
    showToast(d.ok ? `✅ Глава ${d.queued_chapter} в очереди` : '❌ Ошибка');
    if (d.ok) setTimeout(() => loadBookStudio(), 4000);
  } catch(e) { showToast('❌ '+e.message); }
}

async function bsPublish(slug, num) {
  if (!confirm(`Опубликовать главу ${num} на Rulate?`)) return;
  try {
    const d = await fetch(`/bs/books/${slug}/publish/${num}`, {method:'POST'}).then(r=>r.json());
    showToast(d.ok ? `✅ Глава ${num} на Rulate` : '❌ Ошибка');
    document.getElementById('bs-ch-ov')?.remove();
    if (d.ok) setTimeout(() => loadBookStudio(), 2000);
  } catch(e) { showToast('❌ '+e.message); }
}

async function bsPublishAll(slug) {
  const s = slug||_bsSlug;
  const toPublish = _bsChapters.filter(c => !c.published && (c.score||0)>=_BS_OK).sort((a,b)=>a.number-b.number);
  if (!toPublish.length) { showToast('Нет глав для публикации'); return; }
  if (!confirm(`Опубликовать ${toPublish.length} глав (score ≥ ${_BS_OK})?`)) return;
  let ok = 0, err = 0;
  for (const c of toPublish) {
    try { const d = await fetch(`/bs/books/${s}/publish/${c.number}`, {method:'POST'}).then(r=>r.json()); if(d.ok) ok++; else err++; }
    catch { err++; }
    await new Promise(res => setTimeout(res, 600));
  }
  showToast(`✅ Опубликовано: ${ok}${err?' | ❌ Ошибок: '+err:''}`);
  await loadBookStudio();
}

// ── Helpers ───────────────────────────────────────────────────
function _scoreBar(s) {
  const w = Math.min(100, Math.round(s*10)), col = _scoreColor(s);
  return `<div style="flex:1;background:rgba(255,255,255,.08);border-radius:4px;height:6px;max-width:120px">
    <div style="width:${w}%;height:100%;background:${col};border-radius:4px;box-shadow:0 0 6px ${col}66;transition:width .3s"></div></div>`;
}

function _scoreColor(s) { return s>=_BS_GOOD?'var(--green)':s>=_BS_OK?'var(--amber)':'var(--red)'; }

function _scoreTrend(scores) {
  if (scores.length<3) return '—';
  const d = scores[scores.length-1] - scores[scores.length-3];
  return d>0.3?'↑':d<-0.3?'↓':'→';
}

function _sparkline(scores) {
  if (scores.length<2) return '';
  const W=60,H=20,pad=2, min=Math.min(...scores), max=Math.max(...scores), range=max-min||1;
  const pts = scores.map((s,i) => {
    const x=pad+(i/(scores.length-1))*(W-pad*2), y=H-pad-((s-min)/range)*(H-pad*2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const last = scores[scores.length-1], col = _scoreColor(last);
  const [lx,ly] = pts.split(' ').pop().split(',');
  return `<svg width="${W}" height="${H}" style="opacity:.7;vertical-align:middle">
    <polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${lx}" cy="${ly}" r="2.5" fill="${col}"/>
  </svg>`;
}
