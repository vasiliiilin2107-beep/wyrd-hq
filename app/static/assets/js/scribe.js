/* ─── SCRIBE TAB ───────────────────────────────────────── */

async function loadScribe() {
  await Promise.all([loadScribeStats(), loadScribeList()]);
}

async function loadScribeStats() {
  const el = document.getElementById('scribe-stats');
  if (!el) return;
  try {
    const r = await fetch('/tokens/scribe/stats');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    el.innerHTML = `
      <div class="lib-stat-box">
        <div class="lib-stat-num">${d.transcriptions || 0}</div>
        <div class="lib-stat-label">транскрипций</div>
      </div>
      <div class="lib-stat-box">
        <div class="lib-stat-num">${d.total_spent_tokens || 0}</div>
        <div class="lib-stat-label">токенов потрачено</div>
      </div>
      <div class="lib-stat-box">
        <div class="lib-stat-num">${d.unique_users || 0}</div>
        <div class="lib-stat-label">пользователей</div>
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Нет данных (${e.message})</div>`;
  }
}

async function loadScribeList() {
  const el = document.getElementById('scribe-list');
  if (!el) return;
  el.innerHTML = '<div class="lib-empty">Загрузка...</div>';
  try {
    const r = await fetch('/tokens/scribe/stats');
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    const list = d.recent || [];
    if (!list.length) {
      el.innerHTML = '<div class="lib-empty">Транскрипций ещё не было</div>';
      return;
    }
    el.innerHTML = list.map(tx => {
      const amt = Math.abs(tx.amount);
      const time = tx.created_at ? new Date(tx.created_at).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
      }) : '';
      const reason = tx.reason || '';
      const short = reason.length > 80 ? reason.slice(0, 80) + '…' : reason;
      return `<div class="lib-knowledge-row">
        <div class="lib-k-header">
          <span style="font-size:.75rem">📺</span>
          <span class="lib-k-question">${escLibHtml(short || 'транскрипция')}</span>
        </div>
        <div class="lib-k-meta">
          <span class="lib-badge" style="color:#f59e0b;border-color:rgba(245,158,11,.3)">−${amt} токенов</span>
          <span class="lib-badge">user ${tx.chat_id || '—'}</span>
          <span class="lib-k-ttl">${time}</span>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<div class="lib-empty">Ошибка: ${e.message}</div>`;
  }
}
