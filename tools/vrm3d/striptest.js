// 逐帧条（离线确定性渲染）：node striptest.js Wave,Hop,... [fps=8] [maxms=3000]
const { chromium } = require('playwright');
const names = (process.argv[2] || 'Wave,Hop,Cheer,Flinch,Shake,Stretch,Shy,Tilt,Kick,Nod,Land').split(',');
const fps = +(process.argv[3] || 8), maxms = +(process.argv[4] || 3000);
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'] });
  const pg = await b.newPage({ viewport: { width: 340, height: 440 } });
  pg.on('pageerror', e => console.log('PAGEERROR', e.message));
  await pg.addInitScript(() => { localStorage.setItem('whale-prefs', JSON.stringify({ qStyle: 'vrm', qStyleSet: true, quiet: true })); });
  await pg.goto('http://localhost:8765/index.html');
  await pg.waitForFunction(() => document.getElementById('vrm3d') && !document.getElementById('vrm3d').hidden, null, { timeout: 60000 });
  await pg.waitForTimeout(500);
  await pg.evaluate(() => { try { nextRoam = Date.now() + 1e9; nextChat = Date.now() + 1e9; } catch {} setMood('idle', 3600000); });
  const fs = require('fs'); fs.mkdirSync('strips', { recursive: true });
  for (const name of names) {
    await pg.evaluate(() => setMood('idle', 3600000));
    const dur = await pg.evaluate(([name, maxms]) => { const c = VRM3D._acts[name]; return c.loop !== undefined ? Math.min(c.until || maxms, maxms) : c.dur; }, [name, maxms]);
    const n = Math.ceil((dur + 400) / (1000 / fps)) + 1;
    for (let i = 0; i < n; i++) {
      await pg.evaluate(([name, tm]) => VRM3D._renderAt(name, tm), [name, i * (1000 / fps)]);
      fs.writeFileSync(`strips/${name}_${String(i).padStart(2, '0')}.png`, await pg.screenshot({ clip: { x: 20, y: 0, width: 300, height: 440 } }));
    }
    console.log(name, dur, 'ms', n, 'frames');
  }
  await b.close();
})();
