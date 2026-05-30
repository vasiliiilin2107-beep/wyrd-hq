const W = window.innerWidth, H = window.innerHeight;

const DC = {
  top:'#ffd700', hq:'#4a9eff', audit:'#ff4444', lib:'#4aff88',
  analytics:'#ffaa00', media:'#aa44ff', money:'#44ff44',
  promo:'#ffcc00', technik:'#888888'
};
const LC = {command:'#4a9eff', knowledge:'#4aff88', report:'#ffaa00', money:'#44ff44', content:'#cc44ff'};

// Fixed grid positions [x%, y%]
const POS = {
  shef:        [.50, .09],
  tomas:       [.33, .20],
  audit:       [.73, .17],
  strateg:     [.12, .33],
  arhitektor:  [.26, .33],
  kartograf:   [.40, .33],
  kaznachey:   [.54, .33],
  proektniy:   [.68, .33],
  bibliotekar: [.06, .50],
  arhivarius:  [.17, .50],
  pisatel:     [.28, .50],
  skrayb:      [.06, .63],
  musorschik:  [.17, .63],
  hugin:       [.28, .63],
  chitatel:    [.39, .57],
  profobr:     [.50, .57],
  analitika:   [.68, .53],
  studiya:     [.12, .80],
  finansy:     [.30, .80],
  ideynyy:     [.46, .80],
  reklama:     [.62, .80],
  tehnik:      [.83, .70],
};

const NODES = [
  {id:'shef',        e:'👑', n:'ШЕФ',          dept:'top',       d:'Создатель мира. Принимает финальные решения.'},
  {id:'tomas',       e:'🎙', n:'ТОМАС',         dept:'hq',        d:'Глаза, уши и голос Шефа. Координирует весь мир.'},
  {id:'strateg',     e:'🧠', n:'СТРАТЕГ',       dept:'hq',        d:'Думает КАК строить мир. Зачем каждая ветка.'},
  {id:'arhitektor',  e:'📐', n:'АРХИТЕКТОР',    dept:'hq',        d:'Рисует чертежи, пишет ТЗ. Закладывает фундамент.'},
  {id:'kartograf',   e:'🗺', n:'КАРТОГРАФ',     dept:'hq',        d:'Следит за ветками. Не даёт уйти в сторону.'},
  {id:'kaznachey',   e:'💰', n:'КАЗНАЧЕЙ',      dept:'hq',        d:'Финансы мира. Будущая внутренняя валюта WYRD.'},
  {id:'proektniy',   e:'📋', n:'ПРОЕКТНЫЙ',     dept:'hq',        d:'Проект от ТЗ до сдачи в Аудит.'},
  {id:'audit',       e:'⚖',  n:'АУДИТ',         dept:'audit',     d:'Независимый контроль. Только Шефу.'},
  {id:'bibliotekar', e:'📖', n:'БИБЛИОТЕКАРЬ',  dept:'lib',       d:'Единственная точка входа. Принимает все запросы.'},
  {id:'arhivarius',  e:'🗄', n:'АРХИВАРИУС',    dept:'lib',       d:'Знает весь фонд. Управляет читателями.'},
  {id:'pisatel',     e:'✍',  n:'ПИСАТЕЛЬ',      dept:'lib',       d:'Резюмирует темы. Делает знание живым.'},
  {id:'skrayb',      e:'🌍', n:'СКРАЙБ',        dept:'lib',       d:'Переводит EN→RU. Западная экспертиза в фонде.'},
  {id:'musorschik',  e:'🧹', n:'МУСОРЩИК',      dept:'lib',       d:'Чистит дубли. Иммунная система библиотеки.'},
  {id:'hugin',       e:'🦅', n:'ХУГИН',         dept:'lib',       d:'Разведчик. Приносит знания снаружи.'},
  {id:'chitatel',    e:'😴', n:'ЧИТАТЕЛИ×19',   dept:'lib',       d:'Ищут по заданию Архивариуса. Спят без задачи.'},
  {id:'profobr',     e:'🎓', n:'ПРОФОБР',       dept:'lib',       d:'Лучшие промты для каждой профессии бота.'},
  {id:'analitika',   e:'📊', n:'АНАЛИТИКА',     dept:'analytics', d:'Метрики и тренды. Данные для всех отделов.'},
  {id:'studiya',     e:'🎬', n:'СТУДИЯ',        dept:'media',     d:'Видео, рилсы, карусели. Производство контента.'},
  {id:'finansy',     e:'🔢', n:'ФИНАНСЫ',       dept:'money',     d:'Просчёт идей: ROI, стоимость, риски.'},
  {id:'ideynyy',     e:'💡', n:'ИДЕЙНЫЙ',       dept:'money',     d:'Генерирует идеи монетизации из знаний.'},
  {id:'reklama',     e:'📣', n:'РЕКЛАМА',       dept:'promo',     d:'Упаковка и продвижение. Изучает площадки.'},
  {id:'tehnik',      e:'🔧', n:'ТЕХНИК',        dept:'technik',   d:'Везде. Нет офиса. Пейджер. Чинит.'},
];

