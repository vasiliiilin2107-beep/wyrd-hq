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
  {id:'shef',        e:'👑',n:'ШЕФ',          room:null,    s:'live',   d:'Создатель мира. Принимает финальные решения.'},
  {id:'tomas',       e:'🎙',n:'ТОМАС',         room:'hq',    s:'pause',  d:'Глаза, уши и голос Шефа. ⛔ На паузе с 30.05.'},
  {id:'strateg',     e:'🧠',n:'СТРАТЕГ',       room:'hq',    s:'ready',  d:'Думает КАК строить мир. Промпт 100/100.'},
  {id:'arhitektor',  e:'📐',n:'АРХИТЕКТОР',    room:'hq',    s:'ready',  d:'Рисует чертежи, пишет ТЗ. Промпт 100/100.'},
  {id:'kartograf',   e:'🗺',n:'КАРТОГРАФ',     room:'hq',    s:'ready',  d:'Следит за ветками мира. Промпт 100/100.'},
  {id:'kaznachey',   e:'💰',n:'КАЗНАЧЕЙ',      room:'hq',    s:'ghost',  d:'Финансы мира. Не создан.'},
  {id:'proektniy',   e:'📋',n:'ПРОЕКТНЫЙ',     room:'hq',    s:'ghost',  d:'Управляет проектом. Не создан.'},
  {id:'audit',       e:'⚖', n:'АУДИТ',         room:'audit', s:'ghost',  d:'Независимый контроль. Только Шефу.'},
  {id:'bibliotekar', e:'📖',n:'БИБЛИОТЕКАРЬ',  room:'lib',   s:'ghost',  d:'Единственная точка входа запросов.'},
  {id:'arhivarius',  e:'🗄',n:'АРХИВАРИУС',    room:'lib',   s:'ghost',  d:'Знает весь фонд. Управляет читателями.'},
  {id:'pisatel',     e:'✍', n:'ПИСАТЕЛЬ',      room:'lib',   s:'ghost',  d:'Резюмирует и связывает темы.'},
  {id:'skrayb',      e:'🌍',n:'СКРАЙБ',        room:'lib',   s:'ready',  d:'Переводит EN→RU. Горит когда активен.'},
  {id:'musorschik',  e:'🧹',n:'МУСОРЩИК',      room:'lib',   s:'ghost',  d:'Чистит дубли. Не создан.'},
  {id:'hugin',       e:'🦅',n:'ХУГИН',         room:'lib',   s:'ready',  d:'Разведчик снаружи. Горит когда активен.'},
  {id:'chitatel',    e:'😴',n:'ЧИТАТЕЛИ×19',   room:'lib',   s:'pause',  d:'⛔ Спят. Остановлены с 30.05.'},
  {id:'profobr',     e:'🎓',n:'ПРОФОБР',       room:'lib',   s:'ready',  d:'Промпты Совета 100/100 готовы.'},
  {id:'analitika',   e:'📊',n:'АНАЛИТИКА',     room:'anlt',  s:'ghost',  d:'Метрики и тренды. Не создан.'},
  {id:'studiya',     e:'🎬',n:'СТУДИЯ',        room:'prod',  s:'pause',  d:'⛔ На паузе. Видео, рилсы, карусели.'},
  {id:'finansy',     e:'🔢',n:'ФИНАНСЫ',       room:'prod',  s:'ghost',  d:'Просчёт идей. Не создан.'},
  {id:'ideynyy',     e:'💡',n:'ИДЕЙНЫЙ',       room:'prod',  s:'ghost',  d:'Идеи монетизации. Не создан.'},
  {id:'reklama',     e:'📣',n:'РЕКЛАМА',       room:'prod',  s:'ghost',  d:'Упаковка и продвижение. Не создан.'},
  {id:'tehnik',      e:'🔧',n:'ТЕХНИК',        room:'tech',  s:'pause',  d:'⛔ На паузе. Только ремонты — стройка это Моз.'},
  {id:'wyrd_insta',  e:'📸',n:'WYRD INSTA',    room:'build', s:'pending',d:'🔨 Строится. Карусели EU→RU и RU→EN.'},
  {id:'wyrd_income', e:'💸',n:'WYRD INCOME',   room:'build', s:'pending',d:'🔨 Строится. Генератор→Оценщик→Аналитик.'},
];

