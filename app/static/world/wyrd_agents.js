const W = window.innerWidth, H = window.innerHeight;

const DC = {
  top:'#ffd700', hq:'#4a9eff', audit:'#ff4444', lib:'#4aff88',
  analytics:'#ffaa00', media:'#aa44ff', money:'#44ff44',
  promo:'#ffcc00', technik:'#888888'
};
const DNAMES = {
  top:'ШЕФ', hq:'ШТАБ HQ', audit:'АУДИТ', lib:'БИБЛИОТЕКА',
  analytics:'АНАЛИТИКА', media:'НЕЙРОЦЕХ', money:'ОТДЕЛ БАБЛА',
  promo:'РЕКЛАМА', technik:'ТЕХНИК'
};
const DPOS = {
  top:       {x:W*.50, y:H*.08},
  hq:        {x:W*.28, y:H*.26},
  audit:     {x:W*.73, y:H*.18},
  lib:       {x:W*.20, y:H*.57},
  analytics: {x:W*.55, y:H*.50},
  media:     {x:W*.18, y:H*.80},
  money:     {x:W*.45, y:H*.80},
  promo:     {x:W*.68, y:H*.74},
  technik:   {x:W*.78, y:H*.52},
};
const LC = {command:'#4a9eff', knowledge:'#4aff88', report:'#ffaa00', money:'#44ff44', content:'#cc44ff'};

// status: live=работает | pause=остановлен | ready=промпт готов | ghost=не создан
const SS = {
  live:  {op:1.00, dash:'',     dot:'#00ff88', label:'LIVE'},
  pause: {op:0.55, dash:'',     dot:'#ffaa00', label:'ПАУЗА'},
  ready: {op:0.72, dash:'5,3',  dot:'#4a9eff', label:'ГОТОВ'},
  ghost: {op:0.16, dash:'3,5',  dot:'#555',    label:'НЕ СОЗДАН'},
};

