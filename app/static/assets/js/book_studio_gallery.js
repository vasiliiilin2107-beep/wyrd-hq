/* WYRD Book Studio — галерея постеров + страница книги.
   Ядро (состояние, fetch, действия): book_studio.js */

const _BS_PAL = [
  ['#7c3aed','#1e1b4b'], ['#f59e0b','#451a03'], ['#10b981','#022c22'],
  ['#3b82f6','#172554'], ['#ec4899','#500724'], ['#ef4444','#450a0a'],
];

// ── ГАЛЕРЕЯ ───────────────────────────────────────────────────
function bsRenderGallery() {
  const d = _bsStats || {}, books = _bsBooks;
  const sEl = document.getElementById('bs-stats');
  const tEl = document.getElementById('bs-book-tabs');
  const bEl = document.getElementById('bs-book-body');
  if (tEl) tEl.innerHTML = '';
  const withScore = books.filter(b => (b.avg_score||0) > 0);
  const avg = withScore.length ? (withScore.reduce((s,b) => s+(b.avg_score||0), 0)/withScore.length).toFixed(1) : '—';
  if (sEl) sEl.innerHTML =
    _bsStatCard(d.total_chapters||0, 'НАПИСАНО', 'var(--color-studio)', '✍️') +
    _bsStatCard(d.total_published||0, 'НА RULATE', 'var(--status-alive)', '📤') +
    _bsStatCard(books.length, 'КНИГ', 'var(--color-agents)', '📚') +
    _bsStatCard(avg, 'СР. ОЦЕНКА', _scoreColor(parseFloat(avg)||0), '⭐');

  const posters = books.map(b => _bsPosterCard(b)).join('');
  const ideas = _bsIdeasList();
  const ideasBlock = ideas.length
    ? `<div class="stat-card-label" style="margin:18px 0 10px">💡 ИДЕИ АНАЛИТИКА — ВЫБЕРИ СЛЕДУЮЩУЮ КНИГУ</div>
       <div class="bs-ideas-row">${ideas.slice(0,6).map((idea,i) => _bsIdeaCard(idea,i)).join('')}</div>`
    : `<div style="margin-top:18px;font-size:.72rem;color:var(--text-secondary)">💡 Идей нет — запусти разведку из вкладки КОМАНДА любой книги</div>`;
  if (bEl) bEl.innerHTML =
    `<div style="display:flex;justify-content:flex-end;margin-bottom:10px">
      <button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" onclick="bsOpenOffice()">🏢 Офис агентов</button>
    </div>`
    + (posters
      ? `<div class="bs-gallery">${posters}</div>`
      : `<div class="bs-empty"><div style="font-size:3rem">📚</div><div>Книг пока нет — создай первую из идеи Аналитика</div></div>`)
    + ideasBlock;
}

function _bsStatCard(v, label, color, icon) {
  return `<div class="stat-card" style="--stat-accent:${color};position:relative;overflow:hidden">
    <div class="stat-card-value" style="color:${color}">${v}</div>
    <div class="stat-card-label">${label}</div>
    <div style="position:absolute;right:10px;top:10px;font-size:1.3rem;opacity:.13">${icon}</div>
  </div>`;
}

function _bsPosterCard(b) {
  return `<div class="bs-poster" onclick="bsOpenBook('${b.slug}')">
    ${_bsPosterSvg(b)}
    <div class="bs-poster-meta">
      <div class="bs-poster-title" title="${b.title}">${b.title}</div>
      <div class="bs-poster-sub">${b.chapters_total||0} глав · ${b.chapters_published||0} на Rulate</div>
    </div>
  </div>`;
}