const LINKS = [
  {s:'shef',t:'tomas',type:'command'},
  {s:'tomas',t:'shef',type:'report'},
  {s:'audit',t:'shef',type:'report'},
  {s:'tomas',t:'strateg',type:'command'},
  {s:'strateg',t:'arhitektor',type:'command'},
  {s:'strateg',t:'kartograf',type:'command'},
  {s:'arhitektor',t:'kaznachey',type:'command'},
  {s:'arhitektor',t:'proektniy',type:'command'},
  {s:'kaznachey',t:'tomas',type:'report'},
  {s:'kartograf',t:'tomas',type:'report'},
  {s:'proektniy',t:'audit',type:'report'},
  {s:'tomas',t:'bibliotekar',type:'knowledge'},
  {s:'bibliotekar',t:'arhivarius',type:'knowledge'},
  {s:'arhivarius',t:'chitatel',type:'command'},
  {s:'chitatel',t:'arhivarius',type:'knowledge'},
  {s:'arhivarius',t:'pisatel',type:'knowledge'},
  {s:'pisatel',t:'bibliotekar',type:'knowledge'},
  {s:'hugin',t:'bibliotekar',type:'knowledge'},
  {s:'skrayb',t:'bibliotekar',type:'knowledge'},
  {s:'musorschik',t:'bibliotekar',type:'report'},
  {s:'profobr',t:'tomas',type:'knowledge'},
  {s:'bibliotekar',t:'analitika',type:'knowledge'},
  {s:'analitika',t:'tomas',type:'report'},
  {s:'analitika',t:'ideynyy',type:'knowledge'},
  {s:'ideynyy',t:'finansy',type:'money'},
  {s:'finansy',t:'kaznachey',type:'money'},
  {s:'ideynyy',t:'studiya',type:'content'},
  {s:'studiya',t:'reklama',type:'content'},
  {s:'tehnik',t:'tomas',type:'report'},
  {s:'kartograf',t:'wyrd_insta',type:'command'},
  {s:'wyrd_insta',t:'studiya',type:'content'},
  {s:'wyrd_insta',t:'tomas',type:'report'},
  {s:'kartograf',t:'wyrd_income',type:'command'},
  {s:'wyrd_income',t:'ideynyy',type:'knowledge'},
  {s:'wyrd_income',t:'tomas',type:'report'},
];

// КОМНАТЫ — иерархия сверху вниз, позиции в долях экрана
const ROOMS = [
  {id:'hq',    label:'ШТАБ HQ',       color:'#4a9eff', x:.07, y:.13, w:.56, h:.21},
  {id:'audit', label:'АУДИТ',         color:'#ff4444', x:.69, y:.13, w:.25, h:.10},
  {id:'lib',   label:'БИБЛИОТЕКА',    color:'#4aff88', x:.03, y:.39, w:.55, h:.22},
  {id:'anlt',  label:'АНАЛИТИКА',     color:'#ffaa00', x:.63, y:.39, w:.19, h:.09},
  {id:'tech',  label:'ТЕХНИК',        color:'#888888', x:.85, y:.39, w:.12, h:.09},
  {id:'prod',  label:'ПРОИЗВОДСТВО',  color:'#aa44ff', x:.11, y:.66, w:.53, h:.15},
  {id:'build', label:'СТРОИТЕЛЬСТВО', color:'#ff8800', x:.19, y:.85, w:.46, h:.10},
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

// Позиции агентов — ШЕФ над штабом, остальные в сетке внутри комнаты
const NW=70, NH=34;
AGENTS.forEach(a => {
  if (!a.room) { a.x=W*.5; a.y=H*.068; return; }
  const r=roomMap[a.room], list=agentsByRoom[a.room], i=list.indexOf(a);
  const cols=Math.max(1,Math.ceil(Math.sqrt(list.length*(r.rw/r.rh))));
  const col=i%cols, row=Math.floor(i/cols);
  const padX=14, padY=20;
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
    .attr('viewBox','0 -4 8 8').attr('refX',36).attr('refY',0)
    .attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill',color).attr('opacity',.85);
});
defs.append('marker').attr('id','arr-ghost')
  .attr('viewBox','0 -4 8 8').attr('refX',36).attr('refY',0)
  .attr('markerWidth',4).attr('markerHeight',4).attr('orient','auto')
  .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#333').attr('opacity',.4);

// Градиент пульса (горизонтальная волна сверху вниз)
const pg=defs.append('linearGradient').attr('id','pg').attr('x1','0').attr('y1','0').attr('x2','0').attr('y2','1');
pg.append('stop').attr('offset','0').attr('stop-color','#4a9eff').attr('stop-opacity',0);
pg.append('stop').attr('offset','0.4').attr('stop-color','#4a9eff').attr('stop-opacity',0.18);
pg.append('stop').attr('offset','0.6').attr('stop-color','#4a9eff').attr('stop-opacity',0.18);
pg.append('stop').attr('offset','1').attr('stop-color','#4a9eff').attr('stop-opacity',0);

// ─── ZOOM CONTAINER ───────────────────────────────────────────
const zoomG = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.15, 4])
  .on('zoom', ({transform}) => zoomG.attr('transform', transform));