const NODES = [
  {id:'shef',        e:'👑', n:'ШЕФ',          dept:'top',       s:'live',  d:'Создатель мира. Принимает финальные решения. Всё — для него.'},
  {id:'tomas',       e:'🎙', n:'ТОМАС',         dept:'hq',        s:'live',  d:'Маршрутизатор Штаба. Запускает Совет, патрулирует мир.'},
  {id:'strateg',     e:'🧠', n:'СТРАТЕГ',       dept:'hq',        s:'ready', d:'Думает КАК строить мир. Промпт 100/100. Не запущен.'},
  {id:'arhitektor',  e:'📐', n:'АРХИТЕКТОР',    dept:'hq',        s:'ready', d:'Рисует чертежи, пишет ТЗ. Промпт 100/100. Не запущен.'},
  {id:'kartograf',   e:'🗺', n:'КАРТОГРАФ',     dept:'hq',        s:'ready', d:'Следит за ветками мира. Промпт 100/100. Не запущен.'},
  {id:'kaznachey',   e:'💰', n:'КАЗНАЧЕЙ',      dept:'hq',        s:'ghost', d:'Финансы мира. Не создан. Только паспорт.'},
  {id:'proektniy',   e:'📋', n:'ПРОЕКТНЫЙ',     dept:'hq',        s:'ghost', d:'Управляет проектом от ТЗ до сдачи. Не создан.'},
  {id:'audit',       e:'⚖',  n:'АУДИТ',         dept:'audit',     s:'ghost', d:'Независимый контроль. Только Шефу. Не создан.'},
  {id:'bibliotekar', e:'📖', n:'БИБЛИОТЕКАРЬ',  dept:'lib',       s:'ghost', d:'Единственная точка входа запросов. Не создан.'},
  {id:'arhivarius',  e:'🗄', n:'АРХИВАРИУС',    dept:'lib',       s:'ghost', d:'Знает весь фонд. Управляет читателями. Не создан.'},
  {id:'pisatel',     e:'✍',  n:'ПИСАТЕЛЬ',      dept:'lib',       s:'ghost', d:'Резюмирует и связывает темы. Не создан.'},
  {id:'skrayb',      e:'🌍', n:'СКРАЙБ',        dept:'lib',       s:'live',  d:'✅ Работает. Переводит EN→RU. Западная экспертиза в фонде.'},
  {id:'musorschik',  e:'🧹', n:'МУСОРЩИК',      dept:'lib',       s:'ghost', d:'Чистит дубли и устаревшее. Не создан.'},
  {id:'hugin',       e:'🦅', n:'ХУГИН',         dept:'lib',       s:'live',  d:'✅ Работает. Разведчик. Приносит знания снаружи.'},
  {id:'chitatel',    e:'😴', n:'ЧИТАТЕЛИ×19',   dept:'lib',       s:'pause', d:'⛔ Спят. Созданы, остановлены с 30.05. Резерв.'},
  {id:'profobr',     e:'🎓', n:'ПРОФОБР',       dept:'lib',       s:'ready', d:'Промты Совета 100/100 готовы. Не запущен.'},
  {id:'analitika',   e:'📊', n:'АНАЛИТИКА',     dept:'analytics', s:'ghost', d:'Метрики мира и тренды рынка. Не создан.'},
  {id:'studiya',     e:'🎬', n:'СТУДИЯ',        dept:'media',     s:'pause', d:'⛔ На паузе. Генерирует контент: видео, рилсы, карусели.'},
  {id:'finansy',     e:'🔢', n:'ФИНАНСЫ',       dept:'money',     s:'ghost', d:'Просчёт идей: ROI, стоимость, риски. Не создан.'},
  {id:'ideynyy',     e:'💡', n:'ИДЕЙНЫЙ',       dept:'money',     s:'ghost', d:'Генерирует идеи монетизации из знаний. Не создан.'},
  {id:'reklama',     e:'📣', n:'РЕКЛАМА',       dept:'promo',     s:'ghost', d:'Упаковка и продвижение продуктов. Не создан.'},
  {id:'tehnik',      e:'🔧', n:'ТЕХНИК',        dept:'technik',   s:'pause', d:'⛔ На паузе. Чинит. Только ремонты — стройка это Моз.'},
];

const LINKS = [
  {source:'shef',        target:'tomas',       type:'command'},
  {source:'tomas',       target:'shef',        type:'report'},
  {source:'audit',       target:'shef',        type:'report'},
  {source:'tomas',       target:'strateg',     type:'command'},
  {source:'strateg',     target:'arhitektor',  type:'command'},
  {source:'strateg',     target:'kartograf',   type:'command'},
  {source:'arhitektor',  target:'kaznachey',   type:'command'},
  {source:'arhitektor',  target:'proektniy',   type:'command'},
  {source:'kaznachey',   target:'tomas',       type:'report'},
  {source:'kartograf',   target:'tomas',       type:'report'},
  {source:'proektniy',   target:'audit',       type:'report'},
  {source:'tomas',       target:'bibliotekar', type:'knowledge'},
  {source:'bibliotekar', target:'arhivarius',  type:'knowledge'},
  {source:'arhivarius',  target:'chitatel',    type:'command'},
  {source:'chitatel',    target:'arhivarius',  type:'knowledge'},
  {source:'arhivarius',  target:'pisatel',     type:'knowledge'},
  {source:'pisatel',     target:'bibliotekar', type:'knowledge'},
  {source:'hugin',       target:'bibliotekar', type:'knowledge'},
  {source:'skrayb',      target:'bibliotekar', type:'knowledge'},
  {source:'musorschik',  target:'bibliotekar', type:'report'},
  {source:'profobr',     target:'tomas',       type:'knowledge'},
  {source:'bibliotekar', target:'analitika',   type:'knowledge'},
  {source:'analitika',   target:'tomas',       type:'report'},
  {source:'analitika',   target:'ideynyy',     type:'knowledge'},
  {source:'ideynyy',     target:'finansy',     type:'money'},
  {source:'finansy',     target:'kaznachey',   type:'money'},
  {source:'ideynyy',     target:'studiya',     type:'content'},
  {source:'studiya',     target:'reklama',     type:'content'},
  {source:'tehnik',      target:'tomas',       type:'report'},
];

