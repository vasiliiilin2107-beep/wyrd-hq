/* ─── АУДИТ МИРА — вкладка 🔍 ─────────────────────────────────── */

async function loadAudit() {
  setStatus('audit-health', '⏳ Загрузка...');

  const LIBRARY_URL = 'http://at23vp1rnqm4koa2ufqvlm0d.147.45.212.155.sslip.io';

  try {
    const [auditRes, agentsRes, councilRes, janitorRes, libStatsRes] = await Promise.all([
      fetch('/audit/status').then(r => r.json()),
      fetch('/civilization/agents').then(r => r.json()),
      fetch('/council/sessions?limit=100').then(r => r.json()),
      fetch(`${LIBRARY_URL}/janitor/status`).then(r => r.json()).catch(() => null),
      fetch(`${LIBRARY_URL}/knowledge/stats`).then(r => r.json()).catch(() => null),
    ]);

    _renderHealth(auditRes);
    _renderAgents(auditRes, agentsRes.agents || []);
    _renderCouncil(councilRes.sessions || []);
    _renderProfessor(agentsRes.agents || []);
    _renderLibrary(janitorRes, libStatsRes);
    _renderLog(auditRes);

  } catch(e) {
    setStatus('audit-health', `<span style="color:var(--red)">❌ Ошибка: ${e.message}</span>`);
  }
}

function _renderHealth(d) {
  if (!d || !d.health) {
    document.getElementById('audit-health').innerHTML =
      '<div style="color:var(--text-dim);font-size:.8rem">Аудит ещё не запускался. Нажми ▶ Запустить.</div>';
    return;
  }
  const isOk = d.health.includes('✅') || d.health.includes('ok');
  const color = isOk ? 'var(--green)' : 'var(--amber)';
  const stale = (d.agents_stale || []);
  document.getElementById('audit-health').innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;background:var(--card);border:1px solid ${color}44;border-radius:8px;padding:14px 16px">
      <span style="font-size:1.4rem">${isOk ? '✅' : '🟡'}</span>
      <div>
        <div style="font-size:.9rem;font-weight:700;color:${color}">${isOk ? 'МИР ЗДОРОВ' : 'ТРЕБУЕТ ВНИМАНИЯ'}</div>
        <div style="font-size:.75rem;color:var(--text-dim);margin-top:2px">
          Агентов: <b style="color:var(--text)">${d.agents_total || 0}</b> &nbsp;|&nbsp;
          Стальных: <b style="color:${stale.length ? 'var(--red)' : 'var(--green)'}">${stale.length}</b>
          ${stale.length ? ' — ' + stale.join(', ') : ''}
          &nbsp;|&nbsp; Проверено: <b style="color:var(--text)">${d.checked_at ? new Date(d.checked_at).toLocaleTimeString('ru') : '—'}</b>
        </div>
      </div>
    </div>`;
}

function _renderAgents(auditData, agents) {
  const stale = new Set(auditData.agents_stale || []);
  const LEVEL_ORDER = { council: 0, foreman: 1, observer: 2, worker: 3 };
  const sorted = [...agents].sort((a, b) => (LEVEL_ORDER[a.level] ?? 9) - (LEVEL_ORDER[b.level] ?? 9));

  const rows = sorted.map(a => {
    const isStale = stale.has(a.name);
    const dot = a.status === 'active' ? '🟢' : isStale ? '🔴' : '🟡';
    const pulse = a.last_pulse
      ? _ago(a.last_pulse)
      : '<span style="color:var(--red)">никогда</span>';
    const lvlColor = { council:'var(--amber)', foreman:'var(--purple)', observer:'var(--blue)', worker:'var(--text-dim)' }[a.level] || 'var(--text-dim)';
    return `<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid var(--border)22;font-size:.75rem">
      <span>${dot}</span>
      <span style="color:${lvlColor};min-width:52px;font-size:.65rem">${a.level}</span>
      <span style="flex:1;color:var(--text);font-weight:600">${a.name}</span>
      <span style="color:var(--text-dim)">${pulse}</span>
    </div>`;
  }).join('');

  document.getElementById('audit-agents').innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.15em;margin-bottom:10px">👥 АГЕНТЫ (${agents.length})</div>
    <div style="max-height:320px;overflow-y:auto">${rows || '<div style="color:var(--text-dim)">Нет данных</div>'}</div>`;
}