svg.call(zoom).on('dblclick.zoom', null);
if (W < 700) svg.call(zoom.transform, d3.zoomIdentity.scale(Math.max(0.28, W/1100)));

// ─── СЛОЙ 1: КОМНАТЫ ──────────────────────────────────────────
const roomG = zoomG.append('g');
const roomRects = roomG.selectAll('g').data(ROOMS).join('g').style('cursor','pointer');

roomRects.append('rect')
  .attr('x',d=>d.rx).attr('y',d=>d.ry).attr('width',d=>d.rw).attr('height',d=>d.rh)
  .attr('rx',6).attr('fill',d=>d.color+'0a').attr('stroke',d=>d.color)
  .attr('stroke-width',1.5).attr('stroke-opacity',.35).attr('filter','url(#glow)');

roomRects.append('text')
  .attr('x',d=>d.rx+10).attr('y',d=>d.ry+13)
  .attr('fill',d=>d.color).attr('font-size','7px').attr('letter-spacing','2px').attr('opacity',.55)
  .text(d=>d.label);

// ─── СЛОЙ 2: ПАУТИНА СВЯЗЕЙ ───────────────────────────────────
const linkG = zoomG.append('g');
const linkEls = linkG.selectAll('path').data(resolvedLinks).join('path')
  .attr('fill','none').attr('stroke-width',1.2)
  .attr('d',d=>d.path)
  .attr('stroke',d=>linkGhost(d)?'#252525':LC[d.type])
  .attr('opacity',d=>linkGhost(d)?.09:linkPending(d)?.30:.38)
  .attr('stroke-dasharray',d=>linkGhost(d)?'4,5':linkPending(d)?'7,3':null)
  .attr('marker-end',d=>linkGhost(d)?'url(#arr-ghost)':`url(#arr-${d.type})`);

// ─── СЛОЙ 3: АГЕНТЫ ───────────────────────────────────────────
const agentG = zoomG.append('g');
const agentEls = agentG.selectAll('g').data(AGENTS).join('g')
  .attr('transform',d=>`translate(${d.x},${d.y})`).style('cursor','pointer');

// ШЕФ — особый: круг с короной
const shefEl = agentEls.filter(d=>d.id==='shef');
shefEl.append('circle').attr('r',26)
  .attr('fill','#ffd70014').attr('stroke','#ffd700').attr('stroke-width',2.5)
  .attr('filter','url(#glow-s)');
shefEl.append('text').attr('text-anchor','middle').attr('dominant-baseline','central')
  .attr('font-size','20px').text('👑');
shefEl.append('text').attr('text-anchor','middle').attr('dy','38px')
  .attr('fill','#ffd700').attr('font-size','9px').attr('letter-spacing','2px').text('ШЕФ');

// Остальные — карточки
const normalEls = agentEls.filter(d=>d.id!=='shef');
const roomColor = d => { const r=roomMap[d.room]; return r?r.color:'#4a9eff'; };

normalEls.append('rect')
  .attr('x',-NW/2).attr('y',-NH/2).attr('width',NW).attr('height',NH).attr('rx',3)
  .attr('fill',d=>roomColor(d)+'0d').attr('stroke',d=>roomColor(d))
  .attr('stroke-width',1.2).attr('stroke-dasharray',d=>SS[d.s].dash).attr('opacity',d=>SS[d.s].op)
  .attr('filter',d=>d.s==='ghost'?null:'url(#glow)');

