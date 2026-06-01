/* ─── TECHNIK TAB ─────────────────────────────────────── */
const TECH_STATUS_LABELS = {
  pending:          { label: 'ЖДЁТ',    color: '#f59e0b' },
  running:          { label: 'РАБОТАЕТ',color: '#3b82f6' },
  waiting_approval: { label: 'ОДОБРИТЬ',color: '#8b5cf6' },
  done:             { label: 'ГОТОВО',  color: '#10b981' },
  failed:           { label: 'ОШИБКА',  color: '#ef4444' },
};

let techRefreshTimer = null;

function loadTechTasks() {
  const list = document.getElementById('tech-list');
  if (!list) return;
  list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:12px 0">Загрузка...</div>';

  fetch('/tech/tasks?limit=50')
    .then(r => r.json())
    .then(tasks => renderTechTasks(tasks))
    .catch(() => {
      list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
    });

  clearInterval(techRefreshTimer);
  techRefreshTimer = setInterval(loadTechTasks, 20000);
}

function renderTechTasks(tasks) {
  const list = document.getElementById('tech-list');
  if (!list) return;
  list.innerHTML = '';

  const filter = document.getElementById('tech-filter')?.value || 'all';
  const filtered = filter === 'all' ? tasks : tasks.filter(t => t.status === filter);

  if (!filtered.length) {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:12px 0">Задач нет</div>';
    return;
  }

  filtered.forEach(t => {
    const st = TECH_STATUS_LABELS[t.status] || { label: t.status, color: '#6b7280' };
    const ago = t.updated_at ? timeAgo(t.updated_at) : '';
    const row = document.createElement('div');
    row.className = 'tech-row';
    row.dataset.id = t.id;
    row.style.setProperty('--tech-status-color', st.color + '88');
    row.innerHTML = `
      <div class="tech-row-top">
        <span class="tech-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
        <span class="tech-pri" title="приоритет">${t.priority}</span>
        <span class="tech-title">${escHtml(t.title)}</span>
        <span class="tech-ago">${ago}</span>
      </div>
      ${t.description ? `<div class="tech-desc">${escHtml(t.description)}</div>` : ''}
      ${t.result ? `<div class="tech-result" id="res-${t.id}" style="display:none">${escHtml(t.result)}</div>
        <button class="tech-toggle" onclick="toggleResult(${t.id})">▸ результат</button>` : ''}
    `;
    list.appendChild(row);
  });
}

function toggleResult(id) {
  const el = document.getElementById('res-' + id);
  const btn = el?.nextElementSibling;
  if (!el) return;
  const show = el.style.display === 'none';
  el.style.display = show ? 'block' : 'none';
  if (btn) btn.textContent = show ? '▾ результат' : '▸ результат';
}

async function createTechTask() {
  const title = document.getElementById('tech-input-title')?.value.trim();
  const desc  = document.getElementById('tech-input-desc')?.value.trim();
  const prio  = parseInt(document.getElementById('tech-input-prio')?.value || '5');
  if (!title) return;

  const btn = document.getElementById('tech-create-btn');
  if (btn) btn.disabled = true;

  try {
    await fetch('/tech/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc || null, priority: prio, created_by: 'hq' }),
    });
    document.getElementById('tech-input-title').value = '';
    document.getElementById('tech-input-desc').value = '';
    loadTechTasks();
  } catch { /* silent */ }

  if (btn) btn.disabled = false;
}

function techFilterChange() {
  fetch('/tech/tasks?limit=50')
    .then(r => r.json())
    .then(tasks => renderTechTasks(tasks))
    .catch(() => {});
}
