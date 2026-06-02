/* ═══════════════════════════════════════════════════
   WYRD LIVE MAP — живая карта мира
   Данные: /civilization/agents каждые 15 сек
   Нити: толщина и яркость = реальный пульс агентов
═══════════════════════════════════════════════════ */

const BRANCH_COLOR = {
  'аналитика':'#ffaa00', 'идеи':'#a855f7', 'бабло':'#fbbf24',
  'проекты':'#06b6d4',   'строительство':'#64748b', 'образование':'#10b981',
  'global':'#4a9eff',    'наука':'#4aff88', 'контент':'#cc44ff',
  'default':'#94a3b8',
};
const BRANCH_EMOJI = {
  'аналитика':'📊','идеи':'💡','бабло':'💰','проекты':'🏗️',
  'строительство':'🔧','образование':'🎓','global':'👁️',
  'наука':'📚','контент':'🎬','default':'⚡',
};

// Нити мира — кто кому отдаёт данные
const EDGES = [
  // Библиотека → воркеры
  ['library','Разведчик',      '#4aff88','знание'],
  ['library','Генератор',      '#4aff88','знание'],
  ['library','Охотник',        '#4aff88','знание'],
  ['library','Следопыт',       '#4aff88','знание'],
  ['library','Бот-Разведчик',  '#4aff88','знание'],
  // Аналитика: воркеры → бригадир
  ['Счётчик',           'Бригадир Аналитики','#ffaa00','отчёт'],
  ['Разведчик',         'Бригадир Аналитики','#ffaa00','отчёт'],
  ['Критик',            'Бригадир Аналитики','#ffaa00','отчёт'],
  // Идеи: воркеры → бригадир
  ['Генератор',         'Бригадир Идей',     '#a855f7','отчёт'],
  ['Детализатор',       'Бригадир Идей',     '#a855f7','отчёт'],
  ['Оценщик Идей',      'Бригадир Идей',     '#a855f7','отчёт'],
  // Бабло: воркеры → бригадир
  ['Охотник',           'Бригадир Бабла',    '#fbbf24','отчёт'],
  ['Следопыт',          'Бригадир Бабла',    '#fbbf24','отчёт'],
  ['Бот-Разведчик',     'Бригадир Бабла',    '#fbbf24','отчёт'],
  ['Структуролог',      'Бригадир Бабла',    '#fbbf24','отчёт'],
  ['Счетовод',          'Бригадир Бабла',    '#fbbf24','отчёт'],
  ['Приоритизатор',     'Бригадир Бабла',    '#fbbf24','отчёт'],
  // Проекты: воркеры → бригадир
  ['Декомпозер',        'Бригадир Проектов', '#06b6d4','отчёт'],
  ['Синхронизатор',     'Бригадир Проектов', '#06b6d4','отчёт'],
  ['Оценщик Проектов',  'Бригадир Проектов', '#06b6d4','отчёт'],
  // Межотдельные связи
  ['Бригадир Аналитики','Совет',             '#ff6b6b','инсайт'],
  ['Бригадир Идей',     'Совет',             '#ff6b6b','идея'],
  ['Бригадир Бабла',    'Совет',             '#ff6b6b','монетизация'],
  ['Бригадир Бабла',    'Бригадир Идей',     '#fbbf24','идея→банк'],
  ['Совет',             'Бригадир Проектов', '#06b6d4','ТЗ'],
  ['Декомпозер',        'Бригадир Стройки',  '#64748b','задача'],
  ['Профессор',         'Бригадир Идей',     '#10b981','агент'],
  // Томас — центральный нерв
  ['thomas',            'Совет',             '#4a9eff','команда'],
  ['thomas',            'library',           '#4a9eff','запрос'],
  ['Бригадир Аналитики','thomas',            '#4a9eff','рапорт'],
  ['Бригадир Идей',     'thomas',            '#4a9eff','рапорт'],
  ['Бригадир Бабла',    'thomas',            '#4a9eff','рапорт'],
  ['Бригадир Проектов', 'thomas',            '#4a9eff','рапорт'],
];

// Виртуальные узлы (не агенты, но важные сущности)
const VIRTUAL = [
  {name:'Совет',   branch:'global', emoji:'⚖️'},
];

