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
  await Promise.all([loadAgents(), loadProposals(), loadSessions(), loadThoughts()]);
  clearInterval(civRefreshTimer);
  civRefreshTimer = setInterval(loadCivilization, 30000);
}

// ─── AGENTS ──────────────────────────────────────────────

async function loadAgents() {
  const el = document.getElementById('civ-agents-list');
  if (!el) return;
  if (!el.children.length) el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Загрузка...</div>';
  try {
    const data = await fetch('/civilization/agents').then(r => r.json());
    renderAgents(data.agents || []);
  } catch {
    if (!el.children.length) el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
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

// ─── COUNCIL SESSIONS ────────────────────────────────────

const SESSION_STATUS = {
  pending:  { label: 'ЖДЁТ',    color: '#6b7280' },
  thinking: { label: 'ДУМАЮТ',  color: '#f59e0b' },
  verdict:  { label: 'ВЕРДИКТ', color: '#10b981' },
  error:    { label: 'ОШИБКА',  color: '#ef4444' },
};

const openSessions = new Set();

async function loadSessions() {
  const el = document.getElementById('civ-sessions-list');
  if (!el) return;
  if (openSessions.size > 0) return;
  try {
    const data = await fetch('/council/sessions?limit=10').then(r => r.json());
    renderSessions(data.sessions || []);
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
}

function renderSessions(sessions) {
  const el = document.getElementById('civ-sessions-list');
  if (!el) return;
  document.getElementById('civ-sessions-count').textContent = `(${sessions.length})`;
  if (!sessions.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Совет ещё не думал</div>';
    return;
  }
  el.innerHTML = '';
  sessions.forEach(s => el.appendChild(buildSessionCard(s)));
}

function buildSessionCard(s) {
  const st = SESSION_STATUS[s.status] || { label: s.status, color: '#6b7280' };
  const time = s.created_at
    ? new Date(s.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : '';
  const isOpen = openSessions.has(s.id);
  const card = document.createElement('div');
  card.className = 'civ-session-card' + (isOpen ? ' open' : '');
  card.dataset.id = s.id;
  card.innerHTML = `
    <div class="civ-session-top" onclick="toggleSession(${s.id}, this)">
      <span class="civ-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
      <span class="civ-session-idea">${escHtml(s.idea_text)}</span>
      <span class="civ-session-src">${escHtml(s.source)}</span>
      <span class="civ-session-time">${time}</span>
      <span style="font-size:.6rem;color:var(--text-dim)">${isOpen ? '▾' : '▸'}</span>
    </div>
    <div class="civ-dialog${isOpen ? ' open' : ''}" id="dialog-${s.id}">
      <div style="color:var(--text-dim);font-size:.65rem">Загрузка диалога...</div>
    </div>
  `;
  if (isOpen) loadDialog(s.id);
  return card;
}

async function toggleSession(id, headerEl) {
  const dialog = document.getElementById(`dialog-${id}`);
  if (!dialog) return;
  const arrow = headerEl.querySelector('span:last-child');
  if (openSessions.has(id)) {
    openSessions.delete(id);
    dialog.classList.remove('open');
    headerEl.closest('.civ-session-card').classList.remove('open');
    if (arrow) arrow.textContent = '▸';
  } else {
    openSessions.add(id);
    dialog.classList.add('open');
    headerEl.closest('.civ-session-card').classList.add('open');
    if (arrow) arrow.textContent = '▾';
    await loadDialog(id);
  }
}

const MSG_CLASS = {
  strategist:   'civ-msg-strategist',
  architect:    'civ-msg-architect',
  cartographer: 'civ-msg-cartographer',
  thomas:       'civ-msg-thomas',
};

async function loadDialog(sessionId) {
  const el = document.getElementById(`dialog-${sessionId}`);
  if (!el) return;
  try {
    const data = await fetch(`/council/sessions/${sessionId}/messages`).then(r => r.json());
    const msgs = data.messages || [];

    // Найдём вердикт из sessions
    const sCard = document.querySelector(`.civ-session-card[data-id="${sessionId}"]`);

    el.innerHTML = '';
    if (!msgs.length) {
      el.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem">Диалог пока пуст — Совет думает...</div>';
      return;
    }
    msgs.forEach(m => {
      const div = document.createElement('div');
      div.className = `civ-msg ${MSG_CLASS[m.speaker] || ''}`;
      div.innerHTML = `<div class="civ-msg-speaker">${escHtml(m.speaker_label || m.speaker)}</div>${escHtml(m.message)}`;
      el.appendChild(div);
    });

    // Вердикт — берём из sessions list
    const sessData = await fetch('/council/sessions?limit=50').then(r => r.json());
    const sess = (sessData.sessions || []).find(s => s.id === sessionId);
    if (sess && sess.verdict && sess.verdict.summary) {
      const v = document.createElement('div');
      v.className = 'civ-verdict';
      v.innerHTML = `<div class="civ-verdict-label">ВЕРДИКТ</div>${escHtml(sess.verdict.summary)}`;
      el.appendChild(v);
    }
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem">Ошибка загрузки диалога</div>';
  }
}

// ─── COUNCIL FORM ─────────────────────────────────────────

function showCouncilForm() {
  document.getElementById('council-form').style.display = 'block';
  document.getElementById('council-idea-input').focus();
}
function hideCouncilForm() {
  document.getElementById('council-form').style.display = 'none';
  document.getElementById('council-idea-input').value = '';
}

async function submitCouncilSession() {
  const idea = document.getElementById('council-idea-input').value.trim();
  if (!idea) return;
  try {
    await fetch('/council/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idea, source: 'manual' }),
    });
    hideCouncilForm();
    await loadSessions();
  } catch { /* silent */ }
}

// ─── THOUGHTS ─────────────────────────────────────────────

async function loadThoughts() {
  const el = document.getElementById('civ-thoughts-list');
  if (!el) return;
  try {
    const data = await fetch('/council/thoughts?limit=15').then(r => r.json());
    renderThoughts(data.thoughts || []);
  } catch {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>';
  }
}

function renderThoughts(thoughts) {
  const el = document.getElementById('civ-thoughts-list');
  if (!el) return;
  document.getElementById('civ-thoughts-count').textContent = `(${thoughts.length})`;
  if (!thoughts.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Мыслей пока нет</div>';
    return;
  }
  el.innerHTML = '';
  thoughts.forEach(t => {
    const time = t.created_at
      ? new Date(t.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
      : '';
    const div = document.createElement('div');
    div.className = 'civ-thought-item';
    div.innerHTML = `${escHtml(t.text)}<div class="civ-thought-meta">${escHtml(t.source)} · ${time}</div>`;
    el.appendChild(div);
  });
}