normalEls.append('rect')
  .attr('x',-NW/2).attr('y',-NH/2).attr('width',NW).attr('height',10).attr('rx',3)
  .attr('fill',d=>roomColor(d)).attr('opacity',d=>d.s==='ghost'?.05:.22);

normalEls.append('text').attr('text-anchor','middle').attr('dy','-2px')
  .attr('font-size','11px').attr('opacity',d=>SS[d.s].op).text(d=>d.e);

normalEls.append('text').attr('text-anchor','middle').attr('dy','14px')
  .attr('font-size','6.2px').attr('letter-spacing','.4px')
  .attr('fill',d=>d.s==='ghost'?'#444':roomColor(d)).attr('opacity',d=>SS[d.s].op)
  .text(d=>d.n);

normalEls.append('circle').attr('r',3.5).attr('cx',NW/2-5).attr('cy',-NH/2+5)
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
  for(let k=0;k<n;k++) particles.push({li:i,t:Math.random(),spd:.0018+Math.random()*.003});
});
const partG = zoomG.append('g');
const partEls = partG.selectAll('circle').data(particles).join('circle')
  .attr('r',2.5).attr('filter','url(#glow)').attr('fill',d=>LC[activeLinks[d.li].type]);

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

// ─── РЕЖИМЫ НАЖАТИЯ ───────────────────────────────────────────
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
    agentEls.style('opacity',null);
    roomRects.select('rect').attr('stroke-opacity',.35).attr('stroke-width',1.5);
    partEls.attr('opacity',1);
    hint.textContent='нажми на комнату или агента';
    return;
  }
  if(mode==='room'){
    const ra=roomAgentIds(selRoom), ca=roomConnAgents(selRoom), cr=roomConnRooms(selRoom);
    linkEls.attr('opacity',d=>linkGhost(d)?.02:(ra.has(d.s)||ra.has(d.t))?.92:.04)
           .attr('stroke-width',d=>(ra.has(d.s)||ra.has(d.t))?2.8:1.2);
    agentEls.style('opacity',d=>ca.has(d.id)||d.id==='shef'?null:'0.06');
    roomRects.select('rect').attr('stroke-opacity',d=>d.id===selRoom?.9:cr.has(d.id)?.4:.07)
             .attr('stroke-width',d=>d.id===selRoom?2.8:1.5);
    partEls.attr('opacity',d=>{const l=activeLinks[d.li];return(ra.has(l.s)||ra.has(l.t))?1:.03;});
    const rm=ROOMS.find(r=>r.id===selRoom);
    hint.textContent=`◉ ${rm?.label||selRoom} · ещё раз = сброс · нажми агента`;
    return;
  }
  if(mode==='agent'){
    const ca=connAgents(selAgent), cr=connRoomsOf(selAgent);
    linkEls.attr('opacity',d=>linkGhost(d)?.02:(d.s===selAgent||d.t===selAgent)?.95:.03)
           .attr('stroke-width',d=>(d.s===selAgent||d.t===selAgent)?3.2:1.2);
    agentEls.style('opacity',d=>ca.has(d.id)?null:'0.05');
    roomRects.select('rect').attr('stroke-opacity',d=>cr.has(d.id)?.55:.07).attr('stroke-width',1.5);
    partEls.attr('opacity',d=>{const l=activeLinks[d.li];return(l.s===selAgent||l.t===selAgent)?1:0;});
    hint.textContent=`◉ ${agentMap[selAgent].n} · ещё раз = сброс`;
  }
}

agentEls.on('click',(e,d)=>{
  e.stopPropagation(); tip.style('display','none');
  if(mode==='agent'&&selAgent===d.id){
    const r=agentMap[d.id]?.room;
    if(r){mode='room';selRoom=r;}else{mode='all';} selAgent=null;
  } else { mode='agent'; selAgent=d.id; }
  applyMode();
});

roomRects.on('click',(e,d)=>{
  tip.style('display','none');
  if(mode==='room'&&selRoom===d.id){mode='all';selRoom=null;}
  else{mode='room';selRoom=d.id;selAgent=null;}
  applyMode();
});

