const W = window.innerWidth, H = window.innerHeight;

const LC = {command:'#4a9eff',knowledge:'#4aff88',report:'#ffaa00',money:'#44ff44',content:'#cc44ff'};
const SS = {
  live:    {op:1.00, dash:'',    dot:'#00ff88', label:'LIVE'},
  pause:   {op:0.55, dash:'',    dot:'#ffaa00', label:'ПАУЗА'},
  ready:   {op:0.72, dash:'5,3', dot:'#4a9eff', label:'ГОТОВ'},
  pending: {op:0.85, dash:'4,2', dot:'#ff8800', label:'СТРОИТСЯ'},
  ghost:   {op:0.16, dash:'3,5', dot:'#555',    label:'НЕ СОЗДАН'},
};

const AGENTS = [
  {id:'shef',       e:'👑',n:'ШЕФ',           room:null,    s:'live',  d:'Создатель мира. Принимает финальные решения.'},
  // ШТАБ HQ
  {id:'tomas',      e:'🎙',n:'ТОМАС',          room:'hq',    s:'live',  d:'Маршрутизатор Штаба. Запускает Совет, патрулирует мир.',         db:'thomas'},
  {id:'professor',  e:'🎓',n:'ПРОФЕССОР',      room:'hq',    s:'live',  d:'Рождает и обучает новых агентов мира WYRD.',                     db:'Профессор'},
  {id:'strateg',    e:'🧠',n:'СТРАТЕГ',        room:'hq',    s:'ready', d:'Думает КАК строить мир. Промпт 100/100.'},
  {id:'arhitektor', e:'📐',n:'АРХИТЕКТОР',     room:'hq',    s:'ready', d:'Рисует чертежи, пишет ТЗ. Промпт 100/100.'},
  {id:'kartograf',  e:'🗺',n:'КАРТОГРАФ',      room:'hq',    s:'ready', d:'Следит за ветками мира. Промпт 100/100.'},
  {id:'kaznachey',  e:'💰',n:'КАЗНАЧЕЙ',       room:'hq',    s:'ghost', d:'Финансы мира. Ф5 — ещё не создан.'},
  // АУДИТ
  {id:'audit',      e:'⚖', n:'АУДИТ',          room:'audit', s:'ghost', d:'Независимый контроль. Только Шефу.'},
  // БИБЛИОТЕКА
  {id:'skrayb',     e:'🌍',n:'СКРАЙБ',         room:'lib',   s:'live',  d:'Переводит EN→RU видео в Библиотеку.',                           db:'scribe'},
  {id:'chitatel',   e:'😴',n:'ЧИТАТЕЛИ×19',    room:'lib',   s:'pause', d:'⛔ Спят. Остановлены с 30.05.'},
  {id:'profobr',    e:'📚',n:'ПРОФОБР',        room:'lib',   s:'live',  d:'Промпты Совета 100/100 готовы.'},
  {id:'hugin',      e:'🦅',n:'ХУГИН',          room:'lib',   s:'ready', d:'Разведчик снаружи. Горит когда активен.'},
  // АНАЛИТИКА
  {id:'br_anlt',    e:'📊',n:'БР.АНАЛИТИКИ',  room:'anlt',  s:'live',  d:'Координирует аналитику мира WYRD.',                             db:'Бригадир Аналитики'},
  {id:'schetik',    e:'📈',n:'СЧЁТЧИК',        room:'anlt',  s:'live',  d:'Внутренние метрики и аномалии.',                                db:'Счётчик'},
  {id:'razvedchik', e:'🔭',n:'РАЗВЕДЧИК',      room:'anlt',  s:'live',  d:'Внешние тренды и окна возможностей.',                           db:'Разведчик'},
  {id:'kritik',     e:'⚡',n:'КРИТИК',         room:'anlt',  s:'live',  d:'Стресс-тест идей и вердиктов Совета.',                          db:'Критик'},
  // ТЕХНИК
  {id:'tehnik',     e:'🔧',n:'ТЕХНИК',         room:'tech',  s:'pause', d:'⛔ На паузе. Только ремонты, стройка — это Моз.',               db:'technik'},
  // ОТДЕЛ БАБЛА
  {id:'br_babla',   e:'💼',n:'БР.БАБЛА',      room:'babla', s:'live',  d:'Координирует бизнес-разведку.',                                 db:'Бригадир Бабла'},
  {id:'sledopyt',   e:'🔍',n:'СЛЕДОПЫТ',       room:'babla', s:'live',  d:'Денежные потоки людей (платформы, ниши, схемы).',               db:'Следопыт'},
  {id:'bot_razv',   e:'🤖',n:'БОТ-РАЗВ.',     room:'babla', s:'live',  d:'Монетизация ботов и AI (SaaS, API, автоматизация).',            db:'Бот-Разведчик'},
  {id:'struktur',   e:'🏗',n:'СТРУКТУРОЛОГ',   room:'babla', s:'live',  d:'Бизнес-модели и unit economics.',                               db:'Структуролог'},
  {id:'ohotnik',    e:'🎯',n:'ОХОТНИК',        room:'babla', s:'live',  d:'Монетизационные окна из Библиотеки.',                           db:'Охотник'},
  {id:'schetovod',  e:'🧮',n:'СЧЕТОВОД',       room:'babla', s:'live',  d:'Анализ экспериментов и ROI.',                                   db:'Счетовод'},
  {id:'prioritiz',  e:'⚖️',n:'ПРИОРИТИЗАТОР', room:'babla', s:'live',  d:'Приоритизация денежных возможностей.',                          db:'Приоритизатор'},
  // ИДЕЙНЫЙ
  {id:'br_idei',    e:'💡',n:'БР.ИДЕЙ',       room:'ideyny',s:'live',  d:'Координирует генерацию и оценку идей.',                         db:'Бригадир Идей'},
  {id:'generator',  e:'✨',n:'ГЕНЕРАТОР',      room:'ideyny',s:'live',  d:'Генерирует идеи из трендов Библиотеки.',                        db:'Генератор'},
  {id:'detaliz',    e:'🔬',n:'ДЕТАЛИЗАТОР',    room:'ideyny',s:'live',  d:'Детализирует идеи до конкретных шагов.',                        db:'Детализатор'},
  {id:'ocen_idei',  e:'🏆',n:'ОЦЕНЩИК ИД.',   room:'ideyny',s:'live',  d:'Приоритизирует и оценивает банк идей.',                         db:'Оценщик Идей'},
  // ПРОЕКТНЫЙ
  {id:'br_proekt',  e:'📋',n:'БР.ПРОЕКТОВ',   room:'proekt',s:'live',  d:'Координирует проектирование и оценку рисков.',                  db:'Бригадир Проектов'},
  {id:'decomp',     e:'🧩',n:'ДЕКОМПОЗЕР',     room:'proekt',s:'live',  d:'Декомпозиция ТЗ на атомарные задачи.',                          db:'Декомпозер'},
  {id:'sinhron',    e:'🔄',n:'СИНХРОНИЗАТОР',  room:'proekt',s:'live',  d:'Проверка конфликтов в архитектуре.',                            db:'Синхронизатор'},
  {id:'ocen_pr',    e:'📏',n:'ОЦЕНЩИК ПР.',    room:'proekt',s:'live',  d:'Оценка сложности и рисков проектов.',                           db:'Оценщик Проектов'},
  // ПРОИЗВОДСТВО
  {id:'studiya',    e:'🎬',n:'СТУДИЯ',         room:'prod',  s:'pause', d:'⛔ На паузе. Видео, рилсы, карусели.',                          db:'studio'},
  // СТРОИТЕЛЬСТВО
  {id:'wyrd_insta', e:'📸',n:'WYRD INSTA',     room:'build', s:'pending',d:'🔨 Строится. Карусели EU→RU и RU→EN.'},
  {id:'wyrd_income',e:'💸',n:'WYRD INCOME',    room:'build', s:'pending',d:'🔨 Строится. Конвейер Бабло→Идеи.'},
];

