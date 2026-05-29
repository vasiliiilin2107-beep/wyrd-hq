/* ── Вкладка 📁 Файлы Томаса ─────────────────────────── */

let _filesData = [];
let _activeFile = null;

async function loadFilesList() {
  const list = document.getElementById('files-list');
  if (!list) return;
  list.innerHTML = '<div class="files-empty">Загрузка...</div>';
  try {
    const r = await fetch('/thomas/docs');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    _filesData = await r.json();
    renderFilesList(_filesData);
  } catch (e) {
    list.innerHTML = `<div class="files-empty">Ошибка: ${e.message}</div>`;
  }
}

function renderFilesList(files) {
  const list = document.getElementById('files-list');
  if (!list) return;
  if (!files.length) {
    list.innerHTML = '<div class="files-empty">Файлов пока нет</div>';
    return;
  }
  list.innerHTML = files.map(f => {
    const name = f.path.split('/').pop();
    const kb = (f.size / 1024).toFixed(1);
    const active = _activeFile === f.path ? ' active' : '';
    return `<div class="file-item${active}" onclick="openFile('${f.path}')" title="${f.path}">
      <span class="file-icon">${fileIcon(name)}</span>
      <span class="file-name">${name}</span>
      <span class="file-size">${kb} KB</span>
    </div>`;
  }).join('');
}

function fileIcon(name) {
  if (name.endsWith('.md')) return '📄';
  if (name.endsWith('.json')) return '{}';
  if (name.endsWith('.py')) return '🐍';
  if (name.endsWith('.txt')) return '📋';
  return '📎';
}

async function openFile(path) {
  _activeFile = path;
  renderFilesList(_filesData);

  const viewer = document.getElementById('file-viewer');
  const fname = document.getElementById('file-viewer-name');
  if (!viewer) return;

  viewer.innerHTML = '<div class="files-empty">Загрузка...</div>';
  if (fname) fname.textContent = path.split('/').pop();

  try {
    const r = await fetch(`/thomas/docs/${encodeURIComponent(path)}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const text = await r.text();
    viewer.innerHTML = renderContent(path, text);
  } catch (e) {
    viewer.innerHTML = `<div class="files-empty">Ошибка: ${e.message}</div>`;
  }
}

function renderContent(path, text) {
  if (path.endsWith('.md')) {
    return `<pre class="file-content md-content">${escHtml(text)}</pre>`;
  }
  if (path.endsWith('.json')) {
    try {
      const pretty = JSON.stringify(JSON.parse(text), null, 2);
      return `<pre class="file-content json-content">${escHtml(pretty)}</pre>`;
    } catch (_) { /* fall through */ }
  }
  return `<pre class="file-content">${escHtml(text)}</pre>`;
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function filesFilterInput(val) {
  const q = val.trim().toLowerCase();
  const filtered = q ? _filesData.filter(f => f.path.toLowerCase().includes(q)) : _filesData;
  renderFilesList(filtered);
}
