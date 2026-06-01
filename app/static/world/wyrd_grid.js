const W = window.innerWidth, H = window.innerHeight;

const DC = {
  top:'#ffd700', hq:'#4a9eff', audit:'#ff4444', lib:'#4aff88',
  analytics:'#ffaa00', media:'#aa44ff', money:'#44ff44',
  promo:'#ffcc00', technik:'#888888', build:'#ff8800'
};
const LC = {command:'#4a9eff', knowledge:'#4aff88', report:'#ffaa00', money:'#44ff44', content:'#cc44ff'};
const SS = {
  live:    {op:1.00, dash:'',    dot:'#00ff88', label:'LIVE'},
  pause:   {op:0.55, dash:'',    dot:'#ffaa00', label:'ПАУЗА'},
  ready:   {op:0.72, dash:'5,3', dot:'#4a9eff', label:'ГОТОВ'},
  pending: {op:0.85, dash:'4,2', dot:'#ff8800', label:'СТРОИТСЯ'},
  ghost:   {op:0.16, dash:'3,5', dot:'#555',    label:'НЕ СОЗДАН'},
};

const POS = {
  shef:[.50,.09], tomas:[.33,.20], audit:[.73,.17],
  strateg:[.12,.33], arhitektor:[.26,.33], kartograf:[.40,.33],
  kaznachey:[.54,.33], proektniy:[.68,.33],
  bibliotekar:[.06,.50], arhivarius:[.17,.50], pisatel:[.28,.50],
  skrayb:[.06,.63], musorschik:[.17,.63], hugin:[.28,.63],
  chitatel:[.39,.57], profobr:[.50,.57],
  analitika:[.68,.53],
  studiya:[.12,.80], finansy:[.30,.80], ideynyy:[.46,.80], reklama:[.62,.80],
  tehnik:[.83,.70],
  wyrd_insta:[.20,.92], wyrd_income:[.46,.92],
};