svg.on('click',()=>{mode='all';selRoom=null;selAgent=null;applyMode();});

// ─── АНИМАЦИЯ ─────────────────────────────────────────────────
const pendingEl = normalEls.filter(d=>d.s==='pending');
let pulseY=-30, pulseOn=false, lastPulse=0;

d3.timer(el=>{
  const t=el/1000;
  if(!pulseOn&&t-lastPulse>6){pulseOn=true;pulseY=-30;}
  if(pulseOn){
    pulseY+=3.5;
    pulseEl.attr('y',pulseY).attr('opacity',pulseY<H?.85:0);
    if(pulseY>H+30){pulseOn=false;lastPulse=t;}
  }
  const pulse=0.3+0.7*(0.5+0.5*Math.sin(t*2.3));
  pendingEl.select('rect').attr('opacity',pulse).attr('stroke-width',1.2+pulse*2);
  particles.forEach(pt=>{pt.t=(pt.t+pt.spd)%1;});
  partEls
    .attr('opacity', d => {
      const l = activeLinks[d.li];
      return (agentMap[l.s]?.s==='live' || agentMap[l.t]?.s==='live') ? 1 : 0;
    })
    .attr('cx',d=>ptOnQuad(activeLinks[d.li],d.t).x)
    .attr('cy',d=>ptOnQuad(activeLinks[d.li],d.t).y);
});

function zoomBy(k){ svg.transition().duration(260).call(zoom.scaleBy, k); }
function zoomReset(){ svg.transition().duration(320).call(zoom.transform, d3.zoomIdentity.scale(W<700?Math.max(0.28,W/1100):1)); }

// ─── LIVE STATUS FROM DB ──────────────────────────────────
const DB_AGENT_MAP = {
  thomas:  'tomas',
  technik: 'tehnik',
  studio:  'studiya',
  scribe:  'skrayb',
};

function refreshAgentVisuals() {
  normalEls.select('rect:first-child')
    .attr('stroke-dasharray', d => SS[d.s].dash)
    .attr('opacity', d => SS[d.s].op)
    .attr('filter', d => d.s === 'ghost' ? null : 'url(#glow)');

  normalEls.select('rect:nth-child(2)')
    .attr('opacity', d => d.s === 'ghost' ? .05 : .22);

  normalEls.select('text:first-of-type')
    .attr('opacity', d => SS[d.s].op);

  normalEls.select('text:nth-of-type(2)')
    .attr('fill', d => d.s === 'ghost' ? '#444' : roomColor(d))
    .attr('opacity', d => SS[d.s].op);

  normalEls.select('circle')
    .attr('fill', d => SS[d.s].dot)
    .attr('opacity', d => d.s === 'ghost' ? .3 : 1)
    .attr('filter', d => d.s === 'live' ? 'url(#glow)' : null);

  linkEls
    .attr('stroke', d => linkGhost(d) ? '#252525' : LC[d.type])
    .attr('opacity', d => {
      if (linkGhost(d)) return .09;
      if (linkPending(d)) return .18;
      const srcLive = agentMap[d.s]?.s === 'live';
      const tgtLive = agentMap[d.t]?.s === 'live';
      return (srcLive || tgtLive) ? .55 : .10;
    })
    .attr('stroke-dasharray', d => linkGhost(d) ? '4,5' : linkPending(d) ? '7,3' : null)
    .attr('marker-end', d => linkGhost(d) ? 'url(#arr-ghost)' : `url(#arr-${d.type})`);
}

async function fetchLiveStatus() {
  try {
    const data = await fetch('/civilization/agents').then(r => r.json());
    let changed = false;
    (data.agents || []).forEach(a => {
      const jsId = DB_AGENT_MAP[a.name];
      if (!jsId) return;
      const agent = agentMap[jsId];
      if (!agent || agent.s === 'ghost') return;
      const isLive = a.status === 'active' && a.last_pulse &&
        (Date.now() - new Date(a.last_pulse).getTime()) < 300_000;
      const newS = isLive ? 'live' : 'pause';
      if (agent.s !== newS) { agent.s = newS; changed = true; }
    });
    refreshAgentVisuals();
  } catch {}
}

fetchLiveStatus();
setInterval(fetchLiveStatus, 30_000);