// Автоматическая карта DB-имён → JS-id
const DB_AGENT_MAP = {};
AGENTS.forEach(a => { if (a.db) DB_AGENT_MAP[a.db] = a.id; });

const LINKS = [
  {s:'shef',t:'tomas',type:'command'},   {s:'tomas',t:'shef',type:'report'},
  {s:'audit',t:'shef',type:'report'},
  {s:'tomas',t:'strateg',type:'command'},{s:'strateg',t:'arhitektor',type:'command'},
  {s:'strateg',t:'kartograf',type:'command'},
  {s:'arhitektor',t:'kaznachey',type:'command'},
  {s:'tomas',t:'professor',type:'command'},
  {s:'professor',t:'br_anlt',type:'knowledge'},
  {s:'professor',t:'br_babla',type:'knowledge'},
  {s:'professor',t:'br_idei',type:'knowledge'},
  {s:'professor',t:'br_proekt',type:'knowledge'},
  {s:'skrayb',t:'profobr',type:'knowledge'},
  {s:'hugin',t:'profobr',type:'knowledge'},
  {s:'profobr',t:'tomas',type:'knowledge'},
  {s:'br_anlt',t:'tomas',type:'report'},
  {s:'br_anlt',t:'schetik',type:'command'},  {s:'br_anlt',t:'razvedchik',type:'command'},
  {s:'br_anlt',t:'kritik',type:'command'},   {s:'razvedchik',t:'profobr',type:'knowledge'},
  {s:'br_babla',t:'tomas',type:'report'},
  {s:'br_babla',t:'sledopyt',type:'command'},{s:'br_babla',t:'bot_razv',type:'command'},
  {s:'br_babla',t:'struktur',type:'command'},{s:'br_babla',t:'ohotnik',type:'command'},
  {s:'br_babla',t:'schetovod',type:'command'},{s:'br_babla',t:'prioritiz',type:'command'},
  {s:'br_babla',t:'br_anlt',type:'knowledge'},
  {s:'br_idei',t:'tomas',type:'report'},
  {s:'br_idei',t:'generator',type:'command'},{s:'br_idei',t:'detaliz',type:'command'},
  {s:'br_idei',t:'ocen_idei',type:'command'},{s:'br_idei',t:'br_babla',type:'knowledge'},
  {s:'br_proekt',t:'tomas',type:'report'},
  {s:'br_proekt',t:'decomp',type:'command'}, {s:'br_proekt',t:'sinhron',type:'command'},
  {s:'br_proekt',t:'ocen_pr',type:'command'},
  {s:'studiya',t:'tomas',type:'report'},     {s:'tehnik',t:'tomas',type:'report'},
  {s:'kartograf',t:'wyrd_insta',type:'command'},{s:'wyrd_insta',t:'tomas',type:'report'},
  {s:'kartograf',t:'wyrd_income',type:'command'},{s:'wyrd_income',t:'br_idei',type:'knowledge'},
];