const NODES = [
  {id:'shef',        e:'👑', n:'ШЕФ',           dept:'top',       s:'live',    d:'Создатель мира. Принимает финальные решения.'},
  {id:'tomas',       e:'🎙', n:'ТОМАС',          dept:'hq',        s:'pause',   d:'Глаза, уши и голос Шефа. ⛔ На паузе с 30.05.'},
  {id:'strateg',     e:'🧠', n:'СТРАТЕГ',        dept:'hq',        s:'ready',   d:'Думает КАК строить мир. Промпт 100/100.'},
  {id:'arhitektor',  e:'📐', n:'АРХИТЕКТОР',     dept:'hq',        s:'ready',   d:'Рисует чертежи, пишет ТЗ. Промпт 100/100.'},
  {id:'kartograf',   e:'🗺', n:'КАРТОГРАФ',      dept:'hq',        s:'ready',   d:'Следит за ветками мира. Промпт 100/100.'},
  {id:'kaznachey',   e:'💰', n:'КАЗНАЧЕЙ',       dept:'hq',        s:'ghost',   d:'Финансы мира. Не создан.'},
  {id:'proektniy',   e:'📋', n:'ПРОЕКТНЫЙ',      dept:'hq',        s:'ghost',   d:'Управляет проектом от ТЗ до сдачи. Не создан.'},
  {id:'audit',       e:'⚖',  n:'АУДИТ',          dept:'audit',     s:'ghost',   d:'Независимый контроль. Только Шефу. Не создан.'},
  {id:'bibliotekar', e:'📖', n:'БИБЛИОТЕКАРЬ',   dept:'lib',       s:'ghost',   d:'Единственная точка входа запросов. Не создан.'},
  {id:'arhivarius',  e:'🗄', n:'АРХИВАРИУС',     dept:'lib',       s:'live',    d:'✅ Работает в wyrd-library. Знает весь фонд. Управляет читателями.'},
  {id:'pisatel',     e:'✍',  n:'ПИСАТЕЛЬ',       dept:'lib',       s:'live',    d:'✅ Работает в wyrd-library. Резюмирует и связывает темы.'},
  {id:'skrayb',      e:'🌍', n:'СКРАЙБ',         dept:'lib',       s:'live',    d:'✅ Работает. Переводит EN→RU.'},
  {id:'musorschik',  e:'🧹', n:'МУСОРЩИК',       dept:'lib',       s:'ghost',   d:'Чистит дубли. Не создан.'},
  {id:'hugin',       e:'🦅', n:'ХУГИН',          dept:'lib',       s:'live',    d:'✅ Работает. Разведчик. Приносит знания снаружи.'},
  {id:'chitatel',    e:'😴', n:'ЧИТАТЕЛИ×19',    dept:'lib',       s:'pause',   d:'⛔ Спят. Остановлены с 30.05.'},
  {id:'profobr',     e:'🎓', n:'ПРОФОБР',        dept:'lib',       s:'ready',   d:'Промты Совета 100/100 готовы.'},
  {id:'analitika',   e:'📊', n:'АНАЛИТИКА',      dept:'analytics', s:'ghost',   d:'Метрики и тренды. Не создан.'},
  {id:'studiya',     e:'🎬', n:'СТУДИЯ',         dept:'media',     s:'pause',   d:'⛔ На паузе. Видео, рилсы, карусели.'},
  {id:'finansy',     e:'🔢', n:'ФИНАНСЫ',        dept:'money',     s:'ghost',   d:'Просчёт идей. Не создан.'},
  {id:'ideynyy',     e:'💡', n:'ИДЕЙНЫЙ',        dept:'money',     s:'ghost',   d:'Генерирует идеи монетизации. Не создан.'},
  {id:'reklama',     e:'📣', n:'РЕКЛАМА',        dept:'promo',     s:'ghost',   d:'Упаковка и продвижение. Не создан.'},
  {id:'tehnik',      e:'🔧', n:'ТЕХНИК',         dept:'technik',   s:'pause',   d:'⛔ На паузе. Только ремонты.'},
  {id:'wyrd_insta',  e:'📸', n:'WYRD INSTAGRAM', dept:'build',     s:'pending', d:'🔨 Строится. Карусели EU→RU и RU→EN.'},
  {id:'wyrd_income', e:'💸', n:'WYRD INCOME',    dept:'build',     s:'pending', d:'🔨 Строится. 3 бота: Генератор→Оценщик→Аналитик.'},
];

const LINKS = [
  {s:'shef',        t:'tomas',        type:'command'},
  {s:'tomas',       t:'shef',         type:'report'},
  {s:'audit',       t:'shef',         type:'report'},
  {s:'tomas',       t:'strateg',      type:'command'},
  {s:'strateg',     t:'arhitektor',   type:'command'},
  {s:'strateg',     t:'kartograf',    type:'command'},
  {s:'arhitektor',  t:'kaznachey',    type:'command'},
  {s:'arhitektor',  t:'proektniy',    type:'command'},
  {s:'kaznachey',   t:'tomas',        type:'report'},
  {s:'kartograf',   t:'tomas',        type:'report'},
  {s:'proektniy',   t:'audit',        type:'report'},
  {s:'tomas',       t:'bibliotekar',  type:'knowledge'},
  {s:'bibliotekar', t:'arhivarius',   type:'knowledge'},
  {s:'arhivarius',  t:'chitatel',     type:'command'},
  {s:'chitatel',    t:'arhivarius',   type:'knowledge'},
  {s:'arhivarius',  t:'pisatel',      type:'knowledge'},
  {s:'pisatel',     t:'bibliotekar',  type:'knowledge'},
  {s:'hugin',       t:'bibliotekar',  type:'knowledge'},
  {s:'skrayb',      t:'bibliotekar',  type:'knowledge'},
  {s:'musorschik',  t:'bibliotekar',  type:'report'},
  {s:'profobr',     t:'tomas',        type:'knowledge'},
  {s:'bibliotekar', t:'analitika',    type:'knowledge'},
  {s:'analitika',   t:'tomas',        type:'report'},
  {s:'analitika',   t:'ideynyy',      type:'knowledge'},
  {s:'ideynyy',     t:'finansy',      type:'money'},
  {s:'finansy',     t:'kaznachey',    type:'money'},
  {s:'ideynyy',     t:'studiya',      type:'content'},
  {s:'studiya',     t:'reklama',      type:'content'},
  {s:'tehnik',      t:'tomas',        type:'report'},
  {s:'kartograf',   t:'wyrd_insta',   type:'command'},
  {s:'wyrd_insta',  t:'studiya',      type:'content'},
  {s:'wyrd_insta',  t:'tomas',        type:'report'},
  {s:'kartograf',   t:'wyrd_income',  type:'command'},
  {s:'wyrd_income', t:'ideynyy',      type:'knowledge'},
  {s:'wyrd_income', t:'tomas',        type:'report'},
];

