/* WYRD Book Studio — Dashboard JS */

let _bsSlug = null, _bsFilter = 'all', _bsChapters = [];
const _BS_GOOD = 7.5, _BS_OK = 6.5;

async function _bsFetch(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Главный загрузчик ──────────────────────────────────────────
async function loadBookStudio() {
  const sEl = document.getElementById('bs-stats');
  if (sEl) sEl.innerHTML = '<div style="color:var(--text-dim);font-size:.8rem">Загрузка...</div>';
  try {
    const d = await _bsFetch('/bs/stats');
    _renderBsStats(d);
    const books = d.books || [];
    if (books.length) {
      if (!_bsSlug) _bsSlug = books[0].slug;
      await Promise.all([loadBsChapters(_bsSlug), loadBsArc(_bsSlug)]);
      if (d.scout) _renderBsScout(d.scout);
    }
  } catch (e) {
    const el = document.getElementById('bs-stats');
    if (el) el.innerHTML = `<div style="color:var(--red);font-size:.8rem">Ошибка: ${e.message}</div>`;
  }
}

// ── Статы ──────────────────────────────────────────────────────
function _renderBsStats(d) {
  const books = d.books || [];
  const avg = books.length
    ? (books.reduce((s, b) => s + (b.avg_score || 0), 0) / books.length).toFixed(1) : '—';
  const statsEl = document.getElementById('bs-stats');
  if (statsEl) statsEl.innerHTML =
    _bsCard(d.total_chapters || 0, 'НАПИСАНО', 'var(--amber)', '✍️') +
    _bsCard(d.total_published || 0, 'НА RULATE', 'var(--green)', '📤') +
    _bsCard(books.length, 'КНИГ', 'var(--purple)', '📚') +
    _bsCard(avg, 'СР. ОЦЕНКА', _scoreColor(parseFloat(avg)||0), '⭐');

  const tabsEl = document.getElementById('bs-book-tabs');
  if (tabsEl) tabsEl.innerHTML = books.map(b => `
    <button class="wyrd-btn wyrd-btn-sm${_bsSlug === b.slug ? '' : ' wyrd-btn-ghost'}"
      onclick="bsSelectBook('${b.slug}')">
      ${b.title.length > 22 ? b.title.slice(0, 22) + '…' : b.title}
      <span style="color:var(--amber);margin-left:4px">${b.avg_score || '?'}</span>
      ${b.rulate_url ? `<a href="${b.rulate_url}" target="_blank" onclick="event.stopPropagation()"
        style="margin-left:4px;color:var(--text-dim);text-decoration:none" title="Rulate">↗</a>` : ''}
    </button>`).join('');
}

function _bsCard(v, label, color, icon) {
  return `<div style="
    background:var(--card);
    border:1px solid var(--border);
    border-top:3px solid ${color};
    border-radius:10px;
    padding:16px 18px;
    position:relative;
    overflow:hidden;
  ">
    <div style="font-size:2rem;font-weight:900;color:${color};letter-spacing:-1px;line-height:1">${v}</div>
    <div style="font-size:.65rem;color:var(--text-dim);margin-top:5px;letter-spacing:.1em">${label}</div>
    <div style="position:absolute;right:12px;top:12px;font-size:1.4rem;opacity:.15">${icon}</div>
  </div>`;
}

function bsSelectBook(slug) {
  _bsSlug = slug;
  loadBookStudio();
}

// ── Главы ──────────────────────────────────────────────────────
async function loadBsChapters(slug) {
  const el = document.getElementById('bs-chapters');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.78rem">Загрузка глав...</div>';
  try {
    _bsChapters = await _bsFetch(`/bs/books/${slug}/chapters`);
    _bsRenderChapterList(slug);
  } catch (e) {
    el.innerHTML = `<div style="color:var(--red);font-size:.75rem">${e.message}</div>`;
  }
}

function _bsRenderChapterList(slug) {
  const s = slug || _bsSlug;
  const el = document.getElementById('bs-chapters');
  if (!el) return;
  const chs = _bsChapters;
  const scores = chs.map(c => c.score || 0);
  const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : '—';
  const trend = _scoreTrend(scores);
  const trendColor = trend === '↑' ? 'var(--green)' : trend === '↓' ? 'var(--red)' : 'var(--text-dim)';
  const sparkline = _sparkline(scores.slice(-10));
  const toPublish = chs.filter(c => !c.published && (c.score || 0) >= _BS_OK);
  const filtered = _bsApplyFilter(chs);
  const rows = [...filtered].reverse().map(c => _chapterRow(s, c)).join('');
  const filters = [
    ['all','Все'], ['pub','RULATE'], ['draft','Черн.'],
    ['good','≥7.5'], ['ok','6.5–7.5']
  ].map(([f, lbl]) =>
    `<button class="wyrd-btn wyrd-btn-sm${_bsFilter === f ? '' : ' wyrd-btn-ghost'}" onclick="bsSetFilter('${f}')" style="padding:3px 8px">${lbl}</button>`
  ).join('');
  el.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:6px">
      <div>
        <span style="font-size:.7rem;color:var(--text-dim);letter-spacing:.08em">ГЛАВЫ</span>
        <span style="font-size:.75rem;color:var(--text);margin-left:8px"><b style="color:var(--amber)">${chs.length}</b> шт</span>
        <span style="font-size:.75rem;color:var(--text-dim);margin-left:8px">ср. <b style="color:var(--amber)">${avg}</b>/10</span>
        <span style="font-size:.9rem;color:${trendColor};margin-left:8px;font-weight:700">${trend}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px">
        ${sparkline}
        <button class="wyrd-btn wyrd-btn-sm" onclick="bsGenerate('${s}')">＋ Глава</button>
        ${toPublish.length ? `<button class="wyrd-btn wyrd-btn-sm" onclick="bsPublishAll('${s}')" title="${toPublish.length} глав ≥${_BS_OK}">📤 Все (${toPublish.length})</button>` : ''}
      </div>
    </div>
    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:8px">${filters}</div>
    ${filtered.length < chs.length ? `<div style="font-size:.65rem;color:var(--text-dim);margin-bottom:6px">${filtered.length} из ${chs.length}</div>` : ''}
    <div style="max-height:320px;overflow-y:auto;margin:0 -14px;padding:0 14px">${rows}</div>`;
}

function _bsApplyFilter(chs) {
  if (_bsFilter === 'pub') return chs.filter(c => c.published);
  if (_bsFilter === 'draft') return chs.filter(c => !c.published);
  if (_bsFilter === 'good') return chs.filter(c => (c.score || 0) >= _BS_GOOD);
  if (_bsFilter === 'ok') return chs.filter(c => (c.score || 0) >= _BS_OK && (c.score || 0) < _BS_GOOD);
  return chs;
}

function bsSetFilter(f) {
  _bsFilter = f;
  _bsRenderChapterList();
}

function _chapterRow(slug, c) {
  const sc = c.score || 0;
  const col = _scoreColor(sc);
  const pubBadge = c.published
    ? `<span style="font-size:.6rem;background:rgba(74,255,136,.12);color:var(--green);border-radius:4px;padding:1px 5px">RULATE</span>`
    : `<span style="font-size:.6rem;background:rgba(255,255,255,.06);color:var(--text-dim);border-radius:4px;padding:1px 5px">черн.</span>`;
  return `
    <div class="bs-ch-row" onclick="openBsChapter('${slug}',${c.number})"
      style="display:flex;align-items:center;gap:10px;padding:9px 10px;margin:0 -10px;
             border-radius:8px;cursor:pointer;transition:background .15s;border-bottom:1px solid rgba(255,255,255,.04)"
      onmouseenter="this.style.background='rgba(255,255,255,.06)'"
      onmouseleave="this.style.background='transparent'">
      <div style="min-width:28px;height:28px;border-radius:6px;background:rgba(255,255,255,.07);
                  display:flex;align-items:center;justify-content:center;
                  font-size:.65rem;color:var(--text-dim);font-weight:700;flex-shrink:0">${c.number}</div>
      <div style="flex:1;min-width:0">
        <div style="font-size:.78rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px">${c.title}</div>
        <div style="display:flex;align-items:center;gap:8px">
          ${_scoreBar(sc)}
          ${pubBadge}
        </div>
      </div>
      <div style="text-align:right;flex-shrink:0;display:flex;align-items:center;gap:6px">
        <div style="font-size:.9rem;font-weight:800;color:${col}">${sc.toFixed(1)}</div>
        <div style="color:var(--text-dim);font-size:.75rem;opacity:.5">›</div>
      </div>
    </div>`;
}

function _scoreBar(s) {
  const w = Math.min(100, Math.round(s * 10));
  const col = _scoreColor(s);
  return `<div style="flex:1;background:rgba(255,255,255,.08);border-radius:4px;height:6px;max-width:120px">
    <div style="width:${w}%;height:100%;background:${col};border-radius:4px;
                box-shadow:0 0 6px ${col}66;transition:width .3s"></div></div>`;
}

function _scoreColor(s) {
  return s >= _BS_GOOD ? 'var(--green)' : s >= _BS_OK ? 'var(--amber)' : 'var(--red)';
}

function _scoreTrend(scores) {
  if (scores.length < 3) return '—';
  const last = scores.slice(-3);
  const d = last[2] - last[0];
  return d > 0.3 ? '↑' : d < -0.3 ? '↓' : '→';
}

function _sparkline(scores) {
  if (scores.length < 2) return '';
  const W = 60, H = 20, pad = 2;
  const min = Math.min(...scores), max = Math.max(...scores);
  const range = max - min || 1;
  const pts = scores.map((s, i) => {
    const x = pad + (i / (scores.length - 1)) * (W - pad * 2);
    const y = H - pad - ((s - min) / range) * (H - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const last = scores[scores.length - 1];
  const col = _scoreColor(last);
  return `<svg width="${W}" height="${H}" style="opacity:.7;vertical-align:middle">
    <polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2.5" fill="${col}"/>
  </svg>`;
}

// ── Просмотр главы ─────────────────────────────────────────────
async function openBsChapter(slug, num) {
  let ov = document.getElementById('bs-ch-ov');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'bs-ch-ov';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:8000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
    ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = '<div style="color:var(--text-dim)">Загрузка...</div>';
  ov.style.display = 'flex';
  try {
    const ch = await _bsFetch(`/bs/books/${slug}/chapters/${num}`);
    const sc = ch.score || 0;
    const pubBtn = !ch.published
      ? `<div style="padding:12px 20px;border-top:1px solid var(--border)">
           <button class="wyrd-btn wyrd-btn-sm" onclick="bsPublish('${slug}',${ch.number})">📤 Опубликовать на Rulate</button>
         </div>` : '';
    ov.innerHTML = `
      <div style="width:min(740px,96vw);max-height:90vh;background:#0d1117;border:1px solid var(--border);border-radius:14px;display:flex;flex-direction:column;box-shadow:0 24px 60px rgba(0,0,0,.6)">
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
            <div style="font-size:.7rem;color:${ch.published ? 'var(--green)' : 'var(--text-dim)'}">
              ${ch.published ? '✅ на Rulate' : '⬜ черновик'}
            </div>
            <button onclick="document.getElementById('bs-ch-ov').remove()"
              style="background:none;border:1px solid var(--border);color:var(--text-dim);border-radius:8px;padding:5px 12px;cursor:pointer;font-size:.85rem;transition:all .15s"
              onmouseenter="this.style.borderColor='var(--text)';this.style.color='var(--text)'"
              onmouseleave="this.style.borderColor='var(--border)';this.style.color='var(--text-dim)'">✕</button>
          </div>
        </div>
        <div style="overflow-y:auto;padding:20px 24px;font-size:.85rem;line-height:2;color:var(--text);white-space:pre-wrap">${ch.content || ''}</div>
        ${pubBtn}
      </div>`;
  } catch (e) {
    ov.innerHTML = `<div style="color:var(--red);padding:20px">${e.message}</div>`;
  }
}

// ── Арка ───────────────────────────────────────────────────────
const _ARC_COLORS = {
  'открытие': '#60a5fa', 'конфликт': 'var(--red)', 'поворот': 'var(--purple)',
  'пик': 'var(--amber)', 'развязка': 'var(--green)', 'setup': '#60a5fa'
};

async function loadBsArc(slug) {
  const el = document.getElementById('bs-arc');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.78rem">Загрузка арки...</div>';
  try {
    const arc = await _bsFetch(`/bs/books/${slug}/arc`);
    const goals = arc.chapter_goals || [];
    const written = _bsChapters.length;
    const arcTotal = goals.length;
    const pct = arcTotal ? Math.min(100, Math.round(written / arcTotal * 100)) : 0;
    const progressBar = arcTotal ? `
      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <span style="font-size:.62rem;color:var(--text-dim);letter-spacing:.06em">ПРОГРЕСС АРКИ</span>
          <span style="font-size:.65rem;color:var(--amber);font-weight:700">${written}/${arcTotal} · ${pct}%</span>
        </div>
        <div style="background:rgba(255,255,255,.08);border-radius:4px;height:8px">
          <div style="width:${pct}%;height:100%;background:var(--amber);border-radius:4px;transition:width .5s;box-shadow:0 0 8px rgba(255,176,32,.4)"></div>
        </div>
      </div>` : '';
    const rows = goals.slice(0, 12).map(g => {
      const fn = (g.arc_function || '').toLowerCase();
      const col = _ARC_COLORS[fn] || 'var(--text-dim)';
      return `
        <div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.04);align-items:flex-start">
          <div style="min-width:30px;height:20px;border-radius:4px;background:${col}22;border:1px solid ${col}44;
                      display:flex;align-items:center;justify-content:center;
                      font-size:.6rem;color:${col};font-weight:700;flex-shrink:0;margin-top:1px">${g.number}</div>
          <div style="font-size:.74rem;color:var(--text);line-height:1.55;flex:1">${g.goal || ''}</div>
          ${fn ? `<div style="font-size:.6rem;color:${col};flex-shrink:0;margin-top:2px;text-transform:uppercase;letter-spacing:.05em">${fn}</div>` : ''}
        </div>`;
    }).join('');
    const more = goals.length > 12 ? `<div style="font-size:.68rem;color:var(--text-dim);margin-top:8px;padding-top:6px;border-top:1px solid var(--border)">+ ещё ${goals.length - 12} глав в арке</div>` : '';
    el.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div>
          <span style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em">📐 АРКА: ${arc.arc_name || 'Арка 1'}</span>
          <span style="margin-left:8px;font-size:.72rem;color:var(--amber);font-weight:700">${goals.length} глав</span>
        </div>
      </div>
      ${progressBar}
      <div style="font-size:.73rem;color:var(--text-dim);margin-bottom:12px;line-height:1.55;padding:8px 10px;background:rgba(255,255,255,.03);border-radius:6px;border-left:2px solid var(--amber)">${arc.arc_summary || ''}</div>
      <div>${rows}</div>${more}`;
  } catch (e) {
    const el2 = document.getElementById('bs-arc');
    if (el2) el2.innerHTML = `
      <div style="font-size:.75rem;color:var(--text-dim)">Арка не построена.</div>
      <button class="wyrd-btn wyrd-btn-sm" style="margin-top:8px" onclick="bsBuildArc('${slug}')">📐 Построить арку</button>`;
  }
}

async function bsBuildArc(slug) {
  const el = document.getElementById('bs-arc');
  if (el) el.innerHTML = '<div style="color:var(--text-dim);font-size:.78rem">Строим арку... (~30 сек)</div>';
  try {
    await fetch(`/bs/books/${slug}/arc`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({book_slug: slug, arc_number: 1, chapters_count: 20})
    });
    await loadBsArc(slug);
  } catch (e) {
    if (el) el.innerHTML = `<div style="color:var(--red);font-size:.75rem">${e.message}</div>`;
  }
}

// ── Разведка + Следующая книга ─────────────────────────────────
function _renderBsScout(scout) {
  const el = document.getElementById('bs-scout');
  if (!el || !scout) return;
  const chip = (text, col) => `<span style="display:inline-block;background:${col}22;color:${col};border:1px solid ${col}44;border-radius:4px;padding:2px 8px;font-size:.65rem;margin:2px">${text}</span>`;
  el.innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:10px">🔭 РАЗВЕДКА РЫНКА</div>
    <div style="margin-bottom:6px">
      <div style="font-size:.65rem;color:var(--text-dim);margin-bottom:4px">ТРЕНДЫ</div>
      ${(scout.trending_genres || []).map(g => chip(g, 'var(--green)')).join('') || '<span style="color:var(--text-dim);font-size:.72rem">—</span>'}
    </div>
    <div style="margin-bottom:6px">
      <div style="font-size:.65rem;color:var(--text-dim);margin-bottom:4px">МЕХАНИКИ</div>
      ${(scout.top_mechanics || []).map(m => chip(m, 'var(--purple)')).join('') || '<span style="color:var(--text-dim);font-size:.72rem">—</span>'}
    </div>
    <div style="margin-bottom:12px">
      <div style="font-size:.65rem;color:var(--text-dim);margin-bottom:4px">ИЗБЕГАТЬ</div>
      ${(scout.avoid || []).map(a => chip(a, 'var(--red)')).join('') || '<span style="color:var(--text-dim);font-size:.72rem">—</span>'}
    </div>
    <button class="wyrd-btn wyrd-btn-sm" style="width:100%" onclick="loadBsNextBook('${_bsSlug}')">🧠 Предложить следующую книгу</button>
    <div id="bs-next-book" style="margin-top:12px"></div>`;
}

async function loadBsNextBook(slug) {
  const el = document.getElementById('bs-next-book');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.78rem">Анализирую рынок... (~20 сек)</div>';
  try {
    const d = await fetch(`/bs/books/${slug || _bsSlug}/next-book`, {method: 'POST'}).then(r => r.json());
    const ideas = d.ideas || [];
    if (!ideas.length) {
      el.innerHTML = `<div style="color:var(--text-dim);font-size:.75rem">${d.error || 'Идеи не получены'}</div>`;
      return;
    }
    el.innerHTML = `
      <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:8px">💡 КОНЦЕПЦИИ СЛЕДУЮЩЕЙ КНИГИ</div>
      ${ideas.map((idea, i) => `
        <div style="background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin-bottom:8px;
                    transition:border-color .15s;cursor:default"
             onmouseenter="this.style.borderColor='var(--amber)'" onmouseleave="this.style.borderColor='var(--border)'">
          <div style="font-size:.78rem;font-weight:700;color:var(--amber);margin-bottom:5px">${i + 1}. ${idea.title || 'Идея'}</div>
          <div style="font-size:.74rem;color:var(--text);line-height:1.6;margin-bottom:5px">${idea.hook || ''}</div>
          ${idea.why_it_works ? `<div style="font-size:.68rem;color:var(--green)">✓ ${idea.why_it_works}</div>` : ''}
        </div>`).join('')}`;
  } catch (e) {
    el.innerHTML = `<div style="color:var(--red);font-size:.75rem">${e.message}</div>`;
  }
}

// ── Публикация всех ────────────────────────────────────────────
async function bsPublishAll(slug) {
  const s = slug || _bsSlug;
  const toPublish = _bsChapters
    .filter(c => !c.published && (c.score || 0) >= _BS_OK)
    .sort((a, b) => a.number - b.number);
  if (!toPublish.length) { showToast('Нет глав для публикации'); return; }
  if (!confirm(`Опубликовать ${toPublish.length} глав (score ≥ ${_BS_OK})?`)) return;
  let ok = 0, err = 0;
  for (const c of toPublish) {
    try {
      const r = await fetch(`/bs/books/${s}/publish/${c.number}`, {method: 'POST'});
      const d = await r.json();
      if (d.ok) ok++; else err++;
    } catch { err++; }
    await new Promise(res => setTimeout(res, 600));
  }
  showToast(`✅ Опубликовано: ${ok}${err ? ' | ❌ Ошибок: ' + err : ''}`);
  await loadBsChapters(s);
}

// ── Генерация ──────────────────────────────────────────────────
async function bsGenerate(slug) {
  const s = slug || _bsSlug;
  try {
    const r = await fetch(`/bs/books/${s}/generate`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({book_slug: s, target_words: 2000})
    });
    const d = await r.json();
    showToast(d.ok ? `✅ Глава ${d.queued_chapter} в очереди` : '❌ Ошибка');
    if (d.ok) setTimeout(() => loadBsChapters(s), 3000);
  } catch (e) {
    showToast('❌ ' + e.message);
  }
}

// ── Публикация ─────────────────────────────────────────────────
async function bsPublish(slug, num) {
  if (!confirm(`Опубликовать главу ${num} на Rulate?`)) return;
  try {
    const r = await fetch(`/bs/books/${slug}/publish/${num}`, {method: 'POST'});
    const d = await r.json();
    showToast(d.ok ? `✅ Глава ${num} отправлена на Rulate` : '❌ Ошибка публикации');
    document.getElementById('bs-ch-ov')?.remove();
    if (d.ok) setTimeout(() => loadBsChapters(slug), 2000);
  } catch (e) {
    showToast('❌ ' + e.message);
  }
}
