const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const p = await b.newPage({ viewport: { width: 1600, height: 1500 }, deviceScaleFactor: 2, colorScheme: 'light' });
  await p.goto('file:///Users/sidharth/engineeringdesign2026-2027/harvester_sim/plucked_harvester_bench.html');
  await p.addStyleTag({ content: `header,.notes{display:none!important} body{padding:20px!important}` });
  await p.evaluate(() => dispatchEvent(new Event('resize')));
  await p.click('#l2');
  await p.waitForTimeout(9000);
  const wrap = await p.locator('.wrap').boundingBox();
  const rel = async s => { const r = await p.locator(s).boundingBox(); return { x: (r.x - wrap.x) / wrap.width, y: (r.y - wrap.y) / wrap.height, w: r.width / wrap.width, h: r.height / wrap.height }; };
  console.log(JSON.stringify({ stage: await rel('.sheet'), readouts: await rel('.readouts'), status: await rel('.status'), controls: await rel('.controls'), chart: await rel('.recorder'), aspect: wrap.width / wrap.height }));
  console.log(await p.evaluate(() => ['r_fd','r_fp','r_gap','r_snap','r_pl','r_vpk','r_p'].map(i => i + '=' + document.getElementById(i).textContent).join(' ')));
  await p.locator('.wrap').screenshot({ path: '/Users/sidharth/engineeringdesign2026-2027/portfolio/figs/sim_bench_side.png' });
  await b.close();
})();