// Позиции
const nodeMap = {};
NODES.forEach(n => {
  const p = POS[n.id] || [.5,.5];
  n.x = p[0]*W; n.y = p[1]*H;
  nodeMap[n.id] = n;
});

function isGhost(l) {
  return (nodeMap[l.s]?.s === 'ghost') || (nodeMap[l.t]?.s === 'ghost');
}
function isPending(l) {
  return !isGhost(l) && ((nodeMap[l.s]?.s === 'pending') || (nodeMap[l.t]?.s === 'pending'));
}

// Квадратичная дуга — контрольная точка перпендикулярно середине
function makeArc(s, t) {
  const mx = (s.x+t.x)/2, my = (s.y+t.y)/2;
  const dist = Math.hypot(t.x-s.x, t.y-s.y);
  const ang = Math.atan2(t.y-s.y, t.x-s.x) + Math.PI/2;
  const bend = dist * 0.28;
  const cx = mx + Math.cos(ang)*bend;
  const cy = my + Math.sin(ang)*bend;
  return {d:`M${s.x},${s.y}Q${cx},${cy} ${t.x},${t.y}`, cx, cy};
}

const resolvedLinks = LINKS.map(l => {
  const src = nodeMap[l.s], tgt = nodeMap[l.t];
  const arc = makeArc(src, tgt);
  return {...l, source:src, target:tgt, cx:arc.cx, cy:arc.cy, path:arc.d};
});

// SVG
const svg = d3.select('#graph').attr('width',W).attr('height',H);
const defs = svg.append('defs');

const gf = defs.append('filter').attr('id','glow');
gf.append('feGaussianBlur').attr('stdDeviation','2.5').attr('result','b');
const fm = gf.append('feMerge');
fm.append('feMergeNode').attr('in','b');
fm.append('feMergeNode').attr('in','SourceGraphic');

const gfS = defs.append('filter').attr('id','glow-s');
gfS.append('feGaussianBlur').attr('stdDeviation','5').attr('result','b');
const fmS = gfS.append('feMerge');
fmS.append('feMergeNode').attr('in','b');
fmS.append('feMergeNode').attr('in','SourceGraphic');

// Маркеры стрелок — refX подобран под центр панели
Object.entries(LC).forEach(([type,color]) => {
  defs.append('marker').attr('id',`arr-${type}`)
    .attr('viewBox','0 -4 8 8').attr('refX',48).attr('refY',0)
    .attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill',color).attr('opacity',.85);
});
defs.append('marker').attr('id','arr-ghost')
  .attr('viewBox','0 -4 8 8').attr('refX',48).attr('refY',0)
  .attr('markerWidth',4).attr('markerHeight',4).attr('orient','auto')
  .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#333').attr('opacity',.4);

// ZOOM
const zoomG = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.15,4]).on('zoom',({transform})=>zoomG.attr('transform',transform));
svg.call(zoom).on('dblclick.zoom',null);
if (W < 700) svg.call(zoom.transform, d3.zoomIdentity.scale(Math.max(0.28, W/1100)));

