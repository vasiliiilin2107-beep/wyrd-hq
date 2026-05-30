const LINKS = [
  { from: 'room-hq',        to: 'room-library',   color: '#4a9eff', dur: 2.5, label: 'запросы знаний' },
  { from: 'room-hq',        to: 'room-projects',  color: '#44ffee', dur: 3.0, label: 'ТЗ' },
  { from: 'room-hq',        to: 'room-analytics', color: '#ffaa00', dur: 3.8, label: 'задачи аналитике' },
  { from: 'room-projects',  to: 'room-hq',        color: '#44ffee', dur: 4.0, label: 'отчёт' },
  { from: 'room-library',   to: 'room-edu',        color: '#2acc66', dur: 5.0, label: 'знания' },
  { from: 'room-library',   to: 'room-analytics', color: '#4aff88', dur: 3.5, label: 'данные' },
  { from: 'room-analytics', to: 'room-hq',        color: '#ffaa00', dur: 2.2, label: 'отчёты→HQ' },
  { from: 'room-analytics', to: 'room-money',     color: '#ffdd00', dur: 3.2, label: 'данные→Бабло' },
  { from: 'room-money',     to: 'room-media',     color: '#aa44ff', dur: 2.8, label: 'идеи' },
  { from: 'room-media',     to: 'room-promo',     color: '#ffcc00', dur: 3.6, label: 'контент' },
  { from: 'room-money',     to: 'room-hq',        color: '#44ff44', dur: 4.5, label: 'питч→Казначей' },
];

function getCenter(elId, container) {
  const el = document.getElementById(elId);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const c = container.getBoundingClientRect();
  return { x: r.left - c.left + r.width / 2, y: r.top - c.top + r.height / 2 };
}

function makeCurve(p1, p2) {
  const dx = p2.x - p1.x, dy = p2.y - p1.y;
  const bend = Math.min(Math.abs(dy) * 0.4, 120);
  const cx1 = p1.x + dx * 0.25 + bend;
  const cy1 = p1.y + dy * 0.1;
  const cx2 = p2.x - dx * 0.25 + bend;
  const cy2 = p2.y - dy * 0.1;
  return `M${p1.x},${p1.y} C${cx1},${cy1} ${cx2},${cy2} ${p2.x},${p2.y}`;
}

function ns(tag) { return document.createElementNS('http://www.w3.org/2000/svg', tag); }

function drawLinks() {
  const container = document.getElementById('map-container');
  const svg = document.getElementById('links-svg');
  if (!container || !svg) return;

  const W = container.offsetWidth, H = container.offsetHeight;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);
  svg.innerHTML = '';

  const defs = ns('defs');
  svg.appendChild(defs);

  LINKS.forEach((link, i) => {
    const p1 = getCenter(link.from, container);
    const p2 = getCenter(link.to, container);
    if (!p1 || !p2) return;

    const pathId = `lp${i}`;
    const filterId = `gf${i}`;
    const d = makeCurve(p1, p2);

    // glow filter
    const filt = ns('filter');
    filt.id = filterId;
    filt.innerHTML = `<feGaussianBlur in="SourceGraphic" stdDeviation="2.5"/>`;
    defs.appendChild(filt);

    // glow layer
    const glow = ns('path');
    glow.setAttribute('d', d);
    glow.setAttribute('stroke', link.color);
    glow.setAttribute('stroke-width', '4');
    glow.setAttribute('fill', 'none');
    glow.setAttribute('opacity', '0.15');
    glow.setAttribute('filter', `url(#${filterId})`);
    svg.appendChild(glow);

    // main line
    const line = ns('path');
    line.id = pathId;
    line.setAttribute('d', d);
    line.setAttribute('stroke', link.color);
    line.setAttribute('stroke-width', '1');
    line.setAttribute('fill', 'none');
    line.setAttribute('opacity', '0.5');
    svg.appendChild(line);

    // moving dot
    const dot = ns('circle');
    dot.setAttribute('r', '3');
    dot.setAttribute('fill', link.color);

    const dotGlow = ns('filter');
    dotGlow.id = `dg${i}`;
    dotGlow.innerHTML = `<feGaussianBlur stdDeviation="2"/>`;
    defs.appendChild(dotGlow);
    dot.setAttribute('filter', `url(#dg${i})`);

    const motion = ns('animateMotion');
    motion.setAttribute('dur', `${link.dur}s`);
    motion.setAttribute('repeatCount', 'indefinite');
    motion.setAttribute('keyTimes', '0;1');
    motion.setAttribute('calcMode', 'linear');

    const mpath = ns('mpath');
    mpath.setAttributeNS('http://www.w3.org/1999/xlink', 'href', `#${pathId}`);
    motion.appendChild(mpath);
    dot.appendChild(motion);
    svg.appendChild(dot);
  });
}

window.addEventListener('load', () => {
  setTimeout(drawLinks, 100);
  window.addEventListener('resize', drawLinks);
});

window.toggleLinks = function() {
  const svg = document.getElementById('links-svg');
  const btn = document.getElementById('toggle-btn');
  const on = svg.style.display !== 'none';
  svg.style.display = on ? 'none' : 'block';
  btn.textContent = on ? '⬡ НИТИ ВКЛ' : '⬡ НИТИ ВЫКЛ';
  btn.style.opacity = on ? '0.5' : '1';
};
