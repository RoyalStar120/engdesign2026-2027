const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const out = [];
  for (const th of ['phys','poster']) for (const d of ['asdrawn','corrected','redesign']) for (const l of [0,1,2]) {
    const p = await b.newPage({ viewport: { width: 1600, height: 1400 } });
    await p.goto('file:///Users/sidharth/engineeringdesign2026-2027/harvester_sim/plucked_harvester_bench.html');
    await p.click('#s1'); await p.click('#t_'+th); await p.click('#d_'+d); await p.click('#l'+l);
    await p.click('#matchFd');
    await p.waitForTimeout(9000);
    const r = await p.evaluate(() => Object.fromEntries(['r_fd','r_fp','r_cyc','r_gap','r_snap','r_pl','r_xp','r_vpk','r_p','pill','o_freq'].map(i => [i, document.getElementById(i).textContent.trim()])));
    out.push({ theta: th, design: d, len: [85,95,105][l], ...r }); console.error(JSON.stringify(out.at(-1)));
    await p.close();
  }
  require('fs').writeFileSync('bench_results.json', JSON.stringify(out, null, 1));
  await b.close();
})();
