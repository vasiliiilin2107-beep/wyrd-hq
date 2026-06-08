/* WYRD HQ — Command Palette (Ctrl+K) */

const CMD_ITEMS = [
  { icon:'🏠', label:'Главная',             cat:'ПЕРЕХОД',  action:()=>setTab('home',document.querySelector('[data-tab=home]')) },
  { icon:'📖', label:'Book Studio',         cat:'ПЕРЕХОД',  action:()=>{ setTab('bookstudio',document.querySelector('[data-tab=bookstudio]')); loadBookStudio(); } },
  { icon:'📚', label:'Библиотека',          cat:'ПЕРЕХОД',  action:()=>{ setTab('library',document.querySelector('[data-tab=library]')); loadLibrary(); } },
  { icon:'💡', label:'Идеи',               cat:'ПЕРЕХОД',  action:()=>setTab('ideas',document.querySelector('[data-tab=ideas]')) },
  { icon:'🏛️', label:'Цивилизация',        cat:'ПЕРЕХОД',  action:()=>{ setTab('civilization',document.querySelector('[data-tab=civilization]')); loadCivilization(); } },
  { icon:'🌍', label:'Паспорта',            cat:'ПЕРЕХОД',  action:()=>{ setTab('world',document.querySelector('[data-tab=world]')); loadWorld(); } },
  { icon:'👔', label:'Образование',         cat:'ПЕРЕХОД',  action:()=>{ setTab('education',document.querySelector('[data-tab=education]')); loadEducation(); } },
  { icon:'🔧', label:'Техник',              cat:'ПЕРЕХОД',  action:()=>setTab('technik',document.querySelector('[data-tab=technik]')) },
  { icon:'🏗️', label:'Стройка',            cat:'ПЕРЕХОД',  action:()=>{ setTab('build',document.querySelector('[data-tab=build]')); loadBuild(); } },
  { icon:'📝', label:'Заметки',            cat:'ПЕРЕХОД',  action:()=>setTab('notes',document.querySelector('[data-tab=notes]')) },
  { icon:'🗺️', label:'Карта мира',         cat:'ПЕРЕХОД',  action:()=>setTab('map',document.querySelector('[data-tab=map]')) },
  { icon:'🔍', label:'Аудит',              cat:'ПЕРЕХОД',  action:()=>{ setTab('audit',document.querySelector('[data-tab=audit]')); loadAudit(); } },
  { icon:'📜', label:'Конституция',         cat:'ПЕРЕХОД',  action:()=>{ setTab('constitution',document.querySelector('[data-tab=constitution]')); loadConstitution(); } },
  { icon:'📁', label:'Файлы',              cat:'ПЕРЕХОД',  action:()=>{ setTab('files',document.querySelector('[data-tab=files]')); loadFilesList(); } },
  { icon:'📺', label:'Scribe',             cat:'ПЕРЕХОД',  action:()=>{ setTab('scribe',document.querySelector('[data-tab=scribe]')); loadScribe(); } },
  { icon:'➕', label:'Новая задача Технику', cat:'ДЕЙСТВИЕ', action:()=>{ setTab('technik',document.querySelector('[data-tab=technik]')); setTimeout(()=>document.getElementById('tech-input-title')?.focus(), 200); } },
  { icon:'🧠', label:'Запустить Совет',     cat:'ДЕЙСТВИЕ', action:()=>{ setTab('civilization',document.querySelector('[data-tab=civilization]')); loadCivilization(); setTimeout(()=>{ try { showCouncilForm(); } catch {} }, 600); } },
  { icon:'📖', label:'Генерировать главу',  cat:'ДЕЙСТВИЕ', action:()=>{ setTab('bookstudio',document.querySelector('[data-tab=bookstudio]')); loadBookStudio(); } },
  { icon:'⚡', label:'Запустить все циклы', cat:'ДЕЙСТВИЕ', action:()=>triggerAll(document.getElementById('trigger-btn')) },
  { icon:'👁️', label:'Открыть Томаса',     cat:'ДЕЙСТВИЕ', action:()=>window.location='/thomas' },
];

let _cmdSelected = 0;
let _cmdFiltered = [];

function openCmdPalette() {
  const overlay = document.getElementById('cmd-overlay');
  if (!overlay) return;
  overlay.style.display = 'flex';
  const input = document.getElementById('cmd-input');
  if (input) { input.value = ''; input.focus(); }
  cmdFilter('');
}

function closeCmdPalette() {
  const overlay = document.getElementById('cmd-overlay');
  if (overlay) overlay.style.display = 'none';
}

function cmdFilter(query) {
  const q = (query || '').toLowerCase().trim();
  _cmdFiltered = q
    ? CMD_ITEMS.filter(i => i.label.toLowerCase().includes(q) || i.cat.toLowerCase().includes(q))
    : CMD_ITEMS;
  _cmdSelected = 0;
  renderCmdList();
}

function renderCmdList() {
  const list = document.getElementById('cmd-list');
  if (!list) return;
  if (!_cmdFiltered.length) {
    list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:.78rem">Ничего не найдено</div>';
    return;
  }
  list.innerHTML = _cmdFiltered.map((item, i) => `
    <div class="cmd-item${i === _cmdSelected ? ' selected' : ''}" onmouseenter="_cmdSelected=${i};renderCmdList()" onclick="cmdExecute(${i})">
      <span class="cmd-item-icon">${item.icon}</span>
      <span class="cmd-item-label">${escHtml(item.label)}</span>
      <span class="cmd-item-cat">${item.cat}</span>
    </div>
  `).join('');
}

function cmdExecute(i) {
  const item = _cmdFiltered[i !== undefined ? i : _cmdSelected];
  if (!item) return;
  closeCmdPalette();
  item.action();
}

function cmdKeyDown(e) {
  if (e.key === 'ArrowDown') { _cmdSelected = Math.min(_cmdSelected + 1, _cmdFiltered.length - 1); renderCmdList(); e.preventDefault(); }
  else if (e.key === 'ArrowUp') { _cmdSelected = Math.max(_cmdSelected - 1, 0); renderCmdList(); e.preventDefault(); }
  else if (e.key === 'Enter') { cmdExecute(); e.preventDefault(); }
  else if (e.key === 'Escape') { closeCmdPalette(); e.preventDefault(); }
}

document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); openCmdPalette(); }
  else if (e.key === 'Escape') {
    const overlay = document.getElementById('cmd-overlay');
    if (overlay && overlay.style.display !== 'none') { closeCmdPalette(); e.preventDefault(); }
  }
});
