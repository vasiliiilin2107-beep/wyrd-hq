/* ─── BUILD TAB ──────────────────────────────────────────── */

const BUILD_STATUS = {
  waiting:     { label: '🔴 ЖДЁТ',     color: '#ef4444' },
  in_progress: { label: '🟡 В РАБОТЕ', color: '#f59e0b' },
  done:        { label: '🟢 ГОТОВО',   color: '#10b981' },
};

const buildExpanded = new Set();

async function loadBuild() {
  const el = document.getElementById('build-list');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Загрузка...</div>';
  try {
    const data = await fetch('/build/queue').then(r => r.json());
    renderBuildQueue(data.cards || []);
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
  loadForemanReports();
}

// ─── БРИГАДИР ────────────────────────────────────────────

const foremanExpanded = new Set();

async function loadForemanReports() {
  const el = document.getElementById('foreman-list');
  if (!el) return;
  try {
    const data = await fetch('/build/foreman').then(r => r.json());
    renderForemanReports(data.reports || []);
  } catch { /* silent */ }
}

function renderForemanReports(reports) {
  const el = document.getElementById('foreman-list');
  const hdr = document.getElementById('foreman-hdr-count');
  if (!el) return;
  if (hdr) hdr.textContent = reports.length ? `(${reports.length})` : '';
  if (!reports.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Отчётов пока нет — Бригадир проверяет каждые 30 мин</div>';
    return;
  }
  el.innerHTML = '';
  reports.forEach(r => el.appendChild(mkForemanCard(r)));
}

function mkForemanCard(r) {
  const isOpen = foremanExpanded.has(r.id);
  const time = new Date(r.checked_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  const hasProblems = r.stuck_count > 0;
  const el = document.createElement('div');
  el.className = 'build-card';
  el.innerHTML = `
    <div class="build-card-hdr" onclick="foremanToggle(${r.id})">
      <span class="build-badge" style="color:${hasProblems ? '#f59e0b' : '#10b981'};border-color:${hasProblems ? '#f59e0b40' : '#10b98140'}">
        ${hasProblems ? `⚠️ ${r.stuck_count} застряло` : '✅ Всё чисто'}
      </span>
      <span class="build-time">${time}</span>
      <span style="font-size:.55rem;color:var(--text-dim);margin-left:4px">${r.task_ids?.length ? `задачи: #${r.task_ids.join(' #')}` : ''}</span>
      <span class="build-arr">${isOpen ? '▲' : '▼'}</span>
    </div>
    <div class="build-body" style="display:${isOpen ? 'flex' : 'none'}">
      <div class="build-lbl">АНАЛИЗ БРИГАДИРА</div>
      <div class="build-txt">${escHtml(r.analysis)}</div>
    </div>
  `;
  return el;
}

function foremanToggle(id) {
  if (foremanExpanded.has(id)) foremanExpanded.delete(id);
  else foremanExpanded.add(id);
  loadForemanReports();
}

function renderBuildQueue(cards) {
  const el = document.getElementById('build-list');
  const cntEl = document.getElementById('build-count');
  if (!el) return;

  const waiting = cards.filter(c => c.status === 'waiting').length;
  const inProg  = cards.filter(c => c.status === 'in_progress').length;
  if (cntEl) cntEl.textContent = `(${waiting} ждёт · ${inProg} в работе)`;

  if (!cards.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Совет ещё не вынес вердиктов</div>';
    return;
  }
  el.innerHTML = '';
  cards.forEach(c => el.appendChild(mkBuildCard(c)));
}

function mkBuildCard(c) {
  const st = BUILD_STATUS[c.status] || { label: c.status, color: '#6b7280' };
  const isOpen = buildExpanded.has(c.id);
  const time = c.created_at
    ? new Date(c.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '';
  const doneTime = c.completed_at
    ? new Date(c.completed_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '';

  const el = document.createElement('div');
  el.className = 'build-card' + (c.status === 'done' ? ' build-card-done' : '');
  el.dataset.id = c.id;
  el.innerHTML = `
    <div class="build-card-hdr" onclick="buildToggle(${c.id})">
      <span class="build-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
      <span class="build-topic">${escHtml(c.topic)}</span>
      <span class="build-time">${time}</span>
      <span class="build-arr">${isOpen ? '▲' : '▼'}</span>
    </div>
    <div class="build-body" style="display:${isOpen ? 'flex' : 'none'}">
      ${c.summary ? `
        <div class="build-lbl">ВЕРДИКТ КАРТОГРАФА</div>
        <div class="build-txt">${escHtml(c.summary)}</div>
      ` : ''}
      ${c.tz_text ? `
        <div class="build-lbl" style="margin-top:10px">ТЗ АРХИТЕКТОРА</div>
        <div class="build-txt">${escHtml(c.tz_text)}</div>
      ` : ''}
      ${doneTime ? `<div class="build-done-ts">✅ Завершено: ${doneTime}</div>` : ''}
      <div class="build-actions">
        ${c.status !== 'waiting'     ? `<button class="build-btn" onclick="setBuildStatus(${c.id},'waiting')">🔴 ЖДЁТ</button>` : ''}
        ${c.status !== 'in_progress' ? `<button class="build-btn" onclick="setBuildStatus(${c.id},'in_progress')">🟡 В РАБОТЕ</button>` : ''}
        ${c.status !== 'done'        ? `<button class="build-btn build-btn-ok" onclick="setBuildStatus(${c.id},'done')">🟢 ГОТОВО</button>` : ''}
      </div>
    </div>
  `;
  return el;
}

function buildToggle(id) {
  if (buildExpanded.has(id)) buildExpanded.delete(id);
  else buildExpanded.add(id);
  loadBuild();
}

async function setBuildStatus(id, status) {
  try {
    await fetch(`/build/queue/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    buildExpanded.add(id);
    loadBuild();
  } catch { /* silent */ }
}
