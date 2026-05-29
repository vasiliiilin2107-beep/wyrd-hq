/* ─── IDEAS TAB ─────────────────────────────────────── */
const IDEA_STATUS = {
  idea:     { label: 'НОВАЯ',      color: '#f59e0b' },
  testing:  { label: 'В РАБОТЕ',   color: '#3b82f6' },
  active:   { label: 'АКТИВНА',    color: '#10b981' },
  archived: { label: 'АРХИВ',      color: '#6b7280' },
};

let ideasFilter = 'all';
let ideasRefreshTimer = null;

async function loadIdeas() {
  const list = document.getElementById('ideas-list');
  if (!list) return;
  list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:12px 0">Загрузка...</div>';
  try {
    const url = ideasFilter === 'all' ? '/income/ideas' : `/income/ideas?status=${ideasFilter}`;
    const data = await fetch(url).then(r => r.json());
    renderIdeas(data.ideas || []);
  } catch {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
  clearInterval(ideasRefreshTimer);
  ideasRefreshTimer = setInterval(loadIdeas, 30000);
}

function renderIdeas(ideas) {
  const list = document.getElementById('ideas-list');
  if (!list) return;
  list.innerHTML = '';
  if (!ideas.length) {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem;padding:12px 0">Идей пока нет</div>';
    return;
  }
  ideas.forEach(idea => list.appendChild(buildIdeaCard(idea)));
}

function buildIdeaCard(idea) {
  const st = IDEA_STATUS[idea.status] || { label: idea.status, color: '#6b7280' };
  const isPending = idea.status === 'idea';
  const card = document.createElement('div');
  card.className = 'idea-card';
  card.dataset.id = idea.id;
  const time = idea.created_at
    ? new Date(idea.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '';
  card.innerHTML = `
    <div class="idea-header">
      <span class="idea-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
      <span class="idea-source">${escHtml(idea.source || 'thomas')}</span>
      <span class="idea-time">${time}</span>
    </div>
    <div class="idea-title">${escHtml(idea.title)}</div>
    ${idea.description ? `<div class="idea-desc">${escHtml(idea.description)}</div>` : ''}
    ${idea.expected_revenue ? `<div class="idea-rev">💰 ${escHtml(idea.expected_revenue)}</div>` : ''}
    <div class="idea-actions${isPending ? '' : ' idea-actions-sm'}">
      ${isPending
        ? `<button class="idea-btn idea-btn-yes" onclick="patchIdea(${idea.id},'testing')">✅ В РАБОТУ</button>
           <button class="idea-btn idea-btn-no" onclick="patchIdea(${idea.id},'archived')">❌ ОТКЛОНИТЬ</button>`
        : `<button class="idea-btn idea-btn-ghost" onclick="patchIdea(${idea.id},'idea')">↩ ПЕРЕСМОТР</button>
           <button class="idea-btn idea-btn-del" onclick="deleteIdea(${idea.id})" title="Удалить">🗑</button>`
      }
    </div>
  `;
  return card;
}

async function patchIdea(id, status) {
  try {
    await fetch(`/income/ideas/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const card = document.querySelector(`.idea-card[data-id="${id}"]`);
    if (card) {
      card.classList.add(status === 'testing' ? 'idea-flash-green' : 'idea-flash-red');
      setTimeout(loadIdeas, 420);
    }
  } catch { /* silent */ }
}

async function deleteIdea(id) {
  if (!confirm('Удалить идею насовсем?')) return;
  try {
    await fetch(`/income/ideas/${id}`, { method: 'DELETE' });
    loadIdeas();
  } catch { /* silent */ }
}

function ideasFilterClick(btn, status) {
  document.querySelectorAll('.idea-filter').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  ideasFilter = status;
  loadIdeas();
}
