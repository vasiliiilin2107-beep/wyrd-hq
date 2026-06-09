/* Диспетчер — комната wooden house */
const Dispatcher = (() => {

  async function load() {
    const [statsRes, healthRes] = await Promise.allSettled([
      fetch('/dispatcher-proxy/stats'),
      fetch('/dispatcher-proxy/health'),
    ]);

    const stats = statsRes.status === 'fulfilled' ? await statsRes.value.json() : null;
    const health = healthRes.status === 'fulfilled' ? await healthRes.value.json() : null;

    _renderStatus(health);
    _renderClients(stats);
  }

  function _renderStatus(health) {
    const el = document.getElementById('disp-status-dot');
    if (!el) return;
    if (health && health.status === 'ok') {
      el.style.background = 'var(--status-alive)';
      el.title = `Online · ${health.clients} клиентов`;
    } else {
      el.style.background = 'var(--status-dead)';
      el.title = 'Недоступен';
    }
  }

  function _renderClients(data) {
    const el = document.getElementById('disp-clients-list');
    if (!el) return;
    const clients = data?.clients || [];
    if (!clients.length) {
      el.innerHTML = '<div class="disp-empty">Нет клиентов</div>';
      return;
    }
    el.innerHTML = clients.map(c => {
      const alive = c.leads_today >= 0;
      const dot = alive ? '●' : '○';
      const dotColor = alive ? 'var(--status-alive)' : 'var(--text-muted)';
      const name = _clientName(c.id);
      const icon = _clientIcon(c.id);
      return `
        <div class="disp-client-row">
          <span style="color:${dotColor};font-size:10px">${dot}</span>
          <span class="disp-client-icon">${icon}</span>
          <div class="disp-client-info">
            <div class="disp-client-name">${_e(name)}</div>
            <div class="disp-client-meta">${_e(c.name || c.id)}</div>
          </div>
          <div class="disp-client-leads">
            <span class="disp-leads-num">${c.leads_today}</span>
            <span class="disp-leads-lbl">заявок сегодня</span>
          </div>
        </div>
      `;
    }).join('');
  }

  function _clientName(id) {
    if (id === 'woodenhouse') return 'Домик у реки';
    if (id === 'sanya') return 'Саня Окна';
    return id;
  }

  function _clientIcon(id) {
    if (id === 'woodenhouse') return '🏠';
    if (id === 'sanya') return '🪟';
    return '🏢';
  }

  function _e(s) {
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  return { load };
})();
