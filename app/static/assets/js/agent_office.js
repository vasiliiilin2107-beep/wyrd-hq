/* WYRD Book Studio — Офис агентов: карточки агентов + живой лог запуска.
   Бэк: POST /bs/agent-run/{agent} → run_id → GET /agent-log/{run_id}/tail (поллинг 1.5 сек) */

const _BS_OFFICE_AGENTS = [
  {id: 'scout',     icon: '🔭', name: 'Разведчик',   desc: 'Топы и тренды 5 платформ', slug: false},
  {id: 'analyst',   icon: '💡', name: 'Аналитик',    desc: '3 идеи новых книг по рынку', slug: false},
  {id: 'conductor', icon: '🎯', name: 'Дирижёр',     desc: 'Анализ книги → директивы', slug: true},
  {id: 'school',    icon: '🎓', name: 'Школа',       desc: 'Разбор глав → правила агентам', slug: true},
  {id: 'readtops',  icon: '📖', name: 'Читка рынка', desc: 'Читатели читают топ-книги рынка', slug: false},
];

let _bsOfficeTimer = null;

function _bsOfficeBook() {
  if (_bsSlug) return _bsSlug;
  const b = _bsBooks.find(x => (x.chapters_total||0) > 0) || _bsBooks[0];
  return b ? b.slug : '';
}

function bsOpenOffice() {
  let ov = document.getElementById('bs-office-ov');
  if (ov) { ov.style.display = 'flex'; return; }
  ov = document.createElement('div');
  ov.id = 'bs-office-ov';
  ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:8000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)';
  ov.addEventListener('click', e => { if (e.target === ov) bsCloseOffice(); });

  const cards = _BS_OFFICE_AGENTS.map(a => `
    <div class="bs-office-agent" id="bs-oa-${a.id}">
      <div style="font-size:1.5rem;flex-shrink:0">${a.icon}</div>
      <div style="flex:1;min-width:0">
        <div style="font-size:.8rem;font-weight:700">${a.name}${a.slug ? ' <span style="font-size:.6rem;color:var(--text-secondary)">— по книге</span>' : ''}</div>
        <div style="font-size:.65rem;color:var(--text-secondary);line-height:1.4">${a.desc}</div>
      </div>
      <button class="wyrd-btn wyrd-btn-sm" id="bs-oa-btn-${a.id}" onclick="bsOfficeRun('${a.id}')">▶</button>
    </div>`).join('');

  ov.innerHTML = `
    <div style="width:min(920px,96vw);height:min(620px,92vh);background:var(--bg-base);border:1px solid var(--border-base);border-radius:var(--r-xl);display:flex;flex-direction:column;box-shadow:var(--shadow-md)">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border-dim)">
        <div>
          <span style="font-size:.85rem;font-weight:800">🏢 ОФИС АГЕНТОВ</span>
          <span style="margin-left:10px;font-size:.68rem;color:var(--text-secondary)">книга: <b style="color:var(--color-studio)">${_bsOfficeBook() || '—'}</b></span>
        </div>
        <button onclick="bsCloseOffice()" style="background:none;border:1px solid var(--border-base);color:var(--text-secondary);border-radius:var(--r-md);padding:5px 12px;cursor:pointer">✕</button>
      </div>
      <div style="flex:1;display:flex;min-height:0">
        <div style="width:280px;flex-shrink:0;border-right:1px solid var(--border-dim);overflow-y:auto;padding:10px">${cards}</div>
        <div style="flex:1;display:flex;flex-direction:column;min-width:0">
          <div class="stat-card-label" style="padding:10px 14px 4px">ЖИВОЙ ЛОГ</div>
          <div id="bs-office-log" style="flex:1;overflow-y:auto;padding:6px 14px 14px;font-family:ui-monospace,monospace;font-size:.68rem;line-height:1.8;color:var(--text-secondary)">
            <div style="opacity:.5">Выбери агента слева и жми ▶</div>
          </div>
        </div>
      </div>
    </div>`;
  document.body.appendChild(ov);
  _bsOfficeHistory();
}

function bsCloseOffice() {
  const ov = document.getElementById('bs-office-ov');
  if (ov) ov.style.display = 'none';
}

function _bsOfficeAppend(text, color) {
  const log = document.getElementById('bs-office-log');
  if (!log) return;
  const div = document.createElement('div');
  if (color) div.style.color = color;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function _bsOfficeHistory() {
  try {
    const d = await fetch('/agent-log/recent?limit=5').then(r => r.json());
    if (d.runs && d.runs.length) {
      _bsOfficeAppend('— последние запуски —');
      d.runs.forEach(r => _bsOfficeAppend(`${r.ok === false ? '✗' : r.done ? '✓' : '…'} ${r.title} (${r.lines_count} строк)`));
    }
  } catch (e) { /* журнал пуст после рестарта — норма */ }
}

async function bsOfficeRun(agentId) {
  const a = _BS_OFFICE_AGENTS.find(x => x.id === agentId);
  if (!a) return;
  const slug = a.slug ? _bsOfficeBook() : '';
  if (a.slug && !slug) { showToast('Нет книги для агента'); return; }
  const btn = document.getElementById(`bs-oa-btn-${agentId}`);
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  if (_bsOfficeTimer) { clearInterval(_bsOfficeTimer); _bsOfficeTimer = null; }

  _bsOfficeAppend('');
  _bsOfficeAppend(`▶ ${a.icon} ${a.name}${slug ? ' · ' + slug : ''}`, 'var(--color-studio)');
  try {
    const r = await fetch(`/bs/agent-run/${agentId}${slug ? '?slug=' + encodeURIComponent(slug) : ''}`, {method: 'POST'});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    let since = 0;
    _bsOfficeTimer = setInterval(async () => {
      try {
        const t = await fetch(`/agent-log/${d.run_id}/tail?since=${since}`).then(x => { if (!x.ok) throw new Error('HTTP ' + x.status); return x.json(); });
        t.lines.forEach(l => _bsOfficeAppend(`[${l.t}s] ${l.text}`, l.text.startsWith('✗') ? 'var(--status-dead)' : l.text.startsWith('✓') ? 'var(--status-alive)' : null));
        since = t.next;
        if (t.done) {
          clearInterval(_bsOfficeTimer); _bsOfficeTimer = null;
          if (btn) { btn.disabled = false; btn.textContent = '▶'; }
          if (agentId === 'analyst') { _bsIdeas = null; }
          if (agentId === 'conductor') { _bsConductor = null; }
        }
      } catch (e) {
        clearInterval(_bsOfficeTimer); _bsOfficeTimer = null;
        if (btn) { btn.disabled = false; btn.textContent = '▶'; }
        _bsOfficeAppend('✗ Лог оборвался: ' + e.message, 'var(--status-dead)');
      }
    }, 1500);
  } catch (e) {
    if (btn) { btn.disabled = false; btn.textContent = '▶'; }
    _bsOfficeAppend('✗ Не запустился: ' + e.message, 'var(--status-dead)');
  }
}
