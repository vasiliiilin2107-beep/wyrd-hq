/* ─── BUTLER — Дворецкий WYRD ────────────────────────── */

const Butler = (() => {
  let _open = false;
  let _history = [];
  let _orbEl = null;
  let _panelEl = null;
  let _msgsEl = null;
  let _inputEl = null;
  let _autobriefDone = false;

  /* ── DOM ───────────────────────────────────────────── */
  function _getOrb()   { return _orbEl   || (_orbEl   = document.getElementById('butler-orb'));   }
  function _getPanel() { return _panelEl || (_panelEl = document.getElementById('butler-panel')); }
  function _getMsgs()  { return _msgsEl  || (_msgsEl  = document.getElementById('butler-msgs'));  }
  function _getInput() { return _inputEl || (_inputEl = document.getElementById('butler-input')); }

  /* ── ORB STATE ─────────────────────────────────────── */
  function _orbState(state) {
    const orb = _getOrb();
    if (!orb) return;
    orb.className = 'butler-orb ' + (state || 'idle');
  }

  /* ── PANEL TOGGLE ──────────────────────────────────── */
  function togglePanel() {
    _open = !_open;
    const panel = _getPanel();
    if (!panel) return;
    if (_open) {
      panel.classList.add('open');
      const inp = _getInput();
      if (inp) inp.focus();
      if (!_autobriefDone) {
        _autobriefDone = true;
        _autobrief();
      }
    } else {
      panel.classList.remove('open');
    }
  }

  /* ── AUTOBRIEF ─────────────────────────────────────── */
  async function _autobrief() {
    _orbState('speaking');
    _appendMsg('butler', '...');
    try {
      const r = await fetch('/butler/autobrief', { method: 'POST' });
      if (!r.ok) throw new Error(r.status);
      const d = await r.json();
      _replaceLastMsg('butler', d.speech);
      _history.push({ role: 'assistant', content: d.speech });
      if (d.action === 'navigate' && d.tab) _navigate(d.tab);
      if (d.action === 'run' && d.endpoint) _runEndpoint(d.endpoint, d.method);
    } catch (e) {
      _replaceLastMsg('butler', 'Нет связи, Шеф.');
    }
    _orbState('idle');
  }

  /* ── SEND ──────────────────────────────────────────── */
  async function send(text) {
    text = (text || '').trim();
    if (!text) return;
    const inp = _getInput();
    if (inp) inp.value = '';

    _appendMsg('user', text);
    _history.push({ role: 'user', content: text });

    _orbState('speaking');
    _appendMsg('butler', '...');

    try {
      const r = await fetch('/butler/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: _history.slice(-10) }),
      });
      if (!r.ok) throw new Error(r.status);
      const d = await r.json();
      _replaceLastMsg('butler', d.speech);
      _history.push({ role: 'assistant', content: d.speech });
      if (d.action === 'navigate' && d.tab) {
        setTimeout(() => _navigate(d.tab), 300);
      }
      if (d.action === 'run' && d.endpoint) {
        _runEndpoint(d.endpoint, d.method);
      }
    } catch (e) {
      _replaceLastMsg('butler', 'Ошибка связи, Шеф.');
    }
    _orbState('idle');
  }

  /* ── NAVIGATE ──────────────────────────────────────── */
  function _navigate(tab) {
    if (typeof setTab !== 'function') return;
    const btn = document.querySelector(`[data-tab="${tab}"]`);
    setTab(tab, btn || null);
    if (tab === 'bookstudio' && typeof loadBookStudio === 'function') loadBookStudio();
    if (tab === 'library'    && typeof loadLibrary    === 'function') loadLibrary();
    if (tab === 'civilization' && typeof loadCivilization === 'function') loadCivilization();
    if (tab === 'world'      && typeof loadWorld      === 'function') loadWorld();
  }

  /* ── RUN ENDPOINT ──────────────────────────────────── */
  async function _runEndpoint(endpoint, method) {
    try {
      await fetch(endpoint, { method: method || 'POST' });
    } catch (e) {
      console.warn('butler run endpoint error', e);
    }
  }

  /* ── MESSAGE DOM ───────────────────────────────────── */
  function _appendMsg(role, text) {
    const msgs = _getMsgs();
    if (!msgs) return;
    const div = document.createElement('div');
    div.className = 'butler-msg butler-msg-' + role;
    div.innerHTML = _escHtml(text).replace(/\n/g, '<br>');
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function _replaceLastMsg(role, text) {
    const msgs = _getMsgs();
    if (!msgs) return;
    const last = msgs.querySelector('.butler-msg-' + role + ':last-of-type');
    if (last) {
      last.innerHTML = _escHtml(text).replace(/\n/g, '<br>');
    } else {
      _appendMsg(role, text);
    }
    msgs.scrollTop = msgs.scrollHeight;
  }

  function _escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── INPUT KEY ─────────────────────────────────────── */
  function inputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const inp = _getInput();
      send(inp ? inp.value : '');
    }
  }

  /* ── INIT ──────────────────────────────────────────── */
  function init() {
    setTimeout(() => {
      const orb = _getOrb();
      if (orb) {
        orb.style.opacity = '0';
        orb.style.transform = 'scale(0)';
        orb.style.transition = 'opacity 0.3s ease, transform 0.3s cubic-bezier(0.16,1,0.3,1)';
        requestAnimationFrame(() => requestAnimationFrame(() => {
          orb.style.opacity = '1';
          orb.style.transform = 'scale(1)';
        }));
      }
    }, 800);
  }

  return { init, togglePanel, send, inputKey };
})();

document.addEventListener('DOMContentLoaded', () => Butler.init());