// СЛОЙ 1 — Этажи-отделы (здание снизу)
const FLOORS = [
  {y:.05, h:.14, label:'ШТАБ HQ',      color:'#4a9eff'},
  {y:.19, h:.19, label:'СОВЕТ',         color:'#4a9eff'},
  {y:.43, h:.28, label:'БИБЛИОТЕКА',    color:'#4aff88'},
  {y:.47, h:.14, label:'АНАЛИТИКА',     color:'#ffaa00'},
  {y:.73, h:.13, label:'ПРОИЗВОДСТВО',  color:'#aa44ff'},
  {y:.88, h:.10, label:'СТРОИТЕЛЬСТВО', color:'#ff8800'},
];
FLOORS.forEach(f => {
  zoomG.append('rect').attr('x',0).attr('y',f.y*H).attr('width',W).attr('height',f.h*H)
    .attr('fill',f.color).attr('fill-opacity',.022)
    .attr('stroke',f.color).attr('stroke-opacity',.08).attr('stroke-width',1);
  zoomG.append('text').attr('x',W-14).attr('y',f.y*H+14)
    .attr('text-anchor','end').attr('class','dept-label').attr('fill',f.color).text(f.label);
});

// СЛОЙ 2 — Паутина связей
const linkG = zoomG.append('g');
const linkEls = linkG.selectAll('path').data(resolvedLinks).join('path')
  .attr('class','link')
  .attr('d', d => d.path)
  .attr('stroke', d => isGhost(d) ? '#2a2a2a' : LC[d.type])
  .attr('opacity', d => isGhost(d) ? 0.15 : isPending(d) ? 0.38 : 0.42)
  .attr('stroke-dasharray', d => isGhost(d) ? '4,5' : isPending(d) ? '7,3' : null)
  .attr('stroke-width', 1.2)
  .attr('marker-end', d => isGhost(d) ? 'url(#arr-ghost)' : `url(#arr-${d.type})`);

// СЛОЙ 3 — Панели агентов
// Форма: терминал-карточка — основа + цветная шапка-заголовок
const PW = 96, PH = 44, PH_HEAD = 12;
const nodeG = zoomG.append('g');
const nodeEls = nodeG.selectAll('g').data(NODES).join('g')
  .attr('transform', d => `translate(${d.x},${d.y})`).style('cursor','pointer');

// Основа панели
nodeEls.append('rect')
  .attr('x',-PW/2).attr('y',-PH/2).attr('width',PW).attr('height',PH).attr('rx',3)
  .attr('fill', d => DC[d.dept]+'10')
  .attr('stroke', d => d.s==='ghost' ? '#2a3040' : DC[d.dept])
  .attr('stroke-width', 1.2)
  .attr('stroke-dasharray', d => SS[d.s].dash)
  .attr('opacity', d => SS[d.s].op)
  .attr('filter', d => d.s==='ghost' ? null : 'url(#glow)');

// Шапка-заголовок (цветная полоса сверху — как брендинг отдела)
const headerEls = nodeEls.append('rect')
  .attr('x',-PW/2).attr('y',-PH/2).attr('width',PW).attr('height',PH_HEAD).attr('rx',3)
  .attr('fill', d => DC[d.dept])
  .attr('opacity', d => d.s==='ghost' ? 0.06 : 0.28);

// Эмодзи в шапке
nodeEls.append('text').attr('class','node-emoji')
  .attr('dy', -PH/2 + PH_HEAD/2 + 1 + 'px').attr('font-size','9px')
  .attr('opacity', d => SS[d.s].op).text(d => d.e);

// Имя под шапкой
nodeEls.append('text').attr('class','node-name')
  .attr('dy','10px').attr('font-size','7px')
  .attr('fill', d => d.s==='ghost' ? '#444' : DC[d.dept])
  .attr('opacity', d => SS[d.s].op).text(d => d.n);

// Статус-LED (правый верхний угол)
const dotEls = nodeEls.append('circle').attr('r',4).attr('cx',PW/2-5).attr('cy',-PH/2+6)
  .attr('fill', d => SS[d.s].dot)
  .attr('opacity', d => d.s==='ghost' ? 0.3 : 1.0)
  .attr('filter', d => d.s==='live' ? 'url(#glow)' : null);

// Кэш pending
const pendingBases   = nodeEls.filter(d => d.s==='pending').select('rect');
const pendingHeaders = headerEls.filter(d => d.s==='pending');
const pendingDots    = dotEls.filter(d => d.s==='pending');