const ROOMS = [
  {id:'hq',    label:'ШТАБ HQ',       color:'#4a9eff', x:.04, y:.03, w:.58, h:.17},
  {id:'audit', label:'АУДИТ',         color:'#ff4444', x:.68, y:.03, w:.28, h:.09},
  {id:'lib',   label:'БИБЛИОТЕКА',    color:'#4aff88', x:.03, y:.24, w:.37, h:.21},
  {id:'anlt',  label:'АНАЛИТИКА',     color:'#ffaa00', x:.43, y:.24, w:.26, h:.21},
  {id:'tech',  label:'ТЕХНИК',        color:'#888888', x:.72, y:.24, w:.15, h:.08},
  {id:'babla', label:'ОТДЕЛ БАБЛА',   color:'#44ff44', x:.03, y:.49, w:.41, h:.17},
  {id:'ideyny',label:'ИДЕЙНЫЙ',       color:'#cc44ff', x:.47, y:.49, w:.24, h:.17},
  {id:'proekt',label:'ПРОЕКТНЫЙ',     color:'#4a9eff', x:.74, y:.36, w:.22, h:.18},
  {id:'prod',  label:'ПРОИЗВОДСТВО',  color:'#aa44ff', x:.03, y:.70, w:.22, h:.12},
  {id:'build', label:'СТРОИТЕЛЬСТВО', color:'#ff8800', x:.28, y:.70, w:.42, h:.12},
];

