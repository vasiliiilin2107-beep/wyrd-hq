/* Дворецкий — маршрутизатор действий: запуск агентов, офис, задачи Технику.
   Вызывается из butler.js: ButlerRouter.execute(d) где d = ответ /butler/chat */

const ButlerRouter = (() => {
  const AGENT_MANIFEST = {
    scout:     {icon: '🔭', name: 'Разведчик'},
    analyst:   {icon: '💡', name: 'Аналитик'},
    conductor: {icon: '🎯', name: 'Дирижёр',     needsSlug: true},
    school:    {icon: '🎓', name: 'Школа',       needsSlug: true},
    readtops:  {icon: '📖', name: 'Читка рынка'},
  };

  function gotoOffice() {
    if (typeof setTab === 'function') {
      const btn = document.querySelector('[data-tab="bookstudio"]');
      setTab('bookstudio', btn || null);
      if (typeof loadBookStudio === 'function') loadBookStudio();
    }
    if (typeof bsOpenOffice === 'function') setTimeout(bsOpenOffice, 350);
  }

  /* Возвращает true если действие обработано */
  function execute(d) {
    if (d.action === 'agent_call' && AGENT_MANIFEST[d.agent]) {
      if (d.slug && typeof _bsSlug !== 'undefined') _bsSlug = d.slug;
      gotoOffice();
      setTimeout(() => { if (typeof bsOfficeRun === 'function') bsOfficeRun(d.agent); }, 700);
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
