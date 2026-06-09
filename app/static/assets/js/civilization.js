/* ─── CIVILIZATION v3 — D3 граф + список ──────────────── */

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
  pending:  { label: 'ОЖИДАЕТ',   color: '#f59e0b' },
  approved: { label: 'ОДОБРЕНО',  color: '#10b981' },
  rejected: { label: 'ОТКЛОНЕНО', color: '#ef4444' },
  building: { label: 'СТРОИТСЯ',  color: '#3b82f6' },
  done:     { label: 'ГОТОВО',    color: '#6b7280' },
};

let civRefreshTimer = null;
let _civView = 'graph';
let _civAgentsCache = [];

async function loadCivilization() {
  await Promise.all([loadAgents(), loadProposals(), loadSessions(), loadThoughts()]);
  clearInterval(civRefreshTimer);
  civRefreshTimer = setInterval(loadCivilization, 60000);
}

function setCivView(mode) {
  _civView = mode;
  document.getElementById('civ-graph-view').style.display = mode === 'graph' ? '' : 'none';
  document.getElementById('civ-list-view').style.display  = mode === 'list'  ? '' : 'none';
  document.getElementById('civ-btn-graph').classList.toggle('active', mode === 'graph');
  document.getElementById('civ-btn-list').classList.toggle('active',  mode === 'list');
  if (mode === 'list'  && _civAgentsCache.length) _renderAgentList(_civAgentsCache);
  if (mode === 'graph' && _civAgentsCache.length) _renderAgentGraph(_civAgentsCache);
}

// ─── AGENTS ──────────────────────────────────────────────

async function loadAgents() {
  try {
    const data = await fetch('/civilization/agents').then(r => r.json());
    const agents = data.agents || [];
    _civAgentsCache = agents;
    const cnt = document.getElementById('civ-agents-count');
    if (cnt) cnt.textContent = `(${agents.length})`;
    if (_civView === 'graph') _renderAgentGraph(agents);
    else _renderAgentList(agents);
  } catch (e) { console.error('loadAgents:', e); }
}