const nodeById = {};
NODES.forEach(n => nodeById[n.id] = n);

function isGhostLink(l) {
  const sid = l.source.id || l.source;
  const tid = l.target.id || l.target;
  return (nodeById[sid]?.s === 'ghost') || (nodeById[tid]?.s === 'ghost');
}

// SVG setup
const svg = d3.select('#graph').attr('width', W).attr('height', H);
const defs = svg.append('defs');

const glow = defs.append('filter').attr('id','glow');
glow.append('feGaussianBlur').attr('stdDeviation','3').attr('result','blur');
const merge = glow.append('feMerge');
merge.append('feMergeNode').attr('in','blur');
merge.append('feMergeNode').attr('in','SourceGraphic');

Object.entries(LC).forEach(([type, color]) => {
  defs.append('marker').attr('id',`arr-${type}`)
    .attr('viewBox','0 -4 8 8').attr('refX',26).attr('refY',0)
    .attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill',color).attr('opacity',0.8);
});
defs.append('marker').attr('id','arr-ghost')
  .attr('viewBox','0 -4 8 8').attr('refX',26).attr('refY',0)
  .attr('markerWidth',4).attr('markerHeight',4).attr('orient','auto')
  .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#444').attr('opacity',0.5);

// ZOOM
const zoomG = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.15,4]).on('zoom',({transform})=>zoomG.attr('transform',transform));
svg.call(zoom).on('dblclick.zoom',null);
if (W < 700) svg.call(zoom.transform, d3.zoomIdentity.scale(Math.max(0.28, W/1100)));

// Dept zones
const zoneG = zoomG.append('g');
Object.entries(DPOS).forEach(([dept, pos]) => {
  zoneG.append('circle').attr('cx',pos.x).attr('cy',pos.y).attr('r',85)
    .attr('fill',DC[dept]).attr('fill-opacity',0.03)
    .attr('stroke',DC[dept]).attr('stroke-opacity',0.12).attr('stroke-width',1);
  zoneG.append('text').attr('x',pos.x).attr('y',pos.y-72)
    .attr('text-anchor','middle').attr('font-size','7px').attr('letter-spacing','2px')
    .attr('fill',DC[dept]).attr('opacity',0.35).attr('font-family','Courier New')
    .text(DNAMES[dept]);
});

// Links
const linkG = zoomG.append('g');
const linkEls = linkG.selectAll('path').data(LINKS).join('path')
  .attr('class','link')
  .attr('stroke', d => isGhostLink(d) ? '#333' : LC[d.type])
  .attr('opacity', d => isGhostLink(d) ? 0.2 : 0.45)
  .attr('stroke-dasharray', d => isGhostLink(d) ? '4,4' : null)
  .attr('marker-end', d => isGhostLink(d) ? 'url(#arr-ghost)' : `url(#arr-${d.type})`);

// Nodes
const nodeG = zoomG.append('g');
const nodeEls = nodeG.selectAll('g').data(NODES).join('g').style('cursor','pointer');

nodeEls.append('circle').attr('r',22)
  .attr('fill', d => DC[d.dept]+'18')
  .attr('stroke', d => SS[d.s].dash ? '#555' : DC[d.dept])
  .attr('stroke-width', 1.5)
  .attr('stroke-dasharray', d => SS[d.s].dash)
  .attr('opacity', d => SS[d.s].op)
  .attr('filter', d => d.s === 'ghost' ? null : 'url(#glow)');

nodeEls.append('text').attr('class','node-emoji').attr('dy','1px')
  .attr('opacity', d => SS[d.s].op)
  .text(d => d.e);

nodeEls.append('text').attr('class','node-name').attr('dy','34px')
  .attr('fill', d => d.s === 'ghost' ? '#555' : DC[d.dept])
  .attr('opacity', d => SS[d.s].op)
  .text(d => d.n);

