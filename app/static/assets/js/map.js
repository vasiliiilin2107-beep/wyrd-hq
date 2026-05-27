/* ─── WORLD MAP — 7 LAYERS ───────────────────────────── */

const MAP_LAYERS = [
  {id:'cosmos',     name:'ЗАМЫСЕЛ',    icon:'🌌', color:'#a855f7', comp:'global',
   desc:'Цели · Идеи · Стратегия',       types:['idea','beacon','note']},
  {id:'hq',         name:'ШТАБ',       icon:'🏛️', color:'#f59e0b', comp:'hq',
   desc:'PostgreSQL · Redis · Qdrant · FastAPI'},
  {id:'thomas',     name:'ТОМАС',      icon:'👁️', color:'#3b82f6', comp:'thomas',
   desc:'Telegram · Память · Патруль · Техник'},
  {id:'studio',     name:'СТУДИЯ',     icon:'🎬', color:'#8b5cf6', comp:'studio',
   desc:'Боря · Пайплайны · Видео · kie.ai'},
  {id:'library',    name:'БИБЛИОТЕКА', icon:'📚', color:'#10b981', comp:'library',
   desc:'RAG · Векторная база · Курьер'},
  {id:'quarantine', name:'КАРАНТИН',   icon:'🛡️', color:'#06b6d4', comp:'quarantine',
   desc:'Изоляция · Маяк · Угрозы · Репутация'},
  {id:'infra',      name:'ИНФРА',      icon:'🌀', color:'#64748b', comp:'global',
   desc:'VPS · Docker · Coolify · SSH',  types:['anchor','dependency']},
];

const FLAG_IC  = {anchor:'⚓',beacon:'📡',dependency:'🔗',idea:'💡',todo:'📋',risk:'⚠️',note:'📝'};
const FLAG_COL = {anchor:'#f59e0b',beacon:'#3b82f6',dependency:'#64748b',
                  idea:'#a855f7',todo:'#6366f1',risk:'#ef4444',note:'#94a3b8'};

const INFRA_NODES = [
  {label:'POSTGRESQL', ic:'🗄️', col:'#10b981'},
  {label:'REDIS',      ic:'⚡',  col:'#ef4444'},
  {label:'QDRANT',     ic:'🔮', col:'#06b6d4'},
  {label:'VPS 147.45.212.155', ic:'🖥️', col:'#64748b'},
  {label:'COOLIFY',    ic:'🚀', col:'#f59e0b'},
];

let _mapBr   = [];
let _mapFl   = {};
let _mapOpen = new Set(['hq']);
let _mapOK   = false;

/* ─── INIT ────────────────────────────────────────────── */
async function initMap() {
  const el = document.getElementById('world-map');
  if (!el) return;
  if (!_mapOK) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:20px 0">Загрузка карты...</div>';
    try {
      const [b, f] = await Promise.all([
        fetch('/branches').then(r => r.json()).catch(() => []),
        fetch('/flags?limit=200').then(r => r.json()).catch(() => []),
      ]);
      _mapBr = Array.isArray(b) ? b : (b.branches || []);
      (Array.isArray(f) ? f : []).forEach(fg => {
        (_mapFl[fg.component] = _mapFl[fg.component] || []).push(fg);
      });
      _mapOK = true;
    } catch {
      el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:20px 0">Ошибка загрузки</div>';
      return;
    }
  }
  _drawMap(el);
}

async function refreshMap() {
  _mapOK = false; _mapFl = {}; _mapBr = [];
  await initMap();
}