const roomMap = {};
ROOMS.forEach(r => {
  r.rx=r.x*W; r.ry=r.y*H; r.rw=r.w*W; r.rh=r.h*H;
  roomMap[r.id] = r;
});

const agentsByRoom = {};
AGENTS.filter(a=>a.room).forEach(a => {
  (agentsByRoom[a.room] = agentsByRoom[a.room]||[]).push(a);
});

const NW=68, NH=32;
AGENTS.forEach(a => {
  if (!a.room) { a.x=W*.5; a.y=H*.068; return; }
  const r=roomMap[a.room], list=agentsByRoom[a.room], i=list.indexOf(a);
  const cols=Math.max(1,Math.ceil(Math.sqrt(list.length*(r.rw/r.rh))));
  const col=i%cols, row=Math.floor(i/cols);
  const padX=12, padY=18;
  const cellW=(r.rw-padX*2)/cols;
  const cellH=(r.rh-padY-padX)/Math.ceil(list.length/cols);
  a.x=r.rx+padX+cellW*(col+.5);
  a.y=r.ry+padY+cellH*(row+.5);
});

const agentMap = {};
AGENTS.forEach(a => agentMap[a.id]=a);

function linkGhost(l){ return (agentMap[l.s]?.s==='ghost')||(agentMap[l.t]?.s==='ghost'); }
function linkPending(l){ return !linkGhost(l)&&(agentMap[l.s]?.s==='pending'||agentMap[l.t]?.s==='pending'); }

function calcArc(l) {
  const src=agentMap[l.s], tgt=agentMap[l.t];
  const mx=(src.x+tgt.x)/2, my=(src.y+tgt.y)/2;
  const dist=Math.hypot(tgt.x-src.x,tgt.y-src.y);
  const ang=Math.atan2(tgt.y-src.y,tgt.x-src.x)+Math.PI/2;
  const cx=mx+Math.cos(ang)*dist*.26, cy=my+Math.sin(ang)*dist*.26;
  return {path:`M${src.x},${src.y}Q${cx},${cy} ${tgt.x},${tgt.y}`, cx, cy, src, tgt};
}

const resolvedLinks = LINKS.map(l=>({...l,...calcArc(l)}));

// ─── SVG ──────────────────────────────────────────────────────
const svg = d3.select('#graph').attr('width',W).attr('height',H);
const defs = svg.append('defs');

const gf=defs.append('filter').attr('id','glow');
gf.append('feGaussianBlur').attr('stdDeviation','2.5').attr('result','b');
const fm=gf.append('feMerge');
fm.append('feMergeNode').attr('in','b'); fm.append('feMergeNode').attr('in','SourceGraphic');

const gfS=defs.append('filter').attr('id','glow-s');
gfS.append('feGaussianBlur').attr('stdDeviation','7').attr('result','b');
const fmS=gfS.append('feMerge');
fmS.append('feMergeNode').attr('in','b'); fmS.append('feMergeNode').attr('in','SourceGraphic');