const LINKS = [
  {s:'shef',        t:'tomas',       type:'command'},
  {s:'tomas',       t:'shef',        type:'report'},
  {s:'audit',       t:'shef',        type:'report'},
  {s:'tomas',       t:'strateg',     type:'command'},
  {s:'strateg',     t:'arhitektor',  type:'command'},
  {s:'strateg',     t:'kartograf',   type:'command'},
  {s:'arhitektor',  t:'kaznachey',   type:'command'},
  {s:'arhitektor',  t:'proektniy',   type:'command'},
  {s:'kaznachey',   t:'tomas',       type:'report'},
  {s:'kartograf',   t:'tomas',       type:'report'},
  {s:'proektniy',   t:'audit',       type:'report'},
  {s:'tomas',       t:'bibliotekar', type:'knowledge'},
  {s:'bibliotekar', t:'arhivarius',  type:'knowledge'},
  {s:'arhivarius',  t:'chitatel',    type:'command'},
  {s:'chitatel',    t:'arhivarius',  type:'knowledge'},
  {s:'arhivarius',  t:'pisatel',     type:'knowledge'},
  {s:'pisatel',     t:'bibliotekar', type:'knowledge'},
  {s:'hugin',       t:'bibliotekar', type:'knowledge'},
  {s:'skrayb',      t:'bibliotekar', type:'knowledge'},
  {s:'musorschik',  t:'bibliotekar', type:'report'},
  {s:'profobr',     t:'tomas',       type:'knowledge'},
  {s:'bibliotekar', t:'analitika',   type:'knowledge'},
  {s:'analitika',   t:'tomas',       type:'report'},
  {s:'analitika',   t:'ideynyy',     type:'knowledge'},
  {s:'ideynyy',     t:'finansy',     type:'money'},
  {s:'finansy',     t:'kaznachey',   type:'money'},
  {s:'ideynyy',     t:'studiya',     type:'content'},
  {s:'studiya',     t:'reklama',     type:'content'},
  {s:'tehnik',      t:'tomas',       type:'report'},
];

// Assign positions
const nodeMap = {};
NODES.forEach(n => {
  const p = POS[n.id] || [.5,.5];
  n.x = p[0]*W; n.y = p[1]*H;
  nodeMap[n.id] = n;
});

// Resolve links
const resolvedLinks = LINKS.map(l => ({...l, source: nodeMap[l.s], target: nodeMap[l.t]}));

// SVG
const svg = d3.select('#graph').attr('width',W).attr('height',H);
const defs = svg.append('defs');

// Glow filter
const gf = defs.append('filter').attr('id','glow');
gf.append('feGaussianBlur').attr('stdDeviation','2.5').attr('result','b');
const fm = gf.append('feMerge');
fm.append('feMergeNode').attr('in','b');
fm.append('feMergeNode').attr('in','SourceGraphic');

// Markers
Object.entries(LC).forEach(([type,color]) => {
  defs.append('marker').attr('id',`arr-${type}`)
    .attr('viewBox','0 -4 8 8').attr('refX',54).attr('refY',0)
    .attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill',color).attr('opacity',.8);
});

