const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const p = await b.newPage({ viewport: { width: 1700, height: 1300 }, deviceScaleFactor: 2, colorScheme: 'light' });
  await p.goto('file:///Users/sidharth/engineeringdesign2026-2027/harvester_sim/plucked_harvester_bench.html');
  await p.addStyleTag({content:'.wrap{max-width:1560px!important}'}); await p.evaluate(()=>dispatchEvent(new Event('resize'))); await p.click('#l2'); await p.click('#s3');
  await p.$eval('#exag', e => { e.value = '8'; e.dispatchEvent(new Event('input', { bubbles: true })); });
  await p.waitForTimeout(2500);
  await p.click('#once'); await p.click('#play');
  await p.waitForTimeout(300);
  await p.locator('#stage').screenshot({ path: 'burst2/b000.png' });
  await p.click('#play');
  for (let i = 1; i <= 40; i++) { await p.waitForTimeout(110); await p.locator('#stage').screenshot({ path: `burst2/b${String(i).padStart(3,'0')}.png` }); }
  await b.close();
})();