Object.entries(LC).forEach(([type,color])=>{
  defs.append('marker').attr('id',`arr-${type}`)
    .attr('viewBox','0 -4 8 8').attr('refX',34).attr('refY',0)
    .attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill',color).attr('opacity',.85);
});
defs.append('marker').attr('id','arr-ghost')
  .attr('viewBox','0 -4 8 8').attr('refX',34).attr('refY',0)
  .attr('markerWidth',4).attr('markerHeight',4).attr('orient','auto')
  .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#333').attr('opacity',.4);

const pg=defs.append('linearGradient').attr('id','pg').attr('x1','0').attr('y1','0').attr('x2','0').attr('y2','1');
pg.append('stop').attr('offset','0').attr('stop-color','#4a9eff').attr('stop-opacity',0);
pg.append('stop').attr('offset','0.4').attr('stop-color','#4a9eff').attr('stop-opacity',0.18);
pg.append('stop').attr('offset','0.6').attr('stop-color','#4a9eff').attr('stop-opacity',0.18);
pg.append('stop').attr('offset','1').attr('stop-color','#4a9eff').attr('stop-opacity',0);

// ─── ZOOM ─────────────────────────────────────────────────────
const zoomG = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.12, 4])
  .on('zoom', ({transform}) => zoomG.attr('transform', transform));
svg.call(zoom).on('dblclick.zoom', null);
if (W < 900) svg.call(zoom.transform, d3.zoomIdentity.scale(Math.max(0.22, W/1400)));

// ─── КОМНАТЫ ──────────────────────────────────────────────────
const roomG = zoomG.append('g');
const roomRects = roomG.selectAll('g').data(ROOMS).join('g').style('cursor','pointer');
roomRects.append('rect')
  .attr('x',d=>d.rx).attr('y',d=>d.ry).attr('width',d=>d.rw).attr('height',d=>d.rh)
  .attr('rx',6).attr('fill',d=>d.color+'0a').attr('stroke',d=>d.color)
  .attr('stroke-width',1.5).attr('stroke-opacity',.35).attr('filter','url(#glow)');
roomRects.append('text')
  .attr('x',d=>d.rx+10).attr('y',d=>d.ry+13)
  .attr('fill',d=>d.color).attr('font-size','7px').attr('letter-spacing','2px').attr('opacity',.6)
  .text(d=>d.label);

// ─── СВЯЗИ ────────────────────────────────────────────────────
const linkG = zoomG.append('g');
const linkEls = linkG.selectAll('path').data(resolvedLinks).join('path')
  .attr('fill','none').attr('stroke-width',1.2)
  .attr('d',d=>d.path)
  .attr('stroke',d=>linkGhost(d)?'#252525':LC[d.type])
  .attr('opacity',d=>linkGhost(d)?.09:linkPending(d)?.30:.38)
  .attr('stroke-dasharray',d=>linkGhost(d)?'4,5':linkPending(d)?'7,3':null)
  .attr('marker-end',d=>linkGhost(d)?'url(#arr-ghost)':`url(#arr-${d.type})`);

// ─── АГЕНТЫ ───────────────────────────────────────────────────
const agentG = zoomG.append('g');
const agentEls = agentG.selectAll('g').data(AGENTS).join('g')
  .attr('transform',d=>`translate(${d.x},${d.y})`).style('cursor','pointer');

const shefEl = agentEls.filter(d=>d.id==='shef');
shefEl.append('circle').attr('r',26)
  .attr('fill','#ffd70014').attr('stroke','#ffd700').attr('stroke-width',2.5)
  .attr('filter','url(#glow-s)');
shefEl.append('text').attr('text-anchor','middle').attr('dominant-baseline','central')
  .attr('font-size','20px').text('👑');
shefEl.append('text').attr('text-anchor','middle').attr('dy','38px')
  .attr('fill','#ffd700').attr('font-size','9px').attr('letter-spacing','2px').text('ШЕФ');

const normalEls = agentEls.filter(d=>d.id!=='shef');
const roomColor = d => { const r=roomMap[d.room]; return r?r.color:'#4a9eff'; };

