// 把模型摆到各个参数极值，截图看衣服有没有被网格切掉、关节有没有穿帮
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const root = __dirname, RT = '/home/claude/zhixu-whale-maid-pet/src/live2d/seeko';
const srv = http.createServer((q, s) => {
  let p = decodeURIComponent(q.url.split('?')[0]);
  p = p.startsWith('/runtime/') ? path.join(RT, p.slice(9)) : path.join(root, p);
  fs.readFile(p, (e, d) => { if (e) { s.writeHead(404); s.end(); } else s.end(d); });
}).listen(8734);
const POSES = [
  ['neutral', {}], ['angX+', { ParamAngleX: 30 }], ['angX-', { ParamAngleX: -30 }], ['angY+', { ParamAngleY: 30 }], ['angY-', { ParamAngleY: -30 }],
  ['angZ+', { ParamAngleZ: 30 }], ['angZ-', { ParamAngleZ: -30 }], ['bodyX+', { ParamBodyAngleX: 10 }], ['bodyZ+', { ParamBodyAngleZ: 10 }], ['bodyZ-', { ParamBodyAngleZ: -10 }],
  ['armsUp', { ParamArmLA: 10, ParamArmRA: 10 }], ['armsIn', { ParamArmLA: -10, ParamArmRA: -10 }], ['wave', { ParamArmRA: 10, ParamArmLA: -2, ParamAngleZ: -9, ParamBodyAngleZ: -4 }],
  ['combo', { ParamAngleX: 25, ParamAngleY: -20, ParamAngleZ: 20, ParamBodyAngleZ: 8, ParamArmLA: 8, ParamArmRA: -6 }],
];
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell', args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const m = process.argv[2] || 'seeko_pajamas';
  const pg = await b.newPage({ viewport: { width: 400, height: 534 } });
  await pg.goto('http://localhost:8734/pview.html?m=' + m);
  console.log(await pg.evaluate(() => window.ready));
  await pg.evaluate(() => {
    const mm = window.model;
    mm.internalModel.eyeBlink = undefined;
    window._ps = {};
    mm.internalModel.on('beforeModelUpdate', () => { for (const [k, v] of Object.entries(window._ps)) window.setParam(k, v); });
  });
  for (const [n, ps] of POSES) {
    await pg.evaluate((ps) => { window._ps = ps; window.step(800); }, ps);
    await pg.screenshot({ path: path.join(root, `pose_${m}_${n}.png`) });
  }
  await b.close(); srv.close();
  // 拼成一张
  const names = POSES.map((p) => p[0]);
  fs.writeFileSync(path.join(root, `pose_${m}_names.json`), JSON.stringify(names));
})();