/* ─── RENDER ──────────────────────────────────────────── */
function _drawMap(el) {
  const rows = MAP_LAYERS.map((L, i) => {
    let flags = (_mapFl[L.comp] || []).slice();
    if (L.types) flags = flags.filter(f => L.types.includes(f.type));

    const br = _mapBr.find(b => {
      const n = (b.name || '').toLowerCase();
      return n.includes(L.id) || (L.id === 'hq' && (n.includes('wyrd-hq') || n === 'hq'));
    });
    const open = _mapOpen.has(L.id);
    const fc   = flags.length;
    const conn = i < MAP_LAYERS.length - 1
      ? `<div class="wmc"><div class="wmc-l" style="border-color:${L.color}55"></div></div>` : '';

    return `
<div class="wml" id="wml-${L.id}" style="--lc:${L.color}">
  <div class="wml-h" data-lid="${L.id}">
    <div class="wml-left">
      <span class="wml-ic">${L.icon}</span>
      <div>
        <div class="wml-name" style="color:${L.color}">${L.name}</div>
        <div class="wml-sub">${L.desc}</div>
      </div>
    </div>
    <div class="wml-right">
      ${br ? `<span class="wml-tag" style="color:#10b981;border-color:#10b98155">● ${br.status||'online'}</span>` : ''}
      ${fc  ? `<span class="wml-tag" style="color:${L.color};border-color:${L.color}55">${fc} ${fc===1?'флаг':'флагов'}</span>` : ''}
      <span class="wml-arr">${open ? '▲' : '▼'}</span>
    </div>
  </div>
  <div class="wml-body"${open ? '' : ' style="display:none"'}>
    ${_flagsHtml(flags, L)}
    <div class="wml-addf" id="wml-addf-${L.id}" style="display:none">
      <select class="wml-sel" id="wml-ft-${L.id}">
        ${Object.entries(FLAG_IC).map(([k,v]) => `<option value="${k}">${v} ${k}</option>`).join('')}
      </select>
      <input class="wml-fin" id="wml-fi-${L.id}" placeholder="Название флага..."
             data-lid="${L.id}" data-comp="${L.comp}">
      <button class="wml-fbtn wml-fbtn-ok"  data-lid="${L.id}" data-comp="${L.comp}">+</button>
      <button class="wml-fbtn wml-fbtn-no"  data-lid="${L.id}">×</button>
    </div>
    <button class="wml-plus" data-lid="${L.id}">+ флаг</button>
  </div>
</div>${conn}`;
  }).join('');

  el.innerHTML = `
<div class="wmap-hdr">
  <span class="wmap-title">КАРТА МИРА · 7 СЛОЁВ</span>
  <button id="wmap-refresh-btn" class="wmap-refresh">↻</button>
</div>
<div class="wmap">${rows}</div>`;

  /* Enter/Esc на полях ввода */
  el.querySelectorAll('.wml-fin').forEach(inp => {
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter')  submitMapFlag(inp.dataset.lid, inp.dataset.comp);
      if (e.key === 'Escape') cancelMapFlag(inp.dataset.lid);
    });
  });
}