normalEls.append('rect')
  .attr('x',-NW/2).attr('y',-NH/2).attr('width',NW).attr('height',NH).attr('rx',3)
  .attr('fill',d=>roomColor(d)+'0d').attr('stroke',d=>roomColor(d))
  .attr('stroke-width',1.2).attr('stroke-dasharray',d=>SS[d.s].dash).attr('opacity',d=>SS[d.s].op)
  .attr('filter',d=>d.s==='ghost'?null:'url(#glow)');
normalEls.append('rect')
  .attr('x',-NW/2).attr('y',-NH/2).attr('width',NW).attr('height',9).attr('rx',3)
  .attr('fill',d=>roomColor(d)).attr('opacity',d=>d.s==='ghost'?.05:.20);
normalEls.append('text').attr('text-anchor','middle').attr('dy','-2px')
  .attr('font-size','10px').attr('opacity',d=>SS[d.s].op).text(d=>d.e);
normalEls.append('text').attr('text-anchor','middle').attr('dy','13px')
  .attr('font-size','5.8px').attr('letter-spacing','.3px')
  .attr('fill',d=>d.s==='ghost'?'#444':roomColor(d)).attr('opacity',d=>SS[d.s].op)
  .text(d=>d.n);
normalEls.append('circle').attr('r',3).attr('cx',NW/2-4).attr('cy',-NH/2+4)
  .attr('fill',d=>SS[d.s].dot).attr('opacity',d=>d.s==='ghost'?.3:1)
  .attr('filter',d=>d.s==='live'?'url(#glow)':null);

// ─── ПУЛЬС-ВОЛНА ──────────────────────────────────────────────
const pulseEl = svg.append('rect')
  .attr('x',0).attr('width',W).attr('height',28)
  .attr('fill','url(#pg)').attr('opacity',0).attr('pointer-events','none');

// ─── ЧАСТИЦЫ ──────────────────────────────────────────────────
const activeLinks = resolvedLinks.filter(l=>!linkGhost(l));
const particles = [];
activeLinks.forEach((lnk,i)=>{
  const n=lnk.type==='knowledge'?2:1;
  for(let k=0;k<n;k++) particles.push({li:i,t:Math.random(),spd:.0016+Math.random()*.003});
});
const partG = zoomG.append('g');
const partEls = partG.selectAll('circle').data(particles).join('circle')
  .attr('r',2).attr('filter','url(#glow)').attr('fill',d=>LC[activeLinks[d.li].type]);

function ptOnQuad(lnk,t){
  const s=lnk.src, tg=lnk.tgt, u=1-t;
  return {x:u*u*s.x+2*u*t*lnk.cx+t*t*tg.x, y:u*u*s.y+2*u*t*lnk.cy+t*t*tg.y};
}

// ─── TOOLTIP ──────────────────────────────────────────────────
const tip=d3.select('#tooltip');
agentEls.on('mouseover',(e,d)=>{
  const st=SS[d.s]||SS.live, c=d.id==='shef'?'#ffd700':roomColor(d);
  tip.style('display','block')
    .html(`<strong style="color:${c}">${d.e} ${d.n}</strong>
      <span style="background:${st.dot};color:#000;font-size:8px;padding:1px 5px;border-radius:2px;margin-left:5px">${st.label}</span>
      <br><span style="color:#6a8aaa">${d.d}</span>`)
    .style('left',(e.pageX+14)+'px').style('top',(e.pageY-12)+'px');
}).on('mouseout',()=>tip.style('display','none'));

// ─── КЛИКИ / ВЫДЕЛЕНИЕ ────────────────────────────────────────
let mode='all', selRoom=null, selAgent=null;
const hint=document.getElementById('mode-hint');