function agentStrength(a) {
  if (!a) return 0.05;
  if (a.status === 'active') return 1.0;
  if (!a.last_pulse) return 0.08;
  const mins = (Date.now() - new Date(a.last_pulse + 'Z').getTime()) / 60000;
  if (mins < 5)   return 0.95;
  if (mins < 30)  return 0.7;
  if (mins < 90)  return 0.4;
  if (mins < 240) return 0.2;
  return 0.06;
}

function edgeStrength(s, t, agentMap) {
  return Math.min(agentStrength(agentMap[s]), agentStrength(agentMap[t]));
}

let sim, svg, g, linkG, nodeG, labelG;
let W = window.innerWidth, H = window.innerHeight;
let agentMap = {}, allNodes = [], lastFetch = 0;
const REFRESH = 15000;

async function fetchWorld() {
  const [agRes, csRes] = await Promise.all([
    fetch('/civilization/agents').then(r=>r.json()).catch(()=>({agents:[]})),
    fetch('/council/sessions?limit=1').then(r=>r.json()).catch(()=>({sessions:[]})),
  ]);
  const agents = agRes.agents || agRes || [];
  agentMap = {};
  agents.forEach(a => { agentMap[a.name] = a; });

  // Совет — виртуальный, статус по последней сессии
  const lastSession = (csRes.sessions || [])[0];
  if (lastSession) {
    const mins = (Date.now() - new Date(lastSession.created_at + 'Z').getTime()) / 60000;
    agentMap['Совет'] = { name:'Совет', status: mins < 90 ? 'active' : 'idle', last_pulse: lastSession.created_at };
  }
  return agents;
}

function buildNodes(agents) {
  const known = new Set();
  const nodes = [];
  agents.forEach(a => {
    known.add(a.name);
    nodes.push({
      id: a.name,
      emoji: BRANCH_EMOJI[a.branch] || BRANCH_EMOJI.default,
      color: BRANCH_COLOR[a.branch] || BRANCH_COLOR.default,
      agent: a,
    });
  });
  VIRTUAL.forEach(v => {
    if (!known.has(v.name)) {
      nodes.push({ id: v.name, emoji: v.emoji, color: BRANCH_COLOR[v.branch], agent: agentMap[v.name] });
    }
  });
  return nodes;
}

function buildLinks(nodes) {
  const ids = new Set(nodes.map(n=>n.id));
  return EDGES.filter(e => ids.has(e[0]) && ids.has(e[1])).map(e => ({
    source: e[0], target: e[1], color: e[2], label: e[3],
  }));
}

function initSVG() {
  svg = d3.select('#graph')
    .attr('width', W).attr('height', H);
  const defs = svg.append('defs');
  // glow filter
  const filt = defs.append('filter').attr('id','glow');
  filt.append('feGaussianBlur').attr('stdDeviation','3').attr('result','blur');
  const merge = filt.append('feMerge');
  merge.append('feMergeNode').attr('in','blur');
  merge.append('feMergeNode').attr('in','SourceGraphic');

  g = svg.append('g');
  linkG  = g.append('g').attr('class','links');
  nodeG  = g.append('g').attr('class','nodes');
  labelG = g.append('g').attr('class','labels');

  svg.call(d3.zoom().scaleExtent([0.3,3])
    .on('zoom', e => g.attr('transform', e.transform)));
}