// Status dot
nodeEls.append('circle').attr('r',4).attr('cx',16).attr('cy',-16)
  .attr('fill', d => SS[d.s].dot)
  .attr('opacity', d => d.s === 'ghost' ? 0.4 : 0.9)
  .attr('filter', d => d.s === 'live' ? 'url(#glow)' : null);

// Tooltip
const tip = d3.select('#tooltip');
nodeEls
  .on('mouseover',(e,d) => {
    const st = SS[d.s];
    tip.style('display','block')
      .html(`<strong style="color:${DC[d.dept]}">${d.e} ${d.n}</strong>
             <span style="background:${st.dot};color:#000;font-size:8px;padding:1px 5px;border-radius:2px;margin-left:6px">${st.label}</span>
             <br><span style="color:#6a8aaa">${d.d}</span>`)
      .style('left',(e.pageX+14)+'px').style('top',(e.pageY-12)+'px');
    d3.select(e.currentTarget).select('circle').attr('stroke-width',3).attr('r',25);
  })
  .on('mouseout',(e) => {
    tip.style('display','none');
    d3.select(e.currentTarget).select('circle').attr('stroke-width',1.5).attr('r',22);
  });

// Force simulation
const sim = d3.forceSimulation(NODES)
  .force('link', d3.forceLink(LINKS).id(d=>d.id).distance(130).strength(0.25))
  .force('charge', d3.forceManyBody().strength(-280))
  .force('collide', d3.forceCollide(38))
  .force('x', d3.forceX(d => DPOS[d.dept]?.x || W/2).strength(0.35))
  .force('y', d3.forceY(d => DPOS[d.dept]?.y || H/2).strength(0.35));

function arc(d) {
  const dx = d.target.x-d.source.x, dy = d.target.y-d.source.y;
  const r = Math.hypot(dx,dy)*0.75;
  return `M${d.source.x},${d.source.y}A${r},${r} 0 0,1 ${d.target.x},${d.target.y}`;
}
sim.on('tick', () => {
  linkEls.attr('d', arc);
  nodeEls.attr('transform', d => `translate(${d.x},${d.y})`);
});

// Particles — только для живых/паузных связей
const activeLinks = LINKS.filter(l => !isGhostLink(l));
const particles = [];
activeLinks.forEach((lnk, i) => {
  const count = lnk.type === 'knowledge' ? 2 : 1;
  for(let k=0; k<count; k++)
    particles.push({li:i, t:Math.random(), spd:0.0025+Math.random()*0.003});
});

const partG = zoomG.append('g');
const partEls = partG.selectAll('circle').data(particles).join('circle')
  .attr('r',3).attr('filter','url(#glow)')
  .attr('fill', d => LC[activeLinks[d.li].type]);

function ptOnArc(lnk, t) {
  const sx=lnk.source.x||0, sy=lnk.source.y||0;
  const tx=lnk.target.x||0, ty=lnk.target.y||0;
  const mx=(sx+tx)/2, my=(sy+ty)/2;
  const dist=Math.hypot(tx-sx,ty-sy);
  const ang=Math.atan2(ty-sy,tx-sx)+Math.PI/2;
  const bx=mx+Math.cos(ang)*dist*0.35, by=my+Math.sin(ang)*dist*0.35;
  const u=1-t;
  return {x:u*u*sx+2*u*t*bx+t*t*tx, y:u*u*sy+2*u*t*by+t*t*ty};
}
d3.timer(() => {
  particles.forEach(p => { p.t=(p.t+p.spd)%1; });
  partEls
    .attr('cx', d => ptOnArc(activeLinks[d.li], d.t).x)
    .attr('cy', d => ptOnArc(activeLinks[d.li], d.t).y);
});

function zoomBy(k){ svg.transition().duration(260).call(zoom.scaleBy,k); }
function zoomReset(){ svg.transition().duration(320).call(zoom.transform, d3.zoomIdentity.scale(W<700?Math.max(0.28,W/1100):1)); }
