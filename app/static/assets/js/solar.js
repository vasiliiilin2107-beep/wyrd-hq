/* ─── STARFIELD ─────────────────────────────────────── */
function initStars(canvas) {
  const ctx = canvas.getContext('2d');
  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    drawStars(ctx, canvas.width, canvas.height);
  }
  window.addEventListener('resize', resize);
  resize();
}

function drawStars(ctx, w, h) {
  ctx.clearRect(0, 0, w, h);
  const count = Math.floor((w * h) / 4000);
  for (let i = 0; i < count; i++) {
    const x = Math.random() * w;
    const y = Math.random() * h;
    const r = Math.random() * 1.2 + 0.2;
    const a = Math.random() * 0.7 + 0.15;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,${a})`;
    ctx.fill();
  }
}

/* ─── ПЛАНЕТЫ ───────────────────────────────────────── */
const PLANETS = [
  {
    id: 'hq', name: 'HQ', sub: 'Штаб',
    color: '#f59e0b', size: 18,
    orbit: 130, speed: 22, startAngle: 45,
    url: '/hq', active: true
  },
  {
    id: 'thomas', name: 'ТОМАС', sub: 'Страж',
    color: '#3b82f6', size: 14,
    orbit: 225, speed: 38, startAngle: 120,
    url: '/thomas', active: true
  },
  {
    id: 'studio', name: 'СТУДИЯ', sub: 'Контент',
    color: '#8b5cf6', size: 14,
    orbit: 225, speed: 38, startAngle: 290,
    url: '/studio', active: true
  },
  {
    id: 'library', name: 'БИБЛИОТЕКА', sub: 'Знания',
    color: '#10b981', size: 11,
    orbit: 320, speed: 60, startAngle: 60,
    url: null, active: false
  },
  {
    id: 'analytics', name: 'АНАЛИТИКА', sub: 'Данные',
    color: '#f97316', size: 11,
    orbit: 320, speed: 60, startAngle: 195,
    url: null, active: false
  },
  {
    id: 'finance', name: 'БУХГАЛТЕРИЯ', sub: 'Деньги',
    color: '#ef4444', size: 11,
    orbit: 320, speed: 60, startAngle: 330,
    url: null, active: false
  },
];

const ORBITS = [130, 225, 320];

function buildSolar() {
  const scene = document.querySelector('.solar-scene');
  if (!scene) return;

  const cx = scene.offsetWidth  / 2;
  const cy = scene.offsetHeight / 2;

  // Орбитальные кольца
  ORBITS.forEach(r => {
    const ring = document.createElement('div');
    ring.className = 'orbit-ring';
    ring.style.width  = `${r * 2}px`;
    ring.style.height = `${r * 2}px`;
    scene.appendChild(ring);
  });

  // Планеты
  PLANETS.forEach(p => {
    const wrap = document.createElement('div');
    wrap.className = 'planet' + (p.active ? '' : ' planet--inactive');
    wrap.id = 'planet-' + p.id;

    const body = document.createElement('div');
    body.className = 'planet-body';
    body.style.cssText = `
      width: ${p.size}px;
      height: ${p.size}px;
      background: radial-gradient(circle at 35% 35%, ${lighten(p.color, 40)}, ${p.color});
      box-shadow: 0 0 ${p.size}px ${p.color}88, 0 0 ${p.size * 2}px ${p.color}44;
    `;
    body.setAttribute('data-color', p.color);

    const label = document.createElement('div');
    label.className = 'planet-label';
    label.style.color = p.color;
    label.innerHTML = p.name + (p.sub ? `<span class="planet-sub">${p.sub}</span>` : '');

    if (p.active && p.url) {
      body.addEventListener('click', () => navigateTo(body, p.url));
    }

    wrap.appendChild(body);
    wrap.appendChild(label);
    scene.appendChild(wrap);
    p.el = wrap;
    p.bodyEl = body;
  });

  animateOrbits();
}

function animateOrbits() {
  const startTime = performance.now();

  function frame(now) {
    const elapsed = (now - startTime) / 1000;

    PLANETS.forEach(p => {
      if (!p.el) return;
      const rad = ((p.startAngle + elapsed * (360 / p.speed)) * Math.PI) / 180;
      const x = Math.cos(rad) * p.orbit;
      const y = Math.sin(rad) * p.orbit;
      p.el.style.transform = `translate(${x}px, ${y}px)`;
    });

    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

function navigateTo(bodyEl, url) {
  bodyEl.classList.add('flash');
  setTimeout(() => { window.location.href = url; }, 380);
}

function lighten(hex, amt) {
  const num = parseInt(hex.replace('#',''), 16);
  const r = Math.min(255, (num >> 16) + amt);
  const g = Math.min(255, ((num >> 8) & 0xff) + amt);
  const b = Math.min(255, (num & 0xff) + amt);
  return `rgb(${r},${g},${b})`;
}

/* ─── INIT ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('starfield');
  if (canvas) initStars(canvas);
  buildSolar();
});
