/* WYRD Book Studio — Dashboard JS */

let _bsSlug = null;
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
    _bsCard(d.total_chapters || 0, 'НАПИСАНО', 'var(--amber)') +
    _bsCard(d.total_published || 0, 'НА RULATE', 'var(--green)') +
    _bsCard(books.length, 'КНИГ', 'var(--purple)') +
    _bsCard(avg, 'СР. ОЦЕНКА', '#60a5fa');

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
function _bsCard(v, label, color) {
  return `<div class="stat-card" style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px">
    <div style="font-size:1.5rem;font-weight:800;color:${color}">${v}</div>
    <div style="font-size:.68rem;color:var(--text-dim);margin-top:2px">${label}</div></div>`;
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
    const chs = await _bsFetch(`/bs/books/${slug}/chapters`);
    const scores = chs.map(c => c.score || 0);
    const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : '—';
    const trend = _scoreTrend(scores);
    const rows = [...chs].reverse().map(c => `
      <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer"
        onclick="openBsChapter('${slug}',${c.number})">
        <span style="font-size:.68rem;color:var(--text-dim);min-width:22px">#${c.number}</span>
        <div style="flex:1;min-width:0">
          <div style="font-size:.74rem;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${c.title}</div>
          <div style="margin-top:3px">${_scoreBar(c.score || 0)}</div>
        </div>
        <div style="text-align:right;min-width:46px;flex-shrink:0">
          <div style="font-size:.78rem;font-weight:700;color:${_scoreColor(c.score||0)}">${(c.score||0).toFixed(1)}</div>
          <div style="font-size:.6rem;color:var(--text-dim)">${c.published ? '✅' : '⬜'}</div>
        </div>
      </div>`).join('');
    el.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:6px">
        <span style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em">
          ГЛАВЫ · ${chs.length} шт · ср. <b style="color:var(--amber)">${avg}</b>/10 · тренд ${trend}
        </span>
        <button class="wyrd-btn wyrd-btn-sm" onclick="bsGenerate('${slug}')">＋ Глава</button>
      </div>
      <div style="max-height:340px;overflow-y:auto">${rows}</div>`;
  } catch (e) {
    el.innerHTML = `<div style="color:var(--red);font-size:.75rem">${e.message}</div>`;
  }
}

function _scoreBar(s) {
  const w = Math.min(100, Math.round(s * 10));
  return `<div style="background:rgba(255,255,255,.08);border-radius:3px;height:4px">
    <div style="width:${w}%;height:100%;background:${_scoreColor(s)};border-radius:3px"></div></div>`;
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

// ── Просмотр главы ─────────────────────────────────────────────
async function openBsChapter(slug, num) {
  let ov = document.getElementById('bs-ch-ov');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'bs-ch-ov';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.72);z-index:8000;display:flex;align-items:center;justify-content:center';
    ov.addEventListener('click', e => { if (e.target === ov) ov.remove(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = '<div style="color:var(--text-dim)">Загрузка...</div>';
  ov.style.display = 'flex';
  try {
    const ch = await _bsFetch(`/bs/books/${slug}/chapters/${num}`);
    const pubBtn = !ch.published
      ? `<div style="padding:12px 18px;border-top:1px solid var(--border)">
           <button class="wyrd-btn wyrd-btn-sm" onclick="bsPublish('${slug}',${ch.number})">📤 Опубликовать на Rulate</button>
         </div>` : '';
    ov.innerHTML = `
      <div style="width:min(720px,96vw);max-height:90vh;background:#0d1117;border:1px solid var(--border);border-radius:12px;display:flex;flex-direction:column">
        <div style="display:flex;align-items:center;justify-content:space-between;padding:13px 18px;border-bottom:1px solid var(--border)">
          <div>
            <span style="font-size:.85rem;font-weight:700">Гл.${ch.number}: ${ch.title}</span>
            <span style="margin-left:10px;font-size:.75rem;color:${_scoreColor(ch.score||0)}">${(ch.score||0).toFixed(1)}/10</span>
            <span style="margin-left:8px;font-size:.68rem;color:var(--text-dim)">${ch.published ? '✅ на Rulate' : '⬜ не опубл.'}</span>
          </div>
          <button onclick="document.getElementById('bs-ch-ov').remove()"
            style="background:none;border:1px solid var(--border);color:var(--text-dim);border-radius:6px;padding:3px 10px;cursor:pointer;font-size:.8rem">✕</button>
        </div>
        <div style="overflow-y:auto;padding:18px 20px;font-size:.82rem;line-height:1.85;color:var(--text);white-space:pre-wrap">${ch.content || ''}</div>
        ${pubBtn}
      </div>`;
  } catch (e) {
    ov.innerHTML = `<div style="color:var(--red);padding:20px">${e.message}</div>`;
  }
}

// ── Арка ───────────────────────────────────────────────────────
async function loadBsArc(slug) {
  const el = document.getElementById('bs-arc');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.78rem">Загрузка арки...</div>';
  try {
    const arc = await _bsFetch(`/bs/books/${slug}/arc`);
    const goals = arc.chapter_goals || [];
    const rows = goals.slice(0, 10).map(g => `
      <div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04)">
        <span style="font-size:.68rem;color:var(--text-dim);min-width:26px;flex-shrink:0">гл.${g.number}</span>
        <span style="font-size:.72rem;color:var(--text);line-height:1.5;flex:1">${g.goal || ''}</span>
        <span style="font-size:.62rem;color:var(--text-dim);flex-shrink:0">${g.arc_function || ''}</span>
      </div>`).join('');
    const more = goals.length > 10 ? `<div style="font-size:.68rem;color:var(--text-dim);margin-top:6px">+ ещё ${goals.length - 10} глав в арке</div>` : '';
    el.innerHTML = `
      <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:6px">
        📐 АРКА: ${arc.arc_name || 'Арка 1'}
        <span style="margin-left:8px;color:var(--amber)">${goals.length} глав</span>
      </div>
      <div style="font-size:.73rem;color:var(--text-dim);margin-bottom:10px;line-height:1.5">${arc.arc_summary || ''}</div>
      <div>${rows}</div>${more}`;
  } catch (e) {
    const slug2 = slug;
    const el2 = document.getElementById('bs-arc');
    if (el2) el2.innerHTML = `
      <div style="font-size:.75rem;color:var(--text-dim)">Арка не построена.</div>
      <button class="wyrd-btn wyrd-btn-sm" style="margin-top:8px" onclick="bsBuildArc('${slug2}')">📐 Построить арку</button>`;
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
  el.innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.08em;margin-bottom:8px">🔭 РАЗВЕДКА РЫНКА</div>
    <div style="font-size:.74rem;color:var(--text);line-height:1.75">
      <b>Тренды:</b> ${(scout.trending_genres || []).join(', ') || '—'}<br>
      <b>Механики:</b> ${(scout.top_mechanics || []).join(', ') || '—'}<br>
      <b>Избегать:</b> ${(scout.avoid || []).join(', ') || '—'}
    </div>
    <div style="margin-top:10px">
      <button class="wyrd-btn wyrd-btn-sm" onclick="loadBsNextBook('${_bsSlug}')">🧠 Предложить след. книгу</button>
    </div>
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
        <div style="background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:8px;padding:11px 13px;margin-bottom:8px">
          <div style="font-size:.78rem;font-weight:700;color:var(--amber);margin-bottom:4px">${i + 1}. ${idea.title || 'Идея'}</div>
          <div style="font-size:.73rem;color:var(--text);line-height:1.55;margin-bottom:4px">${idea.hook || ''}</div>
          ${idea.why_it_works ? `<div style="font-size:.68rem;color:var(--green)">✓ ${idea.why_it_works}</div>` : ''}
        </div>`).join('')}`;
  } catch (e) {
    el.innerHTML = `<div style="color:var(--red);font-size:.75rem">${e.message}</div>`;
  }
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