function connAgents(id){ const s=new Set([id]); resolvedLinks.forEach(l=>{if(l.s===id)s.add(l.t);if(l.t===id)s.add(l.s);}); return s; }
function connRoomsOf(id){ const s=new Set(); const mr=agentMap[id]?.room; if(mr)s.add(mr); resolvedLinks.forEach(l=>{if(l.s===id&&agentMap[l.t]?.room)s.add(agentMap[l.t].room);if(l.t===id&&agentMap[l.s]?.room)s.add(agentMap[l.s].room);}); return s; }
function roomAgentIds(rid){ return new Set((agentsByRoom[rid]||[]).map(a=>a.id)); }
function roomConnAgents(rid){ const ra=roomAgentIds(rid),s=new Set(ra); ra.forEach(aid=>resolvedLinks.forEach(l=>{if(l.s===aid)s.add(l.t);if(l.t===aid)s.add(l.s);})); return s; }
function roomConnRooms(rid){ const s=new Set([rid]); roomConnAgents(rid).forEach(aid=>{const r=agentMap[aid]?.room;if(r)s.add(r);}); return s; }

function applyMode(){
  if(mode==='all'){
    linkEls.attr('opacity',d=>linkGhost(d)?.09:linkPending(d)?.30:.38).attr('stroke-width',1.2);
    agentEls.style('opacity',null); roomRects.select('rect').attr('stroke-opacity',.35).attr('stroke-width',1.5);
    partEls.attr('opacity',1); hint.textContent='нажми на комнату или агента'; return;
  }
  if(mode==='room'){
    const ra=roomAgentIds(selRoom), ca=roomConnAgents(selRoom), cr=roomConnRooms(selRoom);
    linkEls.attr('opacity',d=>linkGhost(d)?.02:(ra.has(d.s)||ra.has(d.t))?.92:.04).attr('stroke-width',d=>(ra.has(d.s)||ra.has(d.t))?2.8:1.2);
    agentEls.style('opacity',d=>ca.has(d.id)||d.id==='shef'?null:'0.06');
    roomRects.select('rect').attr('stroke-opacity',d=>d.id===selRoom?.9:cr.has(d.id)?.4:.07).attr('stroke-width',d=>d.id===selRoom?2.8:1.5);
    partEls.attr('opacity',d=>{const l=activeLinks[d.li];return(ra.has(l.s)||ra.has(l.t))?1:.03;});
    hint.textContent=`◉ ${ROOMS.find(r=>r.id===selRoom)?.label||selRoom} · ещё раз = сброс`; return;
  }
  if(mode==='agent'){
    const ca=connAgents(selAgent), cr=connRoomsOf(selAgent);
    linkEls.attr('opacity',d=>linkGhost(d)?.02:(d.s===selAgent||d.t===selAgent)?.95:.03).attr('stroke-width',d=>(d.s===selAgent||d.t===selAgent)?3.2:1.2);
    agentEls.style('opacity',d=>ca.has(d.id)?null:'0.05');
    roomRects.select('rect').attr('stroke-opacity',d=>cr.has(d.id)?.55:.07).attr('stroke-width',1.5);
    partEls.attr('opacity',d=>{const l=activeLinks[d.li];return(l.s===selAgent||l.t===selAgent)?1:0;});
    hint.textContent=`◉ ${agentMap[selAgent].n} · ещё раз = сброс`;
  }
}

agentEls.on('click',(e,d)=>{
  e.stopPropagation(); tip.style('display','none');
  if(mode==='agent'&&selAgent===d.id){ const r=agentMap[d.id]?.room; if(r){mode='room';selRoom=r;}else{mode='all';} selAgent=null; }
  else { mode='agent'; selAgent=d.id; }
  applyMode();
});
roomRects.on('click',(e,d)=>{
  tip.style('display','none');
  if(mode==='room'&&selRoom===d.id){mode='all';selRoom=null;} else{mode='room';selRoom=d.id;selAgent=null;}
  applyMode();
});
svg.on('click',()=>{mode='all';selRoom=null;selAgent=null;applyMode();});

