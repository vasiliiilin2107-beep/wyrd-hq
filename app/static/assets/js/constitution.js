/* ── Вкладка 📜 Конституция ─────────────────────────── */

let _constEdited = false;

async function loadConstitution() {
  const ta = document.getElementById('const-textarea');
  const meta = document.getElementById('const-meta');
  if (!ta) return;
  ta.value = 'Загрузка...';
  try {
    const r = await fetch('/constitution');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    ta.value = d.text || '';
    _constEdited = false;
    _constUpdateMeta(d.updated_at);
    _constSetSaved();
  } catch (e) {
    ta.value = '';
    if (meta) meta.textContent = `Ошибка: ${e.message}`;
  }
}

async function saveConstitution() {
  const ta = document.getElementById('const-textarea');
  const btn = document.getElementById('const-save-btn');
  if (!ta || !btn) return;
  btn.disabled = true;
  btn.textContent = 'Сохраняю...';
  try {
    const r = await fetch('/constitution', {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: ta.value}),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    _constEdited = false;
    _constUpdateMeta(d.updated_at);
    _constSetSaved();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = '💾 СОХРАНИТЬ';
    alert(`Ошибка сохранения: ${e.message}`);
  }
}

function _constOnEdit() {
  _constEdited = true;
  const btn = document.getElementById('const-save-btn');
  if (btn) {
    btn.disabled = false;
    btn.textContent = '💾 СОХРАНИТЬ';
    btn.classList.add('const-btn-dirty');
  }
}

function _constSetSaved() {
  const btn = document.getElementById('const-save-btn');
  if (btn) {
    btn.disabled = false;
    btn.textContent = '✓ СОХРАНЕНО';
    btn.classList.remove('const-btn-dirty');
    setTimeout(() => { if (!_constEdited) btn.textContent = '💾 СОХРАНИТЬ'; }, 2000);
  }
}

function _constUpdateMeta(iso) {
  const el = document.getElementById('const-meta');
  if (!el || !iso) return;
  const d = new Date(iso);
  el.textContent = `Обновлено: ${d.toLocaleString('ru-RU')}`;
}