function renderGraph(agents) {
  const nodes = buildNodes(agents);
  const links = buildLinks(nodes);

  if (!sim) {
    sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d=>d.id).distance(d => {
        // Воркер-бригадир близко, межотдельные дальше
        return d.label === 'отчёт' ? 80 : d.label === 'знание' ? 100 : 160;
      }).strength(0.4))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(W/2, H/2))
      .force('collision', d3.forceCollide(36));
  } else {
    sim.nodes(nodes);
    sim.force('link').links(links);
    sim.alpha(0.3).restart();
  }

  // Links
  const linkSel = linkG.selectAll('.link').data(links, d=>`${d.source.id||d.source}-${d.target.id||d.target}`);
  linkSel.exit().remove();
  const linkEnter = linkSel.enter().append('line').attr('class','link');
  const linkAll = linkEnter.merge(linkSel);

  linkAll.each(function(d) {
    const str = edgeStrength(d.source.id||d.source, d.target.id||d.target, agentMap);
    d3.select(this)
      .attr('stroke', d.color)
      .attr('stroke-opacity', Math.max(0.05, str * 0.85))
      .attr('stroke-width', Math.max(0.3, str * 3.5))
      .attr('stroke-dasharray', str > 0.5 ? null : str > 0.2 ? '6,4' : '2,6');
  });

  // Nodes
  const tooltip = d3.select('#tooltip');
  const nodeSel = nodeG.selectAll('.node').data(nodes, d=>d.id);
  nodeSel.exit().remove();
  const nodeEnter = nodeSel.enter().append('circle').attr('class','node')
    .attr('r', 18)
    .call(d3.drag()
      .on('start', (ev,d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on('drag',  (ev,d) => { d.fx=ev.x; d.fy=ev.y; })
      .on('end',   (ev,d) => { if (!ev.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }))
    .on('mouseover', (ev,d) => {
      const a = d.agent || {};
      const mins = a.last_pulse ? Math.round((Date.now()-new Date(a.last_pulse+'Z').getTime())/60000) : '?';
      tooltip.style('display','block').html(
        `<b>${d.id}</b><br>` +
        `статус: ${a.status||'?'}<br>` +
        `пульс: ${mins} мин назад<br>` +
        (a.current_task ? `задача: ${a.current_task}` : '')
      );
    })
    .on('mousemove', ev => tooltip.style('left',(ev.clientX+14)+'px').style('top',(ev.clientY-10)+'px'))
    .on('mouseout', () => tooltip.style('display','none'));

  const nodeAll = nodeEnter.merge(nodeSel);
  nodeAll.each(function(d) {
    const str = agentStrength(d.agent);
    d3.select(this)
      .attr('fill', d.color + Math.round(str*255).toString(16).padStart(2,'0'))
      .attr('stroke', d.color)
      .attr('stroke-width', str > 0.5 ? 2 : 0.5)
      .attr('stroke-opacity', Math.max(0.15, str))
      .style('filter', str > 0.7 ? 'url(#glow)' : 'none');
  });

  // Emoji labels
  const emojiSel = labelG.selectAll('.emoji').data(nodes, d=>d.id);
  emojiSel.exit().remove();
  const emojiEnter = emojiSel.enter().append('text').attr('class','emoji node-emoji');
  emojiEnter.merge(emojiSel).text(d=>d.emoji);

  const nameSel = labelG.selectAll('.lname').data(nodes, d=>d.id);
  nameSel.exit().remove();
  const nameEnter = nameSel.enter().append('text').attr('class','lname node-name');
  nameEnter.merge(nameSel)
    .text(d => d.id.length > 12 ? d.id.slice(0,11)+'…' : d.id)
    .each(function(d){ d3.select(this).attr('fill', d.color).attr('fill-opacity', Math.max(0.3, agentStrength(d.agent))); });

  sim.on('tick', () => {
    linkAll.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
           .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    nodeAll.attr('cx',d=>d.x).attr('cy',d=>d.y);
    labelG.selectAll('.emoji').attr('x',d=>d.x).attr('y',d=>d.y);
    labelG.selectAll('.lname').attr('x',d=>d.x).attr('y',d=>d.y+28);
  });
}

async function refresh() {
  document.getElementById('status').textContent = '⟳ загрузка...';
  const agents = await fetchWorld();
  allNodes = agents;
  renderGraph(agents);
  document.getElementById('status').textContent =
    '● LIVE · ' + agents.length + ' агентов · ' + new Date().toLocaleTimeString('ru');
  document.getElementById('online-count').textContent =
    agents.filter(a=>a.status==='active').length + '/' + agents.length + ' онлайн';
}

async function startLive() {
  initSVG();
  await refresh();
  setInterval(refresh, REFRESH);
}

window.addEventListener('resize', () => {
  W = window.innerWidth; H = window.innerHeight;
  d3.select('#graph').attr('width',W).attr('height',H);
  if (sim) sim.force('center', d3.forceCenter(W/2,H/2)).alpha(0.1).restart();
});

window.addEventListener('load', startLive);