function _renderCouncil(sessions) {
  const verdict = sessions.filter(s => s.status === 'verdict');
  const pending = sessions.filter(s => s.status === 'pending' || s.status === 'thinking');
  const done    = sessions.filter(s => s.status === 'done');

  const auditMode = verdict.length >= 10;
  const modeColor = auditMode ? 'var(--red)' : 'var(--green)';
  const modeLabel = auditMode ? '🚨 РЕЖИМ АУДИТА' : '✅ ГЕНЕРАЦИЯ ИДЕЙ';

  const last5 = verdict.slice(0, 5).map(s => `
    <div style="font-size:.72rem;color:var(--text-dim);padding:4px 0;border-bottom:1px solid var(--border)22;line-height:1.4">
      <span style="color:var(--amber)">#${s.id}</span> ${(s.idea_text||'').slice(0,80)}…
    </div>`).join('');

  document.getElementById('audit-council').innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.15em;margin-bottom:10px">🏛️ СОВЕТ</div>
    <div style="display:flex;gap:12px;margin-bottom:10px">
      <div style="text-align:center">
        <div style="font-size:1.4rem;font-weight:800;color:var(--red)">${verdict.length}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">ВИСИТ</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.4rem;font-weight:800;color:var(--amber)">${pending.length}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">В РАБОТЕ</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.4rem;font-weight:800;color:var(--green)">${done.length}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">ГОТОВО</div>
      </div>
    </div>
    <div style="font-size:.72rem;font-weight:700;color:${modeColor};margin-bottom:8px">${modeLabel}</div>
    <div style="font-size:.65rem;color:var(--text-dim);margin-bottom:6px">Последние висящие:</div>
    ${last5 || '<div style="color:var(--text-dim);font-size:.75rem">Чисто 🎉</div>'}`;
}

function _renderProfessor(agents) {
  const prof = agents.find(a => a.name === 'Профессор' || a.name === 'professor');
  const withPassport = agents.filter(a => a.has_passport).length;
  const withoutPassport = agents.filter(a => !a.has_passport).length;

  const profStatus = prof
    ? `<span style="color:var(--green)">${prof.status}</span> | пульс: ${prof.last_pulse ? _ago(prof.last_pulse) : '<span style="color:var(--red)">никогда</span>'}`
    : '<span style="color:var(--red)">не найден</span>';

  const task = prof?.current_task || '—';

  document.getElementById('audit-professor').innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.15em;margin-bottom:10px">🎓 ПРОФЕССОР — СТАРШИЙ ПО БОТАМ</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px">
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--green)">${withPassport}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">С ПАСПОРТОМ</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--red)">${withoutPassport}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">БЕЗ ПАСПОРТА</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--purple)">${agents.length}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">ВСЕГО БОТОВ</div>
      </div>
    </div>
    <div style="font-size:.75rem;color:var(--text-dim)">
      Статус: ${profStatus}<br>
      Задача: <span style="color:var(--text)">${task}</span>
    </div>`;
}

function _renderLibrary(janitor, stats) {
  const el = document.getElementById('audit-library');
  if (!el) return;

  const total = stats?.total ?? '—';
  const byCategory = stats?.by_category || [];

  const lastRun = janitor?.last_run
    ? _ago(janitor.last_run.replace('Z',''))
    : '—';
  const s = janitor?.last_stats || {};
  const ttlDel   = s.ttl_deleted   ?? '—';
  const dedupDel = s.dedup_deleted  ?? '—';
  const synthTrim = s.synthesis_trimmed ?? '—';

  const catRows = byCategory.slice(0, 5).map(c =>
    `<div style="display:flex;justify-content:space-between;font-size:.72rem;padding:2px 0;border-bottom:1px solid var(--border)22">
      <span style="color:var(--text-dim)">${c.category}</span>
      <span style="color:var(--text);font-weight:600">${c.count}</span>
    </div>`
  ).join('');

  el.innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.15em;margin-bottom:10px">📚 БИБЛИОТЕКА — МУСОРЩИК</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px">
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--blue)">${total}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">ЗАПИСЕЙ</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--red)">${ttlDel}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">TTL УДАЛЕНО</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--amber)">${dedupDel}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">ДУБЛЕЙ УБРАНО</div>
      </div>
      <div style="text-align:center">
        <div style="font-size:1.3rem;font-weight:800;color:var(--purple)">${synthTrim}</div>
        <div style="font-size:.65rem;color:var(--text-dim)">СИНТЕЗОВ ОБРЕЗАНО</div>
      </div>
    </div>
    <div style="font-size:.72rem;color:var(--text-dim);margin-bottom:8px">Последний цикл: <b style="color:var(--text)">${lastRun}</b></div>
    <div style="font-size:.65rem;color:var(--text-dim);margin-bottom:4px">ПО КАТЕГОРИЯМ:</div>
    ${catRows || '<div style="color:var(--text-dim);font-size:.72rem">Нет данных</div>'}`;
}

function _renderLog(d) {
  const lines = (d.agent_lines || []);
  if (!lines.length) {
    document.getElementById('audit-log').innerHTML =
      '<div style="color:var(--text-dim);font-size:.8rem">Лог пустой — нажми ▶ Запустить</div>';
    return;
  }
  const html = lines.map(l => {
    const ok = l.includes('✅');
    return `<div style="font-size:.72rem;color:${ok ? 'var(--text-dim)' : 'var(--amber)'};padding:3px 0;font-family:monospace">${l}</div>`;
  }).join('');
  document.getElementById('audit-log').innerHTML = `
    <div style="font-size:.65rem;color:var(--text-dim);letter-spacing:.15em;margin-bottom:8px">📋 ДЕТАЛЬНЫЙ ЛОГ</div>
    <div style="max-height:200px;overflow-y:auto">${html}</div>`;
}

async function runAuditNow() {
  setStatus('audit-health', '⏳ Запускаю аудит...');
  try {
    await fetch('/audit/run', { method: 'POST' });
    await fetch('/trigger/professor', { method: 'POST' });
    setTimeout(loadAudit, 2000);
  } catch(e) {
    setStatus('audit-health', `<span style="color:var(--red)">❌ ${e.message}</span>`);
  }
}

function _ago(iso) {
  const diff = (Date.now() - new Date(iso + 'Z').getTime()) / 1000;
  if (diff < 60)   return `${Math.round(diff)}с назад`;
  if (diff < 3600) return `${Math.round(diff/60)}м назад`;
  if (diff < 86400) return `${Math.round(diff/3600)}ч назад`;
  return `${Math.round(diff/86400)}д назад`;
}

function setStatus(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}
