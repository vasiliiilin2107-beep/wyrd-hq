/* world.js — вкладка 🌍 Мир: отделы, агенты, паспорта */

let _worldDepts = [];
let _worldActiveDept = null;
let _worldActiveAgent = null;

async function loadWorld() {
  try {
    const r = await fetch('/api/world/departments');
    const data = await r.json();
    _worldDepts = data.departments || [];
    _renderWorldDepts();
    if (_worldDepts.length) selectWorldDept(_worldDepts[0].id);
  } catch(e) {
    document.getElementById('world-dept-list').innerHTML =
      '<div style="color:var(--text-dim);font-size:.65rem;padding:8px">Ошибка загрузки</div>';
  }
}

function _renderWorldDepts() {
  const el = document.getElementById('world-dept-list');
  if (!el) return;
  el.innerHTML = _worldDepts.map(d => `
    <div id="world-dept-btn-${d.id}"
         onclick="selectWorldDept('${d.id}')"
         style="padding:10px 12px;cursor:pointer;border-radius:8px;margin-bottom:4px;
                display:flex;align-items:center;gap:8px;transition:background .15s;
                font-size:.68rem;font-weight:600;letter-spacing:.05em">
      <span>${d.icon}</span>
      <span>${d.name}</span>
      <span style="margin-left:auto;font-size:.55rem;color:var(--text-dim)">${d.agents.length} агент${d.agents.length===1?'':'ов'}</span>
    </div>
  `).join('');
}

async function selectWorldDept(deptId) {
  _worldActiveDept = deptId;
  _worldActiveAgent = null;

  // Подсветить активный
  document.querySelectorAll('[id^="world-dept-btn-"]').forEach(el => {
    el.style.background = el.id === `world-dept-btn-${deptId}` ? 'rgba(255,255,255,.07)' : '';
  });

  const dept = _worldDepts.find(d => d.id === deptId);
  if (!dept) return;

  // Рендер агентов
  const agentsEl = document.getElementById('world-agents-list');
  if (agentsEl) {
    agentsEl.innerHTML = dept.agents.map(a => `
      <div onclick="selectWorldAgent('${a.id}')"
           id="world-agent-btn-${a.id}"
           style="padding:8px 10px;cursor:pointer;border-radius:6px;margin-bottom:3px;
                  display:flex;align-items:center;gap:7px;font-size:.65rem;transition:background .15s">
        <span>${a.icon}</span>
        <span style="font-weight:600">${a.name}</span>
      </div>
    `).join('');
  }

  // Загрузить файл отдела
  await _loadWorldContent(`/api/world/departments/${encodeURIComponent(deptId)}`);
}

async function selectWorldAgent(agentId) {
  _worldActiveAgent = agentId;

  document.querySelectorAll('[id^="world-agent-btn-"]').forEach(el => {
    el.style.background = el.id === `world-agent-btn-${agentId}` ? 'rgba(255,255,255,.1)' : '';
  });

  await _loadWorldContent(`/api/world/agents/${encodeURIComponent(agentId)}`);
}

async function _loadWorldContent(url) {
  const el = document.getElementById('world-content');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-dim);font-size:.65rem;padding:16px">Загрузка...</div>';
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);
    const text = await r.text();
    el.innerHTML = _renderMd(text);
  } catch(e) {
    el.innerHTML = `<div style="color:#ef4444;font-size:.65rem;padding:16px">Ошибка загрузки: ${e.message}</div>`;
  }
}

// Минимальный markdown-рендерер
function _renderMd(text) {
  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const lines = text.split('\n');
  let html = '';
  let inCode = false, inTable = false;

  for (let line of lines) {
    if (line.startsWith('```')) {
      if (!inCode) {
        if (inTable) { html += '</table>'; inTable = false; }
        html += '<pre style="background:rgba(0,0,0,.4);border-radius:6px;padding:10px;font-size:.6rem;overflow-x:auto;margin:8px 0">';
        inCode = true;
      } else {
        html += '</pre>'; inCode = false;
      }
      continue;
    }
    if (inCode) { html += esc(line) + '\n'; continue; }

    if (line.startsWith('| ')) {
      if (!inTable) { html += '<table style="border-collapse:collapse;width:100%;font-size:.62rem;margin:8px 0">'; inTable = true; }
      const cells = line.split('|').filter((_,i,a)=>i>0&&i<a.length-1);
      const isDiv = cells.every(c=>/^[-: ]+$/.test(c.trim()));
      if (!isDiv) {
        html += '<tr>' + cells.map(c=>`<td style="border:1px solid var(--border);padding:4px 8px">${_inlineMd(c.trim())}</td>`).join('') + '</tr>';
      }
      continue;
    }
    if (inTable) { html += '</table>'; inTable = false; }

    if (!line.trim()) { html += '<div style="height:6px"></div>'; continue; }
    if (line.startsWith('# '))  { html += `<div style="font-size:.85rem;font-weight:700;margin:12px 0 6px;color:#f8fafc">${esc(line.slice(2))}</div>`; continue; }
    if (line.startsWith('## ')) { html += `<div style="font-size:.75rem;font-weight:700;margin:10px 0 5px;color:#e2e8f0;border-bottom:1px solid var(--border);padding-bottom:3px">${esc(line.slice(3))}</div>`; continue; }
    if (line.startsWith('### ')){ html += `<div style="font-size:.68rem;font-weight:700;margin:8px 0 4px;color:#cbd5e1">${esc(line.slice(4))}</div>`; continue; }
    if (line.startsWith('> '))  { html += `<div style="border-left:3px solid #4a9eff;padding:4px 10px;color:#94a3b8;font-size:.62rem;margin:4px 0">${_inlineMd(line.slice(2))}</div>`; continue; }
    if (line.startsWith('- '))  { html += `<div style="font-size:.63rem;padding:1px 0 1px 12px;color:#f1f5f9">• ${_inlineMd(line.slice(2))}</div>`; continue; }

    html += `<div style="font-size:.63rem;line-height:1.6;color:#f1f5f9;margin:2px 0">${_inlineMd(line)}</div>`;
  }
  if (inCode) html += '</pre>';
  if (inTable) html += '</table>';
  return html;
}

function _inlineMd(s) {
  const esc = t => t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code style="background:rgba(0,0,0,.3);border-radius:3px;padding:1px 4px;font-size:.9em">$1</code>');
}

// Универсальный модал для промптов и длинных текстов
function showWorldModal(title, text) {
  let modal = document.getElementById('world-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'world-modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:flex-start;justify-content:center;padding:20px;overflow-y:auto';
    modal.onclick = e => { if(e.target===modal) modal.remove(); };
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div style="background:#1e293b;border:1px solid var(--border);border-radius:12px;
                width:100%;max-width:700px;padding:20px;margin:auto;position:relative">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
        <div style="font-size:.75rem;font-weight:700;color:#f8fafc">${title}</div>
        <button onclick="document.getElementById('world-modal').remove()"
                style="background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:1.2rem">✕</button>
      </div>
      <div style="font-size:.6rem;line-height:1.8;color:#cbd5e1;white-space:pre-wrap;
                  max-height:70vh;overflow-y:auto;font-family:monospace">${text.replace(/</g,'&lt;')}</div>
    </div>`;
}
