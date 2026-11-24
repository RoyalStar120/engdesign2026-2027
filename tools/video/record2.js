const { chromium } = require('playwright-core');
const fs = require('fs');
const VW = 1920, VH = 1080, TARGET = 90.6;
// seeded RNG so the take is repeatable
let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const rr = (a, b) => a + (b - a) * rnd();
(async () => {
  const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', args: ['--window-size=1920,1200', '--hide-scrollbars'] });
  const p = await b.newPage({ viewport: { width: VW, height: VH }, colorScheme: 'light' });
  await p.goto('file:///Users/sidharth/engineeringdesign2026-2027/harvester_sim/plucked_harvester_bench.html');
  await p.addStyleTag({ content: `.lede,.notes,.eyebrow{display:none!important} #traces{height:340px!important} body{padding-block:26px 0!important}
    #fakecur{position:fixed;left:0;top:0;width:26px;height:26px;z-index:99999;pointer-events:none;transform:translate(-200px,-200px)}` });
  await p.evaluate(() => {
    const d = document.createElement('div'); d.id = 'fakecur';
    d.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l15 11-6.5 1.2L15 21l-3 1.4-3.4-6.8L3 20z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>';
    document.body.appendChild(d);
    addEventListener('mousemove', e => { d.style.transform = `translate(${e.clientX-3}px,${e.clientY-2}px)`; }, true);
    dispatchEvent(new Event('resize'));
  });
  await p.waitForTimeout(1500);
  for (let i = 0; i < 3; i++) {
    const bot = await p.evaluate(() => { const r = document.querySelector('.recorder').getBoundingClientRect(); return r.bottom; });
    console.log('chart bottom', bot);
    if (bot <= 1060) break;
    await p.evaluate(over => { const t = document.getElementById('traces'); t.style.setProperty('height', (t.getBoundingClientRect().height - over) + 'px', 'important'); dispatchEvent(new Event('resize')); }, bot - 1052);
    await p.waitForTimeout(400);
  }

  const cdp = await p.context().newCDPSession(p);
  const frames = [];
  cdp.on('Page.screencastFrame', async f => { frames.push({ data: f.data, t: f.metadata.timestamp });
    try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch {} });

  let cx = 1250, cy = 640;
  const sleep = ms => p.waitForTimeout(ms);
  // human-ish move: curved path, ease-in-out with variable speed, overshoot + correction, hand tremor
  const humanMove = async (tx, ty, opts = {}) => {
    const dx = tx - cx, dy = ty - cy, dist = Math.hypot(dx, dy);
    if (dist < 2) return;
    const dur = opts.dur ?? Math.min(1100, 260 + 140 * Math.log2(dist / 25 + 1) + rr(-60, 120));
    const over = opts.noOver ? 0 : (dist > 120 ? rr(0.02, 0.07) : 0);
    const ex = tx + dx * over + rr(-4, 4), ey = ty + dy * over + rr(-4, 4);
    const nx = -dy / (dist || 1), ny = dx / (dist || 1), bend = rr(-0.18, 0.18) * dist;
    const c1x = cx + dx * rr(0.2, 0.4) + nx * bend, c1y = cy + dy * rr(0.2, 0.4) + ny * bend;
    const c2x = cx + dx * rr(0.6, 0.85) + nx * bend * 0.5, c2y = cy + dy * rr(0.6, 0.85) + ny * bend * 0.5;
    const sx = cx, sy = cy, tm0 = Date.now();
    for (;;) {
      const el = (Date.now() - tm0) / dur; if (el >= 1) break;
      let t = el; t = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      t = Math.min(1, t + rr(-0.008, 0.008));
      const u = 1 - t;
      const x = u*u*u*sx + 3*u*u*t*c1x + 3*u*t*t*c2x + t*t*t*ex + rr(-0.7, 0.7);
      const y = u*u*u*sy + 3*u*u*t*c1y + 3*u*t*t*c2y + t*t*t*ey + rr(-0.7, 0.7);
      await p.mouse.move(x, y);
    }
    await p.mouse.move(ex, ey);
    cx = ex; cy = ey;
    if (over || Math.hypot(ex - tx, ey - ty) > 1) { // correction
      const cd = rr(90, 170), sx2 = cx, sy2 = cy, tc0 = Date.now();
      for (;;) { const t = (Date.now() - tc0) / cd; if (t >= 1) break; await p.mouse.move(sx2 + (tx - sx2) * t + rr(-0.4, 0.4), sy2 + (ty - sy2) * t + rr(-0.4, 0.4)); }
      await p.mouse.move(tx, ty);
      cx = tx; cy = ty;
    }
  };
  // idle: hand drifts a little while watching
  const idle = async ms => {
    const end = Date.now() + ms;
    while (Date.now() < end - 120) {
      const left = end - Date.now();
      if (rnd() < 0.45 && left > 700) {
        const ox = cx, oy = cy; await humanMove(cx + rr(-26, 26), cy + rr(-16, 16), { dur: rr(250, 500), noOver: true });
        if (rnd() < 0.5) await humanMove(ox + rr(-6, 6), oy + rr(-6, 6), { dur: rr(200, 400), noOver: true });
      } else await sleep(Math.min(left, rr(350, 900)));
    }
    const rest = end - Date.now(); if (rest > 0) await sleep(rest);
  };
  const center = async sel => { const r = await p.locator(sel).boundingBox(); return [r.x + r.width * rr(0.35, 0.65), r.y + r.height * rr(0.35, 0.65)]; };
  const click = async sel => {
    const [x, y] = await center(sel); await humanMove(x, y); await sleep(rr(110, 260));
    await p.mouse.down(); await sleep(rr(60, 120)); await p.mouse.up(); await sleep(rr(80, 200));
  };
  const slide = async (sel, value) => {
    const r = await p.locator(sel).boundingBox();
    const [min, max, cur] = await p.$eval(sel, e => [+e.min, +e.max, +e.value]);
    const px = v => r.x + 8 + (r.width - 16) * (v - min) / (max - min), y = r.y + r.height / 2;
    await humanMove(px(cur) + rr(-2, 2), y + rr(-1.5, 1.5)); await sleep(rr(120, 250));
    await p.mouse.down(); await sleep(rr(60, 110));
    const x0 = cx, x1 = px(value), over = (x1 - x0) * rr(0.03, 0.08), dd = rr(650, 900), td0 = Date.now();
    for (let i = 0;; i++) { let t = (Date.now() - td0) / dd; if (t >= 1) break; t = t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
      await p.mouse.move(x0 + (x1 + over - x0) * t + rr(-1, 1), y + rr(-1.8, 1.8) + Math.sin(i / 5) * 1.2); }
    await sleep(rr(80, 160));
    const tb0 = Date.now(); for (;;) { const t = (Date.now() - tb0) / 160; if (t >= 1) break; await p.mouse.move(x1 + over * (1 - t) + rr(-0.5, 0.5), y + rr(-0.8, 0.8)); }
    await p.mouse.move(x1, y);
    await sleep(rr(50, 100)); await p.mouse.up();
    await p.$eval(sel, (e, v) => { e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); }, String(value));
    cx = x1; cy = y;
  };

  await p.mouse.move(cx, cy);
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
  const t0 = Date.now();
  await idle(1500);
  await humanMove(720, 420); await idle(1600);           // model
  await humanMove(1330, 380); await idle(1400);          // readouts
  await humanMove(820, 860); await idle(1400);           // strip chart
  await click('#l1'); await idle(1600);
  await click('#l2'); await idle(2400);
  await click('#once'); await idle(3600);
  await click('#once'); await idle(1400);                // resume shaking
  await slide('#freq', 10); await idle(2200);
  await slide('#freq', 25); await idle(1800);
  await click('#matchFd'); await idle(1900);
  await slide('#acc', 4); await idle(1800);
  await slide('#acc', 0.6); await idle(2000);
  await slide('#acc', 2); await idle(1000);
  await click('#s1'); await idle(1600);
  await click('#s3'); await idle(1600);
  await click('#s2'); await idle(600);
  await click('#d_asdrawn'); await idle(3200);
  await click('#d_corrected'); await idle(2400);
  await click('#d_redesign'); await idle(1400);
  await click('#t_poster'); await idle(1500);
  await click('#t_phys'); await idle(800);
  await slide('#exag', 9); await idle(1500);
  await slide('#exag', 4); await idle(800);
  await click('#play'); await idle(1300);
  await click('#play');
  const left = TARGET * 1000 - (Date.now() - t0);
  console.log('time before final idle', ((Date.now() - t0) / 1000).toFixed(1));
  await humanMove(1000, 560); await idle(Math.max(1500, left - 600));
  await cdp.send('Page.stopScreencast');
  await b.close();

  fs.rmSync('frames', { recursive: true, force: true }); fs.mkdirSync('frames');
  let list = 'ffconcat version 1.0\n';
  frames.forEach((f, i) => { const name = `frames/f${String(i).padStart(5, '0')}.jpg`;
    fs.writeFileSync(name, Buffer.from(f.data, 'base64'));
    list += `file '${name}'\nduration ${(i + 1 < frames.length ? frames[i + 1].t - f.t : 0.1).toFixed(4)}\n`; });
  list += `file 'frames/f${String(frames.length - 1).padStart(5, '0')}.jpg'\n`;
  fs.writeFileSync('list.txt', list);
  console.log('frames', frames.length, 'span', (frames.at(-1).t - frames[0].t).toFixed(1), 's');
})();
