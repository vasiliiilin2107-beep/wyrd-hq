/* Дворецкий — маршрутизатор действий: агенты с живыми карточками в чате, офис, задачи Технику.
   Вызывается из butler.js: ButlerRouter.execute(d) где d = ответ /butler/chat */

const ButlerRouter = (() => {
  const AGENT_MANIFEST = {
    scout:     {icon: '🔭', name: 'Разведчик'},
    analyst:   {icon: '💡', name: 'Аналитик'},
    conductor: {icon: '🎯', name: 'Дирижёр',    needsSlug: true},
    school:    {icon: '🎓', name: 'Школа',      needsSlug: true},
    readtops:  {icon: '📖', name: 'Читка рынка'},
    thomas:    {icon: '🦉', name: 'Томас'},
    council:   {icon: '🏛', name: 'Совет'},
    library:   {icon: '📚', name: 'Библиотека'},
  };

  function gotoOffice() {
    if (typeof setTab === 'function') {
      const btn = document.querySelector('[data-tab="bookstudio"]');
      setTab('bookstudio', btn || null);
      if (typeof loadBookStudio === 'function') loadBookStudio();
    }
    if (typeof bsOpenOffice === 'function') setTimeout(bsOpenOffice, 350);
  }

  /* Карточка результата агента в чате Дворецкого */
  function _agentResultMsg(a) {
    const msgs = document.getElementById('butler-msgs');
    if (!msgs) return null;
    const div = document.createElement('div');
    div.className = 'butler-msg butler-msg-butler';
    div.innerHTML =
      `<div style="font-weight:700;display:flex;align-items:center;gap:6px">
        <span>${a.icon} ${a.name}</span><span data-st>⏳</span>
      </div>
      <div data-log style="font-size:.68rem;line-height:1.7;color:var(--text-secondary);margin-top:4px;font-family:ui-monospace,monospace"></div>`;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function _cardLine(card, text) {
    const logEl = card.querySelector('[data-log]');
    if (!logEl) return;
    const line = document.createElement('div');
    line.textContent = text;
    if (text.startsWith('✗')) line.style.color = 'var(--status-dead)';
    if (text.startsWith('✓')) line.style.color = 'var(--status-alive)';
    logEl.appendChild(line);
    const msgs = document.getElementById('butler-msgs');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  /* Запуск агента: живая карточка в чате; если чата нет — через офис */
  async function runAgent(d) {
    const a = AGENT_MANIFEST[d.agent];
    const card = _agentResultMsg(a);
    if (!card) {
      if (d.slug && typeof _bsSlug !== 'undefined') _bsSlug = d.slug;
      gotoOffice();
      setTimeout(() => { if (typeof bsOfficeRun === 'function') bsOfficeRun(d.agent); }, 700);
      return;
    }
    try {
      const params = new URLSearchParams();
      if (d.slug) params.set('slug', d.slug);
      if (d.q) params.set('q', d.q);
      const qs = params.toString() ? '?' + params.toString() : '';
      const r = await fetch(`/bs/agent-run/${d.agent}${qs}`, {method: 'POST'});
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || 'HTTP ' + r.status);
      }
      const run = await r.json();
      let since = 0;
      const timer = setInterval(async () => {
        try {
          const t = await fetch(`/agent-log/${run.run_id}/tail?since=${since}`).then(x => { if (!x.ok) throw new Error('HTTP ' + x.status); return x.json(); });
          t.lines.forEach(l => { if (!l.text.startsWith('…')) _cardLine(card, l.text); });
          since = t.next;
          if (t.done) {
            clearInterval(timer);
            const st = card.querySelector('[data-st]');
            if (st) st.textContent = t.ok ? '✓' : '✗';
          }
        } catch (e) {
          clearInterval(timer);
          _cardLine(card, '✗ Лог оборвался: ' + e.message);
        }
      }, 1500);
    } catch (e) {
      _cardLine(card, '✗ Не запустился: ' + e.message);
      const st = card.querySelector('[data-st]');
      if (st) st.textContent = '✗';
    }
  }

  /* Возвращает true если действие обработано */
  function execute(d) {
    if (d.action === 'agent_call' && AGENT_MANIFEST[d.agent]) {
      runAgent(d);
      return true;
    }
    if (d.action === 'navigate' && d.subview === 'office') {
      gotoOffice();
      return true;
    }
    if (d.action === 'create_task') {
      if (typeof showToast === 'function') {
        showToast(d.task_id ? `🔧 Задача #${d.task_id} у Техника` : '🔧 Задача Технику');
      }
      return true;
    }
    return false;
  }

  return { AGENT_MANIFEST, execute, gotoOffice };
})();