function _bsPosterSvg(b, gid) {
  const [c1,c2] = _BS_PAL[(b.slug||'').length % _BS_PAL.length];
  const init = (b.title||'?').replace(/[«»"'!?:.,—-]/g,'').trim().split(/\s+/).slice(0,2).map(w => w[0]||'').join('').toUpperCase() || '?';
  const sc = b.avg_score || 0;
  const scCol = sc >= _BS_GOOD ? '#22c55e' : sc >= _BS_OK ? '#f59e0b' : '#ef4444';
  const genre = (b.genre||'').replace(/_/g,' ').toUpperCase().slice(0,18);
  const id = `bsg-${gid||'g'}-${b.slug}`;
  return `<svg viewBox="0 0 200 300" class="bs-poster-cover" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="0.6" y2="1">
      <stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/>
    </linearGradient></defs>
    <rect width="200" height="300" rx="10" fill="url(#${id})"/>
    <rect x="6" y="6" width="188" height="288" rx="7" fill="none" stroke="rgba(255,255,255,.22)"/>
    <text x="100" y="158" text-anchor="middle" font-size="64" font-weight="900" fill="rgba(255,255,255,.92)" font-family="Georgia,serif">${init}</text>
    <text x="100" y="262" text-anchor="middle" font-size="12" fill="rgba(255,255,255,.55)" letter-spacing="2">${genre}</text>
    ${sc ? `<circle cx="168" cy="32" r="20" fill="rgba(0,0,0,.45)"/><text x="168" y="37" text-anchor="middle" font-size="14" font-weight="800" fill="${scCol}">${sc.toFixed(1)}</text>` : ''}
    <text x="14" y="287" font-size="9" fill="rgba(255,255,255,.4)" letter-spacing="1">WYRD</text>
  </svg>`;
}

function _bsIdeaCard(idea, i) {
  return `<div class="bs-idea-card">
    <div style="font-size:.8rem;font-weight:700;color:var(--color-studio);margin-bottom:4px">${idea.title||idea.idea||'Идея'}</div>
    <div style="font-size:.7rem;color:var(--text-secondary);line-height:1.5;flex:1">${idea.hook||idea.description||''}</div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;gap:8px">
      <span style="font-size:.62rem;color:var(--color-agents)">${(idea.genre||'').replace(/_/g,' ')}</span>
      <button class="wyrd-btn wyrd-btn-sm" onclick="bsCreateBook(${i})">🚀 Создать</button>
    </div>
  </div>`;
}

// ── СТРАНИЦА КНИГИ ────────────────────────────────────────────
function bsOpenBook(slug) {
  _bsSlug = slug; _bsBookTab = 'chapters'; _bsFilter = 'all';
  _bsConductor = null; _bsPanels = null; _bsMetrics = null;
  loadBookStudio();
}
function bsBackToGallery() { _bsSlug = null; loadBookStudio(); }

function bsRenderBookPage() {
  const sEl = document.getElementById('bs-stats');
  const tEl = document.getElementById('bs-book-tabs');
  const bEl = document.getElementById('bs-book-body');
  if (sEl) sEl.innerHTML = ''; if (tEl) tEl.innerHTML = '';
  if (!bEl) return;
  const b = _bsBooks.find(x => x.slug === _bsSlug) || {slug:_bsSlug, title:_bsSlug, genre:''};
  const chs = _bsChapters, scores = chs.map(c => c.score||0);
  const avg = scores.length ? (scores.reduce((a,x) => a+x, 0)/scores.length).toFixed(1) : '—';
  const trend = _scoreTrend(scores), tc = trend==='↑' ? 'var(--status-alive)' : trend==='↓' ? 'var(--status-dead)' : 'var(--text-secondary)';

  const tabs = [['chapters','✍️ ГЛАВЫ'],['team','👥 КОМАНДА'],['plan','📋 ПЛАН'],['control','🔍 КОНТРОЛЬ']];
  const nav = `<div style="display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap">${tabs.map(([t,l]) =>
    `<button onclick="bsBookTab('${t}')" class="wyrd-btn wyrd-btn-sm${_bsBookTab===t?'':' wyrd-btn-ghost'}"
      style="${_bsBookTab===t?'background:var(--color-studio);color:#0d1117':''}">${l}</button>`).join('')}</div>`;
  const fn = {chapters:_buildChaptersTab, team:_buildTeamTab, plan:_buildPlanTab, control:_buildControlTab}[_bsBookTab];

  bEl.innerHTML = `
    <button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" onclick="bsBackToGallery()" style="margin-bottom:12px">← Галерея</button>
    <div class="bs-book-page">
      <div class="bs-book-side">
        ${_bsPosterSvg(b, 'page')}
        <div style="font-size:.92rem;font-weight:800;margin:10px 0 8px;line-height:1.3">${b.title}</div>
        <div class="bs-meta-row"><span>Жанр</span><b>${(b.genre||'—').replace(/_/g,' ')}</b></div>
        <div class="bs-meta-row"><span>Глав</span><b>${chs.length}</b></div>
        <div class="bs-meta-row"><span>На Rulate</span><b>${chs.filter(c=>c.published).length}</b></div>
        <div class="bs-meta-row"><span>Ср. оценка</span><b style="color:${_scoreColor(parseFloat(avg)||0)}">${avg}</b></div>
        <div class="bs-meta-row"><span>Тренд</span><b style="color:${tc}">${trend}</b></div>
        ${b.rulate_url ? `<a href="${b.rulate_url}" target="_blank" class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" style="width:100%;margin-top:10px;text-align:center;display:block">↗ Открыть на Rulate</a>` : ''}
        <button class="wyrd-btn wyrd-btn-sm" style="width:100%;margin-top:8px" onclick="bsGenerate('${b.slug}')">＋ Глава</button>
        <button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" style="width:100%;margin-top:8px" onclick="bsOpenOffice()">🏢 Офис агентов</button>
        ${!_bsArc ? `<button class="wyrd-btn wyrd-btn-sm wyrd-btn-ghost" style="width:100%;margin-top:8px" onclick="bsPrepareBook('${b.slug}')">📐 Подготовка (Bible + арки)</button>` : ''}
      </div>
      <div class="bs-book-main">${nav}${fn()}</div>
    </div>`;
}

function bsBookTab(t) { _bsBookTab = t; bsRenderBookPage(); if (t === 'team') _loadTeamData(); }
function bsSetFilter(f) { _bsFilter = f; bsRenderBookPage(); }

function _bsApplyFilter(chs) {
  if (_bsFilter === 'pub')   return chs.filter(c => c.published);
  if (_bsFilter === 'draft') return chs.filter(c => !c.published);
  if (_bsFilter === 'good')  return chs.filter(c => (c.score||0) >= _BS_GOOD);
  if (_bsFilter === 'ok')    return chs.filter(c => (c.score||0) >= _BS_OK && (c.score||0) < _BS_GOOD);
  return chs;
}

// ── ГЛАВЫ ─────────────────────────────────────────────────────
function _buildChaptersTab() {
  const slug = _bsSlug, chs = _bsChapters;
  if (!chs.length) return `<div class="bs-empty"><div style="font-size:3rem">✍️</div><div>Глав пока нет</div>
    <button class="wyrd-btn" onclick="bsGenerate('${slug}')">＋ Написать первую</button></div>`;
  const scores = chs.map(c => c.score||0);
  const toPublish = chs.filter(c => !c.published && (c.score||0) >= _BS_OK);
  const filtered = _bsApplyFilter(chs);
  const filters = [['all','Все'],['pub','RULATE'],['draft','Черн.'],['good','≥7.5'],['ok','6.5–7.5']]
    .map(([f,l]) => `<button class="wyrd-btn wyrd-btn-sm${_bsFilter===f?'':' wyrd-btn-ghost'}" onclick="bsSetFilter('${f}')" style="padding:3px 8px">${l}</button>`).join('');
  return `<div style="background:var(--bg-surface);border:1px solid var(--border-dim);border-radius:var(--r-md);padding:14px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:6px">
      <div style="display:flex;gap:4px;flex-wrap:wrap">${filters}</div>
      <div style="display:flex;align-items:center;gap:6px">
        ${_sparkline(scores.slice(-10))}
        ${toPublish.length ? `<button class="wyrd-btn wyrd-btn-sm" onclick="bsPublishAll('${slug}')">📤 Опубликовать (${toPublish.length})</button>` : ''}
      </div>
    </div>
    ${filtered.length < chs.length ? `<div style="font-size:.65rem;color:var(--text-secondary);margin-bottom:6px">${filtered.length} из ${chs.length}</div>` : ''}
    <div style="max-height:460px;overflow-y:auto;margin:0 -14px;padding:0 14px">${[...filtered].reverse().map(c => _chapterRow(slug,c)).join('')}</div>
  </div>`;
}

function _chapterRow(slug, c) {
  const sc = c.score||0, col = _scoreColor(sc);
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
        ${dirs.slice(0,4).map(d => `<div>• ${d}</div>`).join('') || cond?.summary}</div>`
    : `<div style="color:var(--text-secondary);font-size:.75rem;margin-bottom:8px">Дирижёр ещё не анализировал</div>`;

  const panels = _bsPanels?.panels || {}, panelNums = Object.keys(panels).map(Number).sort((a,b) => b-a).slice(0,5);
  const panelHtml = panelNums.length
    ? panelNums.map(n => {
        const agg = panels[n]?.aggregate||{}, avg = agg.avg_score?.toFixed(1)||'—', wc = agg.would_continue_pct!=null ? Math.round(agg.would_continue_pct)+'%' : '—', col = _scoreColor(parseFloat(avg)||0);
        return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border-dim)">
          <div class="stat-card-label" style="min-width:32px">Гл${n}</div>
          <div style="flex:1;font-size:.72rem"><b style="color:${col}">${avg}</b>/10</div>
          <div style="font-size:.7rem;color:${parseFloat(wc)>=50?'var(--status-alive)':'var(--status-dead)'}">${wc} дальше</div></div>`;
      }).join('')
    : `<div style="color:var(--text-secondary);font-size:.75rem">Панель не запускалась</div>`;

  const ideas = _bsIdeasList();
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

// ── ПЛАН ──────────────────────────────────────────────────────
function _buildPlanTab() {
  const goals = _bsArc?.chapter_goals || [];
  if (!goals.length || !_bsChapters.length) return `<div class="bs-empty"><div style="font-size:3rem">📋</div><div>Сценарий появится когда конвейер напишет первую главу</div>
    <button class="wyrd-btn" onclick="bsBuildArc('${_bsSlug}')">📐 Построить арку</button></div>`;
  const chMap = Object.fromEntries(_bsChapters.map(c => [c.number, c]));
  const written = _bsChapters.length, total = goals.length, pct = Math.min(100, Math.round(written/total*100));
  const blocks = goals.map(g => {
    const ch = chMap[g.number], sc = ch?.score||0, bg = ch ? _scoreColor(sc) : 'rgba(255,255,255,.08)', fnk = (g.arc_function||'').toLowerCase(), dot = _FN_COL[fnk];
    return `<div onclick="${ch?`openBsChapter('${_bsSlug}',${g.number})`:''}" title="Гл.${g.number}${ch?' · '+sc.toFixed(1):' — не написана'}"
      style="width:30px;height:34px;border-radius:var(--r-sm);background:${bg};border:1px solid ${ch?'transparent':'rgba(255,255,255,.15)'};
             display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:${ch?'pointer':'default'};flex-shrink:0;transition:transform var(--ease-fast)"
      onmouseenter="this.style.transform='scale(1.15)'" onmouseleave="this.style.transform='scale(1)'">
      <div style="font-size:.52rem;font-weight:700;color:${ch?'rgba(0,0,0,.75)':'rgba(255,255,255,.35)'}">${g.number}</div>
      ${dot?`<div style="width:6px;height:2px;border-radius:1px;background:${dot};margin-top:2px"></div>`:''}
    </div>`;
  }).join('');
  const rows = goals.map(g => {
    const ch = chMap[g.number], fnk = (g.arc_function||'').toLowerCase(), col = _FN_COL[fnk]||'var(--text-secondary)';
    const badge = ch ? (ch.score>=_BS_OK ? `<span style="font-size:.62rem;color:var(--status-alive)">✅ ${ch.score.toFixed(1)}</span>` : `<span style="font-size:.62rem;color:var(--status-dead)">⚠️ ${ch.score.toFixed(1)}</span>`)
      : `<span style="font-size:.62rem;color:rgba(255,255,255,.2)">○</span>`;
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
  const ok = _bsChapters.filter(c => (c.score||0) >= _BS_OK).length;
  const rows = [..._bsChapters].sort((a,b) => b.number-a.number).map(c => {
    const g = goalMap[c.number], sc = c.score||0, col = _scoreColor(sc), fnk = (g?.arc_function||'').toLowerCase(), fnCol = _FN_COL[fnk]||'var(--border-dim)';
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
