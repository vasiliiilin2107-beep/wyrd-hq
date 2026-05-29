/* ─── CIVILIZATION TAB ──────────────────────────────────── */

const AGENT_LEVEL = {
  council:  { label: 'СОВЕТ',    color: '#f59e0b' },
  foreman:  { label: 'БРИГАДИР', color: '#3b82f6' },
  worker:   { label: 'РАБОЧИЙ',  color: '#10b981' },
  observer: { label: 'НАБЛЮД.',  color: '#8b5cf6' },
};

const AGENT_STATUS = {
  active:  { icon: '🟢', label: 'Активен' },
  idle:    { icon: '🟡', label: 'Ожидает' },
  offline: { icon: '🔴', label: 'Офлайн' },
};

const PROPOSAL_STATUS = {
  pending:  { label: 'ОЖИДАЕТ',  color: '#f59e0b' },
  approved: { label: 'ОДОБРЕНО', color: '#10b981' },
  rejected: { label: 'ОТКЛОНЕНО',color: '#ef4444' },
  building: { label: 'СТРОИТСЯ', color: '#3b82f6' },
  done:     { label: 'ГОТОВО',   color: '#6b7280' },
};

let civRefreshTimer = null;

async function loadCivilization() {
  await Promise.all([loadAgents(), loadProposals()]);
  clearInterval(civRefreshTimer);
  civRefreshTimer = setInterval(loadCivilization, 30000);
}

// ─── AGENTS ──────────────────────────────────────────────

async function loadAgents() {
  const el = document.getElementById('civ-agents-list');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Загрузка...</div>';
  try {
    const data = await fetch('/civilization/agents').then(r => r.json());
    renderAgents(data.agents || []);
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
}

function renderAgents(agents) {
  const el = document.getElementById('civ-agents-list');
  if (!el) return;
  document.getElementById('civ-agents-count').textContent = `(${agents.length})`;
  if (!agents.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Агентов нет</div>';
    return;
  }
  el.innerHTML = '';
  agents.forEach(a => el.appendChild(buildAgentCard(a)));
}

function buildAgentCard(a) {
  const lv = AGENT_LEVEL[a.level] || { label: a.level, color: '#6b7280' };
  const st = AGENT_STATUS[a.status] || { icon: '⚪', label: a.status };
  const card = document.createElement('div');
  card.className = 'civ-agent-card';
  card.innerHTML = `
    <div class="civ-agent-top">
      <span class="civ-badge" style="color:${lv.color};border-color:${lv.color}40">${lv.label}</span>
      <span class="civ-agent-name">${escHtml(a.name)}</span>
      <span class="civ-agent-status" title="${st.label}">${st.icon}</span>
      <span class="civ-branch-tag">${escHtml(a.branch)}</span>
      ${a.pulse_ago ? `<span class="civ-pulse-time">↯ ${escHtml(a.pulse_ago)}</span>` : ''}
    </div>
    <div class="civ-agent-role">${escHtml(a.role)}</div>
    ${a.current_task ? `<div class="civ-agent-task">⚙ ${escHtml(a.current_task)}</div>` : ''}
  `;
  return card;
}

// ─── PROPOSALS ───────────────────────────────────────────

async function loadProposals() {
  const el = document.getElementById('civ-proposals-list');
  if (!el) return;
  try {
    const data = await fetch('/civilization/proposals').then(r => r.json());
    renderProposals(data.proposals || []);
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
}

function renderProposals(proposals) {
  const el = document.getElementById('civ-proposals-list');
  if (!el) return;
  document.getElementById('civ-proposals-count').textContent = `(${proposals.filter(p => p.status === 'pending').length} ожид.)`;
  if (!proposals.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Предложений нет</div>';
    return;
  }
  el.innerHTML = '';
  proposals.forEach(p => el.appendChild(buildProposalCard(p)));
}

function buildProposalCard(p) {
  const st = PROPOSAL_STATUS[p.status] || { label: p.status, color: '#6b7280' };
  const isPending = p.status === 'pending';
  const time = p.created_at
    ? new Date(p.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '';
  const card = document.createElement('div');
  card.className = 'civ-proposal-card';
  card.dataset.id = p.id;
  card.innerHTML = `
    <div class="civ-proposal-top">
      <span class="civ-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
      <span class="civ-prop-from">от: ${escHtml(p.from_agent)}</span>
      <span class="civ-prop-time">${time}</span>
    </div>
    <div class="civ-prop-role">${escHtml(p.role_needed)}</div>
    ${p.reason ? `<div class="civ-prop-reason">${escHtml(p.reason)}</div>` : ''}
    ${isPending ? `
      <div class="civ-prop-actions">
        <button class="idea-btn idea-btn-yes" onclick="patchProposal(${p.id},'approved')">✅ ОДОБРИТЬ</button>
        <button class="idea-btn idea-btn-no" onclick="patchProposal(${p.id},'rejected')">❌ ОТКЛОНИТЬ</button>
      </div>` : ''}
  `;
  return card;
}

async function patchProposal(id, status) {
  try {
    await fetch(`/civilization/proposals/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    loadProposals();
  } catch { /* silent */ }
}