// ─── АНИМАЦИЯ ─────────────────────────────────────────────────
const pendingEl = normalEls.filter(d=>d.s==='pending');
let pulseY=-30, pulseOn=false, lastPulse=0;

d3.timer(el=>{
  const t=el/1000;
  if(!pulseOn&&t-lastPulse>6){pulseOn=true;pulseY=-30;}
  if(pulseOn){ pulseY+=3.5; pulseEl.attr('y',pulseY).attr('opacity',pulseY<H?.85:0); if(pulseY>H+30){pulseOn=false;lastPulse=t;} }
  const pulse=0.3+0.7*(0.5+0.5*Math.sin(t*2.3));
  pendingEl.select('rect').attr('opacity',pulse).attr('stroke-width',1.2+pulse*2);
  particles.forEach(pt=>{pt.t=(pt.t+pt.spd)%1;});
  partEls
    .attr('opacity',d=>{ const l=activeLinks[d.li]; return (agentMap[l.s]?.s==='live'||agentMap[l.t]?.s==='live')?1:0; })
    .attr('cx',d=>ptOnQuad(activeLinks[d.li],d.t).x)
    .attr('cy',d=>ptOnQuad(activeLinks[d.li],d.t).y);
});

function zoomBy(k){ svg.transition().duration(260).call(zoom.scaleBy, k); }
function zoomReset(){ svg.transition().duration(320).call(zoom.transform, d3.zoomIdentity.scale(W<900?Math.max(0.22,W/1400):1)); }

// ─── LIVE STATUS FROM API ──────────────────────────────────────
function refreshAgentVisuals() {
  normalEls.select('rect:first-child')
    .attr('stroke-dasharray',d=>SS[d.s].dash).attr('opacity',d=>SS[d.s].op)
    .attr('filter',d=>d.s==='ghost'?null:'url(#glow)');
  normalEls.select('rect:nth-child(2)').attr('opacity',d=>d.s==='ghost'?.05:.20);
  normalEls.select('text:first-of-type').attr('opacity',d=>SS[d.s].op);
  normalEls.select('text:nth-of-type(2)')
    .attr('fill',d=>d.s==='ghost'?'#444':roomColor(d)).attr('opacity',d=>SS[d.s].op);
  normalEls.select('circle')
    .attr('fill',d=>SS[d.s].dot).attr('opacity',d=>d.s==='ghost'?.3:1)
    .attr('filter',d=>d.s==='live'?'url(#glow)':null);
  linkEls
    .attr('stroke',d=>linkGhost(d)?'#252525':LC[d.type])
    .attr('opacity',d=>{
      if(linkGhost(d))return .09; if(linkPending(d))return .18;
      return (agentMap[d.s]?.s==='live'||agentMap[d.t]?.s==='live')?.55:.10;
    })
    .attr('stroke-dasharray',d=>linkGhost(d)?'4,5':linkPending(d)?'7,3':null)
    .attr('marker-end',d=>linkGhost(d)?'url(#arr-ghost)':`url(#arr-${d.type})`);
}

async function fetchLiveStatus() {
  try {
    const data = await fetch('/civilization/agents').then(r=>r.json());
    let changed = false;
    const now = Date.now();
    (data.agents||[]).forEach(a=>{
      const jsId = DB_AGENT_MAP[a.name];
      if (!jsId) return;
      const agent = agentMap[jsId];
      if (!agent || agent.s==='ghost') return;
      const pulseMs = a.last_pulse ? now - new Date(a.last_pulse+'Z').getTime() : Infinity;
      const newS = (a.status==='active' && pulseMs < 600_000) ? 'live'
                 : a.last_pulse ? 'pause' : 'ready';
      if (agent.s !== newS) { agent.s = newS; changed = true; }
    });
    if (changed) refreshAgentVisuals();
  } catch {}
}

fetchLiveStatus();
setInterval(fetchLiveStatus, 30_000);