// Tooltip
const tip = d3.select('#tooltip');
nodeEls
  .on('mouseover',(e,d) => {
    const st = SS[d.s];
    tip.style('display','block')
      .html(`<strong style="color:${DC[d.dept]}">${d.e} ${d.n}</strong>
             <span style="background:${st.dot};color:#000;font-size:8px;padding:1px 5px;border-radius:2px;margin-left:5px">${st.label}</span>
             <br><span style="color:#6a8aaa">${d.d}</span>`)
      .style('left',(e.pageX+14)+'px').style('top',(e.pageY-12)+'px');
    if (!focusId) d3.select(e.currentTarget).select('rect').attr('stroke-width',2.5);
  })
  .on('mouseout',(e,d) => {
    tip.style('display','none');
    if (!focusId || focusId!==d.id) d3.select(e.currentTarget).select('rect').attr('stroke-width',1.2);
  });

// ФОКУС-РЕЖИМ
let focusId = null;
function connectedSet(id) {
  const s = new Set([id]);
  resolvedLinks.forEach(l => { if(l.s===id) s.add(l.t); if(l.t===id) s.add(l.s); });
  return s;
}
function applyFocus(id) {
  focusId = id;
  const hint = document.getElementById('focus-hint');
  if (!id) {
    linkEls.attr('opacity', d => isGhost(d)?0.15:isPending(d)?0.38:0.42).attr('stroke-width',1.2);
    nodeEls.style('opacity', null);
    partEls.attr('opacity', 1);
    if (hint) hint.style.opacity='0';
    return;
  }
  const conn = connectedSet(id);
  linkEls
    .attr('opacity', d => (d.s===id||d.t===id) ? 0.95 : 0.03)
    .attr('stroke-width', d => (d.s===id||d.t===id) ? 2.8 : 1.2);
  nodeEls.style('opacity', d => conn.has(d.id) ? null : '0.05');
  partEls.attr('opacity', d => { const l=activeLinks[d.li]; return (l.s===id||l.t===id)?1:0; });
  if (hint) { hint.textContent=`◉ ${nodeMap[id].n} · клик ещё раз = сброс`; hint.style.opacity='1'; }
}
nodeEls.on('click',(e,d) => { tip.style('display','none'); applyFocus(focusId===d.id?null:d.id); });

// Частицы по дугам
const activeLinks = resolvedLinks.filter(l => !isGhost(l));
const particles = [];
activeLinks.forEach((lnk,i) => {
  const n = lnk.type==='knowledge'?2:1;
  for(let k=0;k<n;k++) particles.push({li:i, t:Math.random(), spd:.002+Math.random()*.003});
});
const partG = zoomG.append('g');
const partEls = partG.selectAll('circle').data(particles).join('circle')
  .attr('r',3).attr('filter','url(#glow)')
  .attr('fill', d => LC[activeLinks[d.li].type]);

function ptOnQuad(lnk, t) {
  const s=lnk.source, tg=lnk.target, u=1-t;
  return {
    x: u*u*s.x + 2*u*t*lnk.cx + t*t*tg.x,
    y: u*u*s.y + 2*u*t*lnk.cy + t*t*tg.y
  };
}

d3.timer(() => {
  const now = Date.now()/1000;
  const pulse = 0.3 + 0.7*(0.5 + 0.5*Math.sin(now*2.3));

  pendingBases.attr('opacity', pulse).attr('stroke-width', 1.2 + pulse*2).attr('filter', pulse>0.65?'url(#glow-s)':'url(#glow)');
  pendingHeaders.attr('opacity', pulse*0.4);
  pendingDots.attr('opacity', pulse);

  particles.forEach(p => { p.t=(p.t+p.spd)%1; });
  partEls.attr('cx', d=>ptOnQuad(activeLinks[d.li],d.t).x).attr('cy', d=>ptOnQuad(activeLinks[d.li],d.t).y);
});

function zoomBy(k){ svg.transition().duration(260).call(zoom.scaleBy,k); }
function zoomReset(){ svg.transition().duration(320).call(zoom.transform, d3.zoomIdentity.scale(W<700?Math.max(0.28,W/1100):1)); }