function _flagsHtml(flags, L) {
  let html = '';
  if (L.id === 'infra') {
    html += INFRA_NODES.map(n =>
      `<div class="wml-flag wml-flag-static">
        <span style="color:${n.col}">${n.ic}</span>
        <span class="wml-ft">${n.label}</span>
        <span style="color:#10b981;font-size:.5rem;margin-left:2px">●</span>
      </div>`
    ).join('');
  }
  if (!flags.length) {
    if (L.id !== 'infra') html += '<div class="wml-nf">Нет активных флагов</div>';
    return html;
  }
  html += flags.map(f => {
    const ic   = FLAG_IC[f.type]  || '📌';
    const col  = FLAG_COL[f.type] || '#94a3b8';
    const body = f.body ? f.body.replace(/&/g,'&amp;').replace(/"/g,'&quot;') : '';
    return `<div class="wml-flag" data-id="${f.id}" data-comp="${L.comp}" data-body="${body}">
      <span style="color:${col}">${ic}</span>
      <span class="wml-ft">${escHtml(f.title)}</span>
      ${f.body ? '<span class="wml-fexp">▸</span>' : ''}
      <button class="wml-fdel" data-id="${f.id}" data-comp="${L.comp}">×</button>
    </div>`;
  }).join('');
  return html;
}

/* ─── ACTIONS ─────────────────────────────────────────── */
function toggleMapLayer(id) {
  if (_mapOpen.has(id)) _mapOpen.delete(id); else _mapOpen.add(id);
  const el = document.getElementById('world-map');
  if (el) _drawMap(el);
}

function showMapFlagForm(lid) {
  const f   = document.getElementById(`wml-addf-${lid}`);
  const btn = document.querySelector(`.wml-plus[data-lid="${lid}"]`);
  if (f)   f.style.display = 'flex';
  if (btn) btn.style.display = 'none';
  const inp = document.getElementById(`wml-fi-${lid}`);
  if (inp) inp.focus();
}

function cancelMapFlag(lid) {
  const f   = document.getElementById(`wml-addf-${lid}`);
  const btn = document.querySelector(`.wml-plus[data-lid="${lid}"]`);
  if (f)   f.style.display = 'none';
  if (btn) btn.style.display = '';
}

async function submitMapFlag(lid, comp) {
  const inp   = document.getElementById(`wml-fi-${lid}`);
  const sel   = document.getElementById(`wml-ft-${lid}`);
  const title = inp ? inp.value.trim() : '';
  const type  = sel ? sel.value : 'note';
  if (!title) return;
  try {
    const r = await fetch('/flags', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({title, type, component: comp, author: 'moz'}),
    });
    if (r.ok) {
      const f = await r.json();
      (_mapFl[comp] = _mapFl[comp] || []).unshift(f);
      const el = document.getElementById('world-map');
      if (el) _drawMap(el);
    }
  } catch { /* silent */ }
}

async function archiveMapFlag(id, comp) {
  try {
    await fetch(`/flags/${id}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: 'done'}),
    });
    if (_mapFl[comp]) _mapFl[comp] = _mapFl[comp].filter(f => f.id !== id);
    const el = document.getElementById('world-map');
    if (el) _drawMap(el);
  } catch { /* silent */ }
}

function toggleFlagBody(flagEl) {
  const body = flagEl.dataset.body;
  if (!body) return;
  let bd  = flagEl.querySelector('.wml-flag-bd');
  const exp = flagEl.querySelector('.wml-fexp');
  if (!bd) {
    bd = document.createElement('div');
    bd.className = 'wml-flag-bd';
    bd.textContent = body.replace(/&amp;/g,'&').replace(/&quot;/g,'"');
    flagEl.insertBefore(bd, flagEl.querySelector('.wml-fdel'));
    if (exp) exp.textContent = '▾';
  } else {
    bd.remove();
    if (exp) exp.textContent = '▸';
  }
}

/* ─── EVENT DELEGATION ────────────────────────────────── */
document.addEventListener('click', function(e) {
  /* Обновить карту */
  if (e.target.closest('#wmap-refresh-btn')) { refreshMap(); return; }

  /* Удалить флаг */
  const del = e.target.closest('.wml-fdel');
  if (del) { archiveMapFlag(+del.dataset.id, del.dataset.comp); return; }

  /* Подтвердить добавление */
  const ok = e.target.closest('.wml-fbtn-ok');
  if (ok) { submitMapFlag(ok.dataset.lid, ok.dataset.comp); return; }

  /* Отменить добавление */
  const no = e.target.closest('.wml-fbtn-no');
  if (no) { cancelMapFlag(no.dataset.lid); return; }

  /* Кнопка + флаг */
  const plus = e.target.closest('.wml-plus');
  if (plus) { showMapFlagForm(plus.dataset.lid); return; }

  /* Клик по флагу — показать/скрыть тело */
  const flag = e.target.closest('.wml-flag:not(.wml-flag-static)');
  if (flag) { toggleFlagBody(flag); return; }

  /* Заголовок слоя — свернуть/развернуть */
  const head = e.target.closest('.wml-h');
  if (head && head.dataset.lid) { toggleMapLayer(head.dataset.lid); return; }
});