function _renderAgentGraph(agents) {
  if (typeof d3 === 'undefined') { console.warn('D3 not loaded'); return; }
  const svgEl = document.getElementById('civ-svg');
  if (!svgEl) return;
  const container = document.getElementById('civ-graph-container');
  const W = container.clientWidth || 700, H = container.clientHeight || 440;

  const svg = d3.select('#civ-svg');
  svg.selectAll('*').remove();
  svg.attr('viewBox', `0 0 ${W} ${H}`);

  const SIZES = { council: 22, foreman: 15, observer: 13, worker: 10 };
  const STATUS_FILL = { active: '#22C55E', idle: '#EAB308', offline: '#EF4444' };

  const nodes = agents.map(a => ({
    id: a.name, label: a.name, level: a.level, status: a.status,
    task: a.current_task, pulse_ago: a.pulse_ago,
    r: SIZES[a.level] || 10,
    fill: STATUS_FILL[a.status] || '#6B7280',
  }));

  const byLevel = {};
  nodes.forEach(n => (byLevel[n.level] = byLevel[n.level] || []).push(n));
  const pick = (lvl) => byLevel[lvl]?.length ? byLevel[lvl] : [];
  const links = [];
  (byLevel.foreman  || []).forEach((f,i) => { const t=pick('council'); if(t.length) links.push({source:f.id,target:t[i%t.length].id}); });
  (byLevel.worker   || []).forEach((w,i) => { const t=pick('foreman').length?pick('foreman'):pick('council'); if(t.length) links.push({source:w.id,target:t[i%t.length].id}); });
  (byLevel.observer || []).forEach((o,i) => { const t=pick('council'); if(t.length) links.push({source:o.id,target:t[i%t.length].id}); });

  const sim = d3.forceSimulation(nodes)
    .force('link',      d3.forceLink(links).id(d=>d.id).distance(85).strength(0.5))
    .force('charge',    d3.forceManyBody().strength(-260))
    .force('center',    d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide().radius(d=>d.r+10));

  const g = svg.append('g');

  const linkSel = g.append('g').attr('stroke','#2a2a2a').attr('stroke-opacity',0.6)
    .selectAll('line').data(links).join('line').attr('stroke-width',1.5);

  const nodeSel = g.append('g').selectAll('circle').data(nodes).join('circle')
    .attr('r', d=>d.r).attr('fill', d=>d.fill)
    .attr('stroke', d=>d.fill).attr('stroke-width',2.5).attr('stroke-opacity',0.35)
    .style('cursor','pointer')
    .call(d3.drag()
      .on('start',(e,d)=>{ if(!e.active)sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on('drag', (e,d)=>{ d.fx=e.x; d.fy=e.y; })
      .on('end',  (e,d)=>{ if(!e.active)sim.alphaTarget(0); d.fx=null; d.fy=null; }));

  const labelSel = g.append('g').selectAll('text').data(nodes).join('text')
    .text(d=>d.label).attr('font-size','9px').attr('fill','#666')
    .attr('text-anchor','middle').attr('dy', d=>d.r+12).style('pointer-events','none');

  const tip = document.getElementById('civ-tooltip');
  nodeSel.on('mouseover',(e,d)=>{
    if (!tip) return;
    tip.style.display = 'block';
    tip.style.left = (e.offsetX+14)+'px'; tip.style.top = (e.offsetY-10)+'px';
    const lv = AGENT_LEVEL[d.level]||{label:d.level,color:'#888'};
    tip.innerHTML = `<b>${d.label}</b> <span style="color:${lv.color};font-size:.65rem">${lv.label}</span><br>${d.task||'—'}<br><span style="color:#555;font-size:.65rem">${d.pulse_ago||''}</span>`;
  }).on('mouseout', ()=>{ if(tip) tip.style.display='none'; });

  svg.call(d3.zoom().scaleExtent([0.2,4]).on('zoom', e=>g.attr('transform',e.transform)));

  sim.on('tick',()=>{
    linkSel.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
           .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    nodeSel.attr('cx',d=>Math.max(d.r,Math.min(W-d.r,d.x))).attr('cy',d=>Math.max(d.r,Math.min(H-d.r,d.y)));
    labelSel.attr('x',d=>d.x).attr('y',d=>d.y);
  });

  setTimeout(()=>{
    nodeSel.filter(d=>d.status==='active').each(function pls(){
      d3.select(this).transition().duration(1600).attr('stroke-opacity',0.9).attr('r',d=>d.r*1.4)
        .transition().duration(1600).attr('stroke-opacity',0.35).attr('r',d=>d.r).on('end',pls);
    });
  }, 800);
}

function _renderAgentList(agents) {
  const el = document.getElementById('civ-agents-list');
  if (!el) return;
  const order = ['council','foreman','worker','observer'];
  const groups = {};
  agents.forEach(a => (groups[a.level] = groups[a.level] || []).push(a));
  el.innerHTML = '';
  order.forEach(lvl => {
    if (!groups[lvl]?.length) return;
    const lv = AGENT_LEVEL[lvl] || { label: lvl, color: '#888' };
    const hdr = document.createElement('div');
    hdr.className = 'section-header';
    hdr.style.cssText = `color:${lv.color};margin:12px 0 6px`;
    hdr.textContent = lv.label;
    el.appendChild(hdr);
    groups[lvl].forEach(a => el.appendChild(buildAgentCard(a)));
  });
}

function buildAgentCard(a) {
  const lv = AGENT_LEVEL[a.level] || { label: a.level, color: '#6b7280' };
  const st = AGENT_STATUS[a.status] || { icon: '⚪', label: a.status };
  const card = document.createElement('div');
  card.className = 'civ-agent-card';
  card.style.setProperty('--agent-color', lv.color);
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
  } catch { el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>'; }
}

function renderProposals(proposals) {
  const el = document.getElementById('civ-proposals-list');
  if (!el) return;
  document.getElementById('civ-proposals-count').textContent = `(${proposals.filter(p=>p.status==='pending').length} ожид.)`;
  if (!proposals.length) { el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Предложений нет</div>'; return; }
  el.innerHTML = '';
  proposals.forEach(p => el.appendChild(buildProposalCard(p)));
}

function buildProposalCard(p) {
  const st = PROPOSAL_STATUS[p.status] || { label: p.status, color: '#6b7280' };
  const isPending = p.status === 'pending';
  const time = p.created_at ? new Date(p.created_at).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : '';
  const card = document.createElement('div');
  card.className = 'civ-proposal-card'; card.dataset.id = p.id;
  card.innerHTML = `
    <div class="civ-proposal-top">
      <span class="civ-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
      <span class="civ-prop-from">от: ${escHtml(p.from_agent)}</span>
      <span class="civ-prop-time">${time}</span>
    </div>
    <div class="civ-prop-role">${escHtml(p.role_needed)}</div>
    ${p.reason ? `<div class="civ-prop-reason">${escHtml(p.reason)}</div>` : ''}
    ${isPending ? `<div class="civ-prop-actions">
      <button class="idea-btn idea-btn-yes" onclick="patchProposal(${p.id},'approved')">✅ ОДОБРИТЬ</button>
      <button class="idea-btn idea-btn-no"  onclick="patchProposal(${p.id},'rejected')">❌ ОТКЛОНИТЬ</button>
    </div>` : ''}
  `;
  return card;
}

async function patchProposal(id, status) {
  try {
    await fetch(`/civilization/proposals/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});
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
const sessionFilter = {};

async function loadSessions() {
  const el = document.getElementById('civ-sessions-list');
  if (!el || openSessions.size > 0) return;
  try {
    const data = await fetch('/council/sessions?limit=10').then(r => r.json());
    renderSessions(data.sessions || []);
  } catch { el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>'; }
}

function renderSessions(sessions) {
  const el = document.getElementById('civ-sessions-list');
  if (!el) return;
  document.getElementById('civ-sessions-count').textContent = `(${sessions.length})`;
  if (!sessions.length) { el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Совет ещё не думал</div>'; return; }
  el.innerHTML = '';
  sessions.forEach(s => el.appendChild(buildSessionCard(s)));
}

function buildSessionCard(s) {
  const st = SESSION_STATUS[s.status] || { label: s.status, color: '#6b7280' };
  const time = s.created_at ? new Date(s.created_at).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : '';
  const isOpen = openSessions.has(s.id);
  const card = document.createElement('div');
  card.className = 'civ-session-card' + (isOpen ? ' open' : ''); card.dataset.id = s.id;
  card.innerHTML = `
    <div class="civ-session-top" onclick="toggleSession(${s.id},this)">
      <span class="civ-badge" style="color:${st.color};border-color:${st.color}40">${st.label}</span>
      <span class="civ-session-idea">${escHtml(s.idea_text)}</span>
      <span class="civ-session-src">${escHtml(s.source)}</span>
      <span class="civ-session-time">${time}</span>
      <span style="font-size:.6rem;color:var(--text-dim)">${isOpen?'▾':'▸'}</span>
    </div>
    <div class="civ-dialog${isOpen?' open':''}" id="dialog-${s.id}">
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

const MSG_CLASS = { strategist:'civ-msg-strategist', architect:'civ-msg-architect', cartographer:'civ-msg-cartographer', thomas:'civ-msg-thomas' };

function toggleSpeakerFilter(sessionId, speaker) {
  sessionFilter[sessionId] = sessionFilter[sessionId] === speaker ? null : speaker;
  _applyFilter(sessionId);
}

function _applyFilter(sessionId) {
  const el = document.getElementById(`dialog-${sessionId}`);
  if (!el) return;
  const active = sessionFilter[sessionId];
  el.querySelectorAll('.civ-msg').forEach(div => { div.style.opacity = (!active||div.dataset.speaker===active)?'1':'0.18'; });
  el.querySelectorAll('.civ-msg-speaker').forEach(sp => {
    const isActive = active && sp.closest('.civ-msg').dataset.speaker === active;
    sp.style.outline = isActive ? '1px solid currentColor' : 'none';
    sp.style.borderRadius = isActive ? '3px' : '';
  });
}

async function loadDialog(sessionId) {
  const el = document.getElementById(`dialog-${sessionId}`);
  if (!el) return;
  try {
    const data = await fetch(`/council/sessions/${sessionId}/messages`).then(r => r.json());
    const msgs = data.messages || [];
    el.innerHTML = '';
    if (!msgs.length) { el.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem">Диалог пока пуст — Совет думает...</div>'; return; }
    msgs.forEach(m => {
      const div = document.createElement('div');
      div.className = `civ-msg ${MSG_CLASS[m.speaker]||''}`; div.dataset.speaker = m.speaker;
      div.innerHTML = `<div class="civ-msg-speaker" style="cursor:pointer" onclick="toggleSpeakerFilter(${sessionId},'${m.speaker}')">${escHtml(m.speaker_label||m.speaker)}</div>${escHtml(m.message)}`;
      el.appendChild(div);
    });
    _applyFilter(sessionId);
  } catch { el.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem">Ошибка загрузки диалога</div>'; }
}

async function clearAllSessions() {
  const count = document.getElementById('civ-sessions-count').textContent.replace(/\D/g,'');
  if (!confirm(`Удалить все сессии Совета (${count||'?'})? Это нельзя отменить.`)) return;
  try { await fetch('/council/sessions',{method:'DELETE'}); openSessions.clear(); await loadSessions(); }
  catch (e) { alert('Ошибка: '+e.message); }
}

function showCouncilForm()  { document.getElementById('council-form').style.display='block'; document.getElementById('council-idea-input').focus(); }
function hideCouncilForm()  { document.getElementById('council-form').style.display='none'; document.getElementById('council-idea-input').value=''; }

async function submitCouncilSession() {
  const idea = document.getElementById('council-idea-input').value.trim();
  if (!idea) return;
  try {
    await fetch('/council/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({idea,source:'manual'})});
    hideCouncilForm(); await loadSessions();
  } catch { /* silent */ }
}

// ─── THOUGHTS ─────────────────────────────────────────────

async function loadThoughts() {
  const el = document.getElementById('civ-thoughts-list');
  if (!el) return;
  try {
    const data = await fetch('/council/thoughts?limit=15').then(r => r.json());
    renderThoughts(data.thoughts || []);
  } catch { el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Ошибка загрузки</div>'; }
}

function renderThoughts(thoughts) {
  const el = document.getElementById('civ-thoughts-list');
  if (!el) return;
  document.getElementById('civ-thoughts-count').textContent = `(${thoughts.length})`;
  if (!thoughts.length) { el.innerHTML = '<div style="color:var(--text-dim);font-size:.7rem">Мыслей пока нет</div>'; return; }
  el.innerHTML = '';
  thoughts.forEach(t => {
    const time = t.created_at ? new Date(t.created_at).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : '';
    const div = document.createElement('div');
    div.className = 'civ-thought-item';
    div.innerHTML = `${escHtml(t.text)}<div class="civ-thought-meta">${escHtml(t.source)} · ${time}</div>`;
    el.appendChild(div);
  });
}