// Row background bands
const rows = [
  {y:.05, h:.14, label:'ШТАБ HQ', color:'#4a9eff'},
  {y:.19, h:.19, label:'СОВЕТ', color:'#4a9eff'},
  {y:.43, h:.28, label:'БИБЛИОТЕКА', color:'#4aff88'},
  {y:.47, h:.14, label:'АНАЛИТИКА', color:'#ffaa00'},
  {y:.73, h:.13, label:'ПРОИЗВОДСТВО', color:'#aa44ff'},
];
rows.forEach(r => {
  svg.append('rect').attr('x',0).attr('y',r.y*H).attr('width',W).attr('height',r.h*H)
    .attr('fill',r.color).attr('fill-opacity',.018)
    .attr('stroke',r.color).attr('stroke-opacity',.06).attr('stroke-width',1);
  svg.append('text').attr('x',W-16).attr('y',r.y*H+14)
    .attr('text-anchor','end').attr('class','dept-label').attr('fill',r.color).text(r.label);
});

// Links
const linkG = svg.append('g');
function bezier(s,t) {
  const dx = t.x-s.x, dy = t.y-s.y;
  const cx1 = s.x + dx*.4, cy1 = s.y + dy*.1;
  const cx2 = t.x - dx*.4, cy2 = t.y - dy*.1;
  return `M${s.x},${s.y}C${cx1},${cy1},${cx2},${cy2},${t.x},${t.y}`;
}

const linkEls = linkG.selectAll('path').data(resolvedLinks).join('path')
  .attr('class','link')
  .attr('d', d => bezier(d.source, d.target))
  .attr('stroke', d => LC[d.type]).attr('opacity',.4)
  .attr('marker-end', d => `url(#arr-${d.type})`);

// Node squares
const SW=100, SH=48;
const nodeG = svg.append('g');
const nodeEls = nodeG.selectAll('g').data(NODES).join('g')
  .attr('transform', d => `translate(${d.x},${d.y})`).style('cursor','pointer');

nodeEls.append('rect')
  .attr('x',-SW/2).attr('y',-SH/2).attr('width',SW).attr('height',SH)
  .attr('rx',4).attr('ry',4)
  .attr('fill', d => DC[d.dept]+'16')
  .attr('stroke', d => DC[d.dept]).attr('stroke-width',1.5)
  .attr('filter','url(#glow)');

nodeEls.append('text').attr('class','node-emoji').attr('dy','-6px').text(d => d.e);
nodeEls.append('text').attr('class','node-name').attr('dy','10px')
  .attr('fill', d => DC[d.dept]).text(d => d.n);

// Tooltip
const tip = d3.select('#tooltip');
nodeEls
  .on('mouseover',(e,d) => {
    tip.style('display','block')
      .html(`<strong style="color:${DC[d.dept]}">${d.e} ${d.n}</strong><br><span style="color:#6a8aaa">${d.d}</span>`)
      .style('left',(e.pageX+14)+'px').style('top',(e.pageY-12)+'px');
    d3.select(e.currentTarget).select('rect').attr('stroke-width',3).attr('fill', d => DC[d.dept]+'30');
  })
  .on('mouseout',(e,d) => {
    tip.style('display','none');
    d3.select(e.currentTarget).select('rect').attr('stroke-width',1.5).attr('fill', DC[d.dept]+'16');
  });

// Particles
const particles = [];
resolvedLinks.forEach((lnk,i) => {
  const n = lnk.type==='knowledge' ? 2 : 1;
  for(let k=0;k<n;k++) particles.push({li:i, t:Math.random(), spd:.002+Math.random()*.003});
});

const partG = svg.append('g');
const partEls = partG.selectAll('circle').data(particles).join('circle')
  .attr('r',3).attr('filter','url(#glow)')
  .attr('fill', d => LC[resolvedLinks[d.li].type]);

function ptOnBez(lnk, t) {
  const s=lnk.source, tg=lnk.target;
  const dx=tg.x-s.x, dy=tg.y-s.y;
  const cx1=s.x+dx*.4, cy1=s.y+dy*.1;
  const cx2=tg.x-dx*.4, cy2=tg.y-dy*.1;
  const u=1-t;
  return {
    x: u*u*u*s.x + 3*u*u*t*cx1 + 3*u*t*t*cx2 + t*t*t*tg.x,
    y: u*u*u*s.y + 3*u*u*t*cy1 + 3*u*t*t*cy2 + t*t*t*tg.y
  };
}

d3.timer(() => {
  particles.forEach(p => { p.t=(p.t+p.spd)%1; });
  partEls
    .attr('cx', d => ptOnBez(resolvedLinks[d.li], d.t).x)
    .attr('cy', d => ptOnBez(resolvedLinks[d.li], d.t).y);
});
