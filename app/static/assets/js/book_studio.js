/* WYRD Book Studio v5 — Design System polish */

let _bsSlug = null, _bsBookTab = 'chapters', _bsFilter = 'all';
let _bsChapters = [], _bsArc = null;
let _bsConductor = null, _bsPanels = null, _bsIdeas = null, _bsMetrics = null;
const _BS_GOOD = 7.5, _BS_OK = 6.5;
const _FN_COL = {открытие:'#60a5fa',конфликт:'var(--status-dead)',поворот:'var(--color-agents)',пик:'var(--color-studio)',развязка:'var(--status-alive)',setup:'#60a5fa'};

async function _bsFetch(p) {
  const r = await fetch(p, {signal: AbortSignal.timeout(12000)});
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Main ──────────────────────────────────────────────────────
async function loadBookStudio() {
  const sEl = document.getElementById('bs-stats');
  if (sEl) sEl.innerHTML = _bsSkeleton(4);
  try {
    const d = await _bsFetch('/bs/stats');
    _renderBsStats(d);
    const books = d.books || [];
    if (!books.length) return;
    if (!_bsSlug) _bsSlug = books[0].slug;
    const [chs, arc] = await Promise.all([
      _bsFetch(`/bs/books/${_bsSlug}/chapters`),
      _bsFetch(`/bs/books/${_bsSlug}/arc`).catch(() => null)
    ]);
    _bsChapters = chs;
    _bsArc = arc;
    _renderBookBody();
    if (_bsBookTab === 'team') _loadTeamData();
  } catch (e) {
    if (sEl) sEl.innerHTML = `<div class="bs-error">⚠ ${e.message} <button class="wyrd-btn wyrd-btn-sm" style="margin-left:8px" onclick="loadBookStudio()">↺</button></div>`;
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
  _renderBookBody();
}

// ── Stats header ──────────────────────────────────────────────
function _renderBsStats(d) {
  const books = d.books || [];
  const avg = books.length ? (books.reduce((s,b) => s+(b.avg_score||0), 0)/books.length).toFixed(1) : '—';
  const sEl = document.getElementById('bs-stats');
  if (sEl) sEl.innerHTML =
    _bsCard(d.total_chapters||0,'НАПИСАНО','var(--color-studio)','✍️') +
    _bsCard(d.total_published||0,'НА RULATE','var(--status-alive)','📤') +
    _bsCard(books.length,'КНИГ','var(--color-agents)','📚') +
    _bsCard(avg,'СР. ОЦЕНКА',_scoreColor(parseFloat(avg)||0),'⭐');
  const tEl = document.getElementById('bs-book-tabs');
  if (tEl) tEl.innerHTML = books.map(b =>
    `<button class="wyrd-btn wyrd-btn-sm${_bsSlug===b.slug?'':' wyrd-btn-ghost'}" onclick="bsSelectBook('${b.slug}')">
      ${b.title.length>22?b.title.slice(0,22)+'…':b.title}
      <span style="color:var(--color-studio);margin-left:4px">${b.avg_score||'?'}</span>
      ${b.rulate_url?`<a href="${b.rulate_url}" target="_blank" onclick="event.stopPropagation()" style="margin-left:4px;color:var(--text-secondary)">↗</a>`:''}
    </button>`).join('');
}

function _bsCard(v, label, color, icon) {
  return `<div class="stat-card" style="--stat-accent:${color};position:relative;overflow:hidden">
    <div class="stat-card-value" style="color:${color}">${v}</div>
    <div class="stat-card-label">${label}</div>
    <div style="position:absolute;right:10px;top:10px;font-size:1.3rem;opacity:.13">${icon}</div>
  </div>`;
}

function bsSelectBook(slug) {
  _bsSlug = slug; _bsBookTab = 'chapters';
  _bsConductor = null; _bsPanels = null; _bsIdeas = null; _bsMetrics = null;
  loadBookStudio();
}

// ── Tab router ────────────────────────────────────────────────
function _renderBookBody() {
  const el = document.getElementById('bs-book-body');
  if (!el) return;
  const tabs = [['chapters','✍️ ГЛАВЫ'],['team','👥 КОМАНДА'],['plan','📋 ПЛАН'],['control','🔍 КОНТРОЛЬ']];
  const nav = `<div style="display:flex;gap:6px;margin-bottom:16px">${tabs.map(([t,l]) =>
    `<button onclick="bsBookTab('${t}')" class="wyrd-btn wyrd-btn-sm${_bsBookTab===t?'':' wyrd-btn-ghost'}"
      style="${_bsBookTab===t?'background:var(--color-studio);color:#0d1117':''}">${l}</button>`
  ).join('')}</div>`;
  const fn = {chapters:_buildChaptersTab,team:_buildTeamTab,plan:_buildPlanTab,control:_buildControlTab}[_bsBookTab];
  el.innerHTML = nav + fn();
}

function bsBookTab(t) { _bsBookTab = t; _renderBookBody(); if (t==='team') _loadTeamData(); }

// ── ГЛАВЫ ─────────────────────────────────────────────────────
function _buildChaptersTab() {
  const slug = _bsSlug, chs = _bsChapters;
  if (!chs.length) return `<div class="bs-empty"><div style="font-size:3rem">✍️</div><div>Глав пока нет</div>
    <button class="wyrd-btn" onclick="bsGenerate('${slug}')">＋ Написать первую</button></div>`;
  const scores = chs.map(c => c.score||0);
  const avg = (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1);
  const trend = _scoreTrend(scores), tc = trend==='↑'?'var(--status-alive)':trend==='↓'?'var(--status-dead)':'var(--text-secondary)';
  const toPublish = chs.filter(c => !c.published && (c.score||0)>=_BS_OK);
  const filtered = _bsApplyFilter(chs);
  const filters = [['all','Все'],['pub','RULATE'],['draft','Черн.'],['good','≥7.5'],['ok','6.5–7.5']]
    .map(([f,l]) => `<button class="wyrd-btn wyrd-btn-sm${_bsFilter===f?'':' wyrd-btn-ghost'}" onclick="bsSetFilter('${f}')" style="padding:3px 8px">${l}</button>`).join('');
  return `<div style="background:var(--bg-surface);border:1px solid var(--border-dim);border-radius:var(--r-md);padding:14px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:6px">
      <div>
        <span style="font-size:.65rem;color:var(--text-secondary);letter-spacing:.1em;text-transform:uppercase">ГЛАВЫ</span>
        <span style="margin-left:8px;font-size:.75rem"><b style="color:var(--color-studio)">${chs.length}</b></span>
        <span style="margin-left:6px;font-size:.75rem;color:var(--text-secondary)">ср. <b style="color:${_scoreColor(parseFloat(avg))}">${avg}</b>/10</span>
        <span style="margin-left:6px;color:${tc};font-weight:700">${trend}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        ${_sparkline(scores.slice(-10))}
        <button class="wyrd-btn wyrd-btn-sm" onclick="bsGenerate('${slug}')">＋ Глава</button>
        ${toPublish.length?`<button class="wyrd-btn wyrd-btn-sm" onclick="bsPublishAll('${slug}')">📤 (${toPublish.length})</button>`:''}
      </div>
    </div>
    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px">${filters}</div>
    ${filtered.length<chs.length?`<div style="font-size:.65rem;color:var(--text-secondary);margin-bottom:6px">${filtered.length} из ${chs.length}</div>`:''}
    <div style="max-height:460px;overflow-y:auto;margin:0 -14px;padding:0 14px">${[...filtered].reverse().map(c=>_chapterRow(slug,c)).join('')}</div>
  </div>`;
}

function _bsApplyFilter(chs) {
  if (_bsFilter==='pub')   return chs.filter(c => c.published);
  if (_bsFilter==='draft') return chs.filter(c => !c.published);
  if (_bsFilter==='good')  return chs.filter(c => (c.score||0)>=_BS_GOOD);
  if (_bsFilter==='ok')    return chs.filter(c => (c.score||0)>=_BS_OK && (c.score||0)<_BS_GOOD);
  return chs;
}
function bsSetFilter(f) { _bsFilter = f; _renderBookBody(); }

// ── КОМАНДА ───────────────────────────────────────────────────
function _buildTeamTab() {
  const blk = (t, c) =>
    `<div style="background:var(--bg-surface);border:1px solid var(--border-dim);border-radius:var(--r-md);padding:14px;margin-bottom:10px">
      <div class="stat-card-label" style="margin-bottom:10px">${t}</div>${c}</div>`;

  const m = _bsMetrics;
  const metricsHtml = m
    ? `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">
        ${[['👁 ПРОСМОТРЫ',m.views||'—','var(--color-studio)'],
           ['🔖 ЗАКЛАДКИ',m.bookmarks||'—','var(--color-library)'],
           ['⭐ РЕЙТИНГ',m.rating||'—','var(--status-idle)']].map(([l,v,c]) =>
          `<div class="stat-card" style="--stat-accent:${c};text-align:center">
            <div class="stat-card-value" style="color:${c};font-size:1.3rem">${v}</div>
            <div class="stat-card-label">${l}</div></div>`).join('')}
       </div>
       <button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" style="width:100%" onclick="bsLoadMetrics('${_bsSlug}')">↻ Обновить</button>`
    : `<button class="wyrd-btn wyrd-btn-sm" style="width:100%" onclick="bsLoadMetrics('${_bsSlug}')">📊 Загрузить метрики Rulate</button>`;

  const cond = _bsConductor, dirs = cond?.directives || [];
  const condHtml = (dirs.length || cond?.summary)
    ? `<div style="padding:8px 10px;background:var(--gold-dim);border-radius:var(--r-sm);border-left:2px solid var(--color-studio);margin-bottom:8px;font-size:.72rem;line-height:1.7">
        ${dirs.slice(0,4).map(d=>`<div>• ${d}</div>`).join('') || cond?.summary}</div>`
    : `<div style="color:var(--text-secondary);font-size:.75rem;margin-bottom:8px">Дирижёр ещё не анализировал</div>`;

  const panels = _bsPanels?.panels || {}, panelNums = Object.keys(panels).map(Number).sort((a,b)=>b-a).slice(0,5);
  const panelHtml = panelNums.length
    ? panelNums.map(n => {
        const agg=panels[n]?.aggregate||{}, avg=agg.avg_score?.toFixed(1)||'—', wc=agg.would_continue_pct!=null?Math.round(agg.would_continue_pct)+'%':'—', col=_scoreColor(parseFloat(avg)||0);
        return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border-dim)">
          <div class="stat-card-label" style="min-width:32px">Гл${n}</div>
          <div style="flex:1;font-size:.72rem"><b style="color:${col}">${avg}</b>/10</div>
          <div style="font-size:.7rem;color:${parseFloat(wc)>=50?'var(--status-alive)':'var(--status-dead)'}">${wc} дальше</div></div>`;
      }).join('')
    : `<div style="color:var(--text-secondary);font-size:.75rem">Панель не запускалась</div>`;

  const rawIdeas = _bsIdeas, ideas = Array.isArray(rawIdeas)?rawIdeas:(rawIdeas?.ideas||[]);
  const ideasHtml = ideas.length
    ? ideas.slice(0,3).map((idea,i) =>
        `<div style="padding:6px 8px;margin-bottom:6px;background:var(--bg-raised);border-radius:var(--r-sm);border-left:2px solid var(--color-agents)">
          <div style="font-size:.73rem;font-weight:700;color:var(--color-studio)">${i+1}. ${idea.title||idea.idea||'Идея'}</div>
          <div style="font-size:.68rem;color:var(--text-secondary);line-height:1.5;margin-top:2px">${idea.hook||idea.description||''}</div></div>`).join('')
    : `<div style="color:var(--text-secondary);font-size:.75rem;margin-bottom:8px">Нет идей — запусти разведку</div>`;

  return blk('📊 RULATE МЕТРИКИ', metricsHtml) +
    blk('🎯 ДИРИЖЁР', condHtml + `<button class="wyrd-btn wyrd-btn-sm" onclick="bsRunConductor('${_bsSlug}')">🎯 Анализировать</button>`) +
    blk('📚 ЧИТАТЕЛЬСКАЯ ПАНЕЛЬ', panelHtml) +
    blk('💡 АНАЛИТИК — ИДЕИ', ideasHtml + `<button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" style="margin-top:8px;width:100%" onclick="bsRunScout()">🔭 Разведка (~60 сек)</button>`);
}

async function bsLoadMetrics(slug) {
  showToast('Загружаю метрики...');
  try { _bsMetrics = await _bsFetch(`/bs/books/${slug}/rulate_metrics`); _renderBookBody(); }
  catch(e) { showToast('Ошибка: '+e.message); }
}
async function bsRunConductor(slug) {
  showToast('Дирижёр анализирует... (~30 сек)');
  try {
    _bsConductor = await fetch(`/bs/books/${slug}/conductor`,{method:'POST'}).then(r=>r.json());
    _renderBookBody(); showToast('✅ Директивы готовы');
  } catch(e) { showToast('❌ '+e.message); }
}
async function bsRunScout() {
  showToast('Разведка запущена...');
  try {
    await fetch('/bs/scout/all',{method:'POST',signal:AbortSignal.timeout(90000)}).catch(()=>{});
    _bsIdeas = await _bsFetch('/bs/analyst/ideas').catch(()=>null);
    _renderBookBody(); showToast('✅ Разведка завершена');
  } catch(e) { showToast('Разведка: '+e.message); }
}

// ── ПЛАН ──────────────────────────────────────────────────────
function _buildPlanTab() {
  const goals = _bsArc?.chapter_goals || [];
  if (!goals.length || !_bsChapters.length) return `<div class="bs-empty"><div style="font-size:3rem">📋</div><div>Сценарий появится когда конвейер напишет первую главу</div>
    <button class="wyrd-btn" onclick="bsBuildArc('${_bsSlug}')">📐 Построить арку</button></div>`;
  const chMap = Object.fromEntries(_bsChapters.map(c => [c.number, c]));
  const written = _bsChapters.length, total = goals.length, pct = Math.min(100, Math.round(written/total*100));
  const blocks = goals.map(g => {
    const ch=chMap[g.number], sc=ch?.score||0, bg=ch?_scoreColor(sc):'rgba(255,255,255,.08)', fn=(g.arc_function||'').toLowerCase(), dot=_FN_COL[fn];
    return `<div onclick="${ch?`openBsChapter('${_bsSlug}',${g.number})`:''}" title="Гл.${g.number}${ch?' · '+sc.toFixed(1):' — не написана'}"
      style="width:30px;height:34px;border-radius:var(--r-sm);background:${bg};border:1px solid ${ch?'transparent':'rgba(255,255,255,.15)'};
             display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:${ch?'pointer':'default'};flex-shrink:0;transition:transform var(--ease-fast)"
      onmouseenter="this.style.transform='scale(1.15)'" onmouseleave="this.style.transform='scale(1)'">
      <div style="font-size:.52rem;font-weight:700;color:${ch?'rgba(0,0,0,.75)':'rgba(255,255,255,.35)'}">${g.number}</div>
      ${dot?`<div style="width:6px;height:2px;border-radius:1px;background:${dot};margin-top:2px"></div>`:''}
    </div>`;
  }).join('');
  const rows = goals.map(g => {
    const ch=chMap[g.number], fn=(g.arc_function||'').toLowerCase(), col=_FN_COL[fn]||'var(--text-secondary)';
    const badge = ch?(ch.score>=_BS_OK?`<span style="font-size:.62rem;color:var(--status-alive)">✅ ${ch.score.toFixed(1)}</span>`:`<span style="font-size:.62rem;color:var(--status-dead)">⚠️ ${ch.score.toFixed(1)}</span>`)
      :`<span style="font-size:.62rem;color:rgba(255,255,255,.2)">○</span>`;
    return `<div style="display:flex;gap:8px;padding:7px 0;border-bottom:1px solid var(--border-dim);align-items:flex-start">
      <div style="min-width:24px;height:18px;border-radius:3px;background:${col}22;border:1px solid ${col}44;display:flex;align-items:center;justify-content:center;font-size:.58rem;color:${col};font-weight:700;flex-shrink:0;margin-top:1px">${g.number}</div>
      <div style="flex:1;font-size:.73rem;line-height:1.5">${g.goal||''}</div>
      <div style="flex-shrink:0">${badge}</div></div>`;
  }).join('');
  return `<div style="background:var(--bg-surface);border:1px solid var(--border-dim);border-radius:var(--r-md);padding:14px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
      <div><span style="font-size:.65rem;color:var(--text-secondary)">📐 ${_bsArc?.arc_name||'Арка 1'}</span>
        <span style="margin-left:8px;font-size:.72rem;color:var(--color-studio);font-weight:700">${total} глав · ${written} написано</span></div>
      <button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" onclick="bsBuildArc('${_bsSlug}')">🔄</button>
    </div>
    <div style="background:var(--border-dim);border-radius:var(--r-sm);height:7px;margin-bottom:10px">
      <div style="width:${pct}%;height:100%;background:var(--color-studio);border-radius:var(--r-sm);transition:width .5s;box-shadow:0 0 8px rgba(245,158,11,.4)"></div>
    </div>
    <div style="font-size:.72rem;color:var(--text-secondary);line-height:1.55;padding:8px 10px;background:var(--gold-dim);border-radius:var(--r-sm);border-left:2px solid var(--color-studio);margin-bottom:14px">${_bsArc?.arc_summary||''}</div>
    <div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:14px">${blocks}</div>
    <div class="stat-card-label" style="margin-bottom:10px">СЦЕНАРИЙ ГЛАВ</div>
    <div style="max-height:320px;overflow-y:auto">${rows}</div>
  </div>`;
}

// ── КОНТРОЛЬ ──────────────────────────────────────────────────
function _buildControlTab() {
  if (!_bsChapters.length) return `<div class="bs-empty"><div style="font-size:3rem">🔍</div><div>Глав пока нет</div></div>`;
  const goalMap = Object.fromEntries((_bsArc?.chapter_goals||[]).map(g => [g.number, g]));
  const ok = _bsChapters.filter(c=>(c.score||0)>=_BS_OK).length;
  const rows = [..._bsChapters].sort((a,b)=>b.number-a.number).map(c => {
    const g=goalMap[c.number], sc=c.score||0, col=_scoreColor(sc), fn=(g?.arc_function||'').toLowerCase(), fnCol=_FN_COL[fn]||'var(--border-dim)';
    const pub = c.published
      ? `<span style="font-size:.6rem;background:rgba(34,197,94,.12);color:var(--status-alive);border-radius:var(--r-sm);padding:1px 6px">RULATE</span>`
      : `<span style="font-size:.6rem;background:var(--bg-raised);color:var(--text-secondary);border-radius:var(--r-sm);padding:1px 6px">черн.</span>`;
    return `<div style="padding:8px 10px;margin-bottom:6px;background:var(--bg-raised);border:1px solid var(--border-dim);border-radius:var(--r-md);border-left:3px solid ${col}">
      <div style="display:flex;align-items:center;gap:8px">
        <div style="min-width:28px;height:24px;border-radius:var(--r-sm);background:${col}22;display:flex;align-items:center;justify-content:center;font-size:.62rem;color:${col};font-weight:700">${c.number}</div>
        <div style="flex:1;font-size:.78rem;font-weight:600;cursor:pointer" onclick="openBsChapter('${_bsSlug}',${c.number})">${c.title}</div>
        <span style="font-size:1.1rem;font-weight:900;color:${col}">${sc.toFixed(1)}</span>
        <span style="font-size:.68rem;font-weight:700;color:${sc>=_BS_OK?'var(--status-alive)':'var(--status-dead)'}">${sc>=_BS_OK?'✅':'❌'}</span>
        ${pub}
      </div>
      ${g?`<div style="font-size:.68rem;color:var(--text-secondary);margin-top:4px;padding:3px 8px;border-left:2px solid ${fnCol};margin-left:36px">🎯 ${g.goal}</div>`:''}
    </div>`;
  }).join('');
  return `<div style="background:var(--bg-surface);border:1px solid var(--border-dim);border-radius:var(--r-md);padding:14px">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border-dim)">
      <span class="stat-card-label">КОНТРОЛЬ КАЧЕСТВА</span>
      <span style="font-size:.72rem;color:var(--status-alive)">✅ ${ok}</span>
      <span style="font-size:.72rem;color:var(--status-dead)">❌ ${_bsChapters.length-ok}</span>
    </div>
    <div style="max-height:520px;overflow-y:auto">${rows}</div>
  </div>`;
}

// ── Chapter row ───────────────────────────────────────────────
function _chapterRow(slug, c) {
  const sc=c.score||0, col=_scoreColor(sc);
  const pub = c.published
    ? `<span style="font-size:.6rem;background:rgba(34,197,94,.12);color:var(--status-alive);border-radius:var(--r-sm);padding:1px 5px">RULATE</span>`
    : `<span style="font-size:.6rem;background:var(--bg-raised);color:var(--text-secondary);border-radius:var(--r-sm);padding:1px 5px">черн.</span>`;
  return `<div onclick="openBsChapter('${slug}',${c.number})"
    style="display:flex;align-items:center;gap:10px;padding:9px 10px;margin:0 -10px;border-radius:var(--r-md);cursor:pointer;transition:background var(--ease-fast);border-bottom:1px solid var(--border-dim)"
    onmouseenter="this.style.background='var(--bg-raised)'" onmouseleave="this.style.background='transparent'">
    <div style="min-width:28px;height:28px;border-radius:var(--r-sm);background:var(--bg-raised);display:flex;align-items:center;justify-content:center;font-size:.65rem;color:var(--text-secondary);font-weight:700;flex-shrink:0">${c.number}</div>
    <div style="flex:1;min-width:0">
      <div style="font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px">${c.title}</div>
      <div style="display:flex;align-items:center;gap:8px">${_scoreBar(sc)}${pub}</div>
    </div>
    <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
      <div style="font-size:.9rem;font-weight:800;color:${col}">${sc.toFixed(1)}</div>
      <div style="color:var(--text-secondary);font-size:.75rem;opacity:.5">›</div>
    </div>
  </div>`;
}

// ── Arc build ─────────────────────────────────────────────────
async function bsBuildArc(slug) {
  const s=slug||_bsSlug; showToast('📐 Строим арку... (~30 сек)');
  try {
    await fetch(`/bs/books/${s}/arc`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({book_slug:s,arc_number:1,chapters_count:20})});
    _bsArc = await _bsFetch(`/bs/books/${s}/arc`).catch(()=>null);
    _renderBookBody(); showToast('✅ Арка построена');
  } catch(e) { showToast('❌ '+e.message); }
}

// ── Chapter viewer ────────────────────────────────────────────
async function openBsChapter(slug, num) {
  let ov = document.getElementById('bs-ch-ov');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'bs-ch-ov';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:8000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
    ov.addEventListener('click', e => { if(e.target===ov) ov.remove(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = `<div style="color:var(--text-secondary)">Загрузка...</div>`;
  try {
    const ch = await _bsFetch(`/bs/books/${slug}/chapters/${num}`);
    const sc=ch.score||0;
    const pubBtn = !ch.published?`<div style="padding:12px 20px;border-top:1px solid var(--border-dim)">
      <button class="wyrd-btn wyrd-btn-sm" onclick="bsPublish('${slug}',${ch.number})">📤 Опубликовать на Rulate</button></div>`:'';
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
          <div style="font-size:.7rem;color:${ch.published?'var(--status-alive)':'var(--text-secondary)'}">${ch.published?'✅ Rulate':'⬜ черн.'}</div>
          <button onclick="document.getElementById('bs-ch-ov').remove()"
            style="background:none;border:1px solid var(--border-base);color:var(--text-secondary);border-radius:var(--r-md);padding:5px 12px;cursor:pointer">✕</button>
        </div>
      </div>
      <div style="overflow-y:auto;padding:20px 24px;font-size:.85rem;line-height:2;white-space:pre-wrap">${ch.content||''}</div>
      ${pubBtn}
    </div>`;
  } catch(e) { ov.innerHTML = `<div style="color:var(--status-dead);padding:20px">${e.message}</div>`; }
}

// ── Actions ───────────────────────────────────────────────────
async function bsGenerate(slug) {
  const s=slug||_bsSlug;
  try {
    const d = await fetch(`/bs/books/${s}/generate`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({book_slug:s,target_words:2000})}).then(r=>r.json());
    showToast(d.ok?`✅ Глава ${d.queued_chapter} в очереди`:'❌ Ошибка');
    if (d.ok) setTimeout(()=>loadBookStudio(), 4000);
  } catch(e) { showToast('❌ '+e.message); }
}

async function bsPublish(slug, num) {
  if (!confirm(`Опубликовать главу ${num} на Rulate?`)) return;
  try {
    const d = await fetch(`/bs/books/${slug}/publish/${num}`,{method:'POST'}).then(r=>r.json());
    showToast(d.ok?`✅ Глава ${num} на Rulate`:'❌ Ошибка');
    document.getElementById('bs-ch-ov')?.remove();
    if (d.ok) setTimeout(()=>loadBookStudio(), 2000);
  } catch(e) { showToast('❌ '+e.message); }
}

async function bsPublishAll(slug) {
  const s=slug||_bsSlug, toPublish=_bsChapters.filter(c=>!c.published&&(c.score||0)>=_BS_OK).sort((a,b)=>a.number-b.number);
  if (!toPublish.length) { showToast('Нет глав для публикации'); return; }
  if (!confirm(`Опубликовать ${toPublish.length} глав?`)) return;
  let ok=0, err=0;
  for (const c of toPublish) {
    try { const d=await fetch(`/bs/books/${s}/publish/${c.number}`,{method:'POST'}).then(r=>r.json()); if(d.ok) ok++; else err++; }
    catch { err++; }
    await new Promise(res=>setTimeout(res,600));
  }
  showToast(`✅ ${ok}${err?' | ❌ '+err:''}`);
  loadBookStudio();
}

// ── Helpers ───────────────────────────────────────────────────
function _scoreBar(s) {
  const col=_scoreColor(s), pct=Math.min(100,Math.round(s*10));
  return `<div style="flex:1;background:var(--bg-raised);border-radius:var(--r-full);height:6px;max-width:120px">
    <div style="width:${pct}%;height:100%;background:${col};border-radius:var(--r-full);box-shadow:0 0 6px ${col}88"></div></div>`;
}
function _scoreColor(s) { return s>=_BS_GOOD?'var(--status-alive)':s>=_BS_OK?'var(--color-studio)':'var(--status-dead)'; }
function _scoreTrend(s) { if(s.length<3) return '—'; const d=s[s.length-1]-s[s.length-3]; return d>0.3?'↑':d<-0.3?'↓':'→'; }
function _sparkline(scores) {
  if (scores.length<2) return '';
  const W=60,H=20,pad=2,min=Math.min(...scores),max=Math.max(...scores),range=max-min||1;
  const pts=scores.map((s,i)=>{ const x=pad+(i/(scores.length-1))*(W-pad*2),y=H-pad-((s-min)/range)*(H-pad*2); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join(' ');
  const last=scores[scores.length-1],col=_scoreColor(last),[lx,ly]=pts.split(' ').pop().split(',');
  return `<svg width="${W}" height="${H}" style="opacity:.7;vertical-align:middle"><polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${lx}" cy="${ly}" r="2.5" fill="${col}"/></svg>`;
}
function _bsSkeleton(n) {
  return `<div style="display:grid;grid-template-columns:repeat(${n},1fr);gap:10px">${Array.from({length:n},()=>`<div class="ds-skeleton" style="height:72px;border-radius:var(--r-md)"></div>`).join('')}</div>`;
}

setInterval(loadBookStudio, 60000);
