// 希可 Live2D 验收截图（参考 live2d-agent-kit 的检查清单）：
//  1 半睁眼    2 嘴型×张嘴组合    3 头和身体反着转    4 转头极限+表情组合    5 连续动作逐帧
// 每类拼成一张大图：check_<模型>_<类>.png。用法：node checks.js [模型名，默认 seeko]
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const root = __dirname, RT = process.env.RT || '/home/claude/zhixu-whale-maid-pet/src/live2d/seeko';
const M = process.argv[2] || 'seeko';
const srv = http.createServer((q, s) => {
  let p = decodeURIComponent(q.url.split('?')[0]);
  p = p.startsWith('/runtime/') ? path.join(RT, p.slice(9)) : path.join(root, p);
  fs.readFile(p, (e, d) => { if (e) { s.writeHead(404); s.end(); } else s.end(d); });
}).listen(8737);

const P = (o) => o; // 只是让下面的表格好看
const SETS = {
  eyes: [
    ['睁眼', {}], ['0.8', P({ ParamEyeLOpen: 0.8, ParamEyeROpen: 0.8 })], ['0.6', P({ ParamEyeLOpen: 0.6, ParamEyeROpen: 0.6 })],
    ['0.4', P({ ParamEyeLOpen: 0.4, ParamEyeROpen: 0.4 })], ['0.2', P({ ParamEyeLOpen: 0.2, ParamEyeROpen: 0.2 })], ['闭眼', P({ ParamEyeLOpen: 0, ParamEyeROpen: 0 })],
    ['笑眼', P({ ParamEyeLOpen: 0, ParamEyeROpen: 0, ParamEyeLSmile: 1, ParamEyeRSmile: 1 })], ['半笑', P({ ParamEyeLOpen: 0.5, ParamEyeROpen: 0.5, ParamEyeLSmile: 0.5, ParamEyeRSmile: 0.5 })],
    ['左眨', P({ ParamEyeLOpen: 0 })], ['右眨', P({ ParamEyeROpen: 0 })], ['闭+左转', P({ ParamEyeLOpen: 0, ParamEyeROpen: 0, ParamAngleX: 30 })], ['眼珠左上', P({ ParamEyeBallX: -1, ParamEyeBallY: 1 })],
  ],
  mouth: [],
  body: [
    ['头右身左', P({ ParamAngleX: 30, ParamBodyAngleX: -10 })], ['头左身右', P({ ParamAngleX: -30, ParamBodyAngleX: 10 })],
    ['头歪右身歪左', P({ ParamAngleZ: 30, ParamBodyAngleZ: -10 })], ['头歪左身歪右', P({ ParamAngleZ: -30, ParamBodyAngleZ: 10 })],
    ['抬头身右', P({ ParamAngleY: 30, ParamBodyAngleX: 10 })], ['低头身左', P({ ParamAngleY: -30, ParamBodyAngleX: -10 })],
    ['全极限1', P({ ParamAngleX: 30, ParamAngleY: 30, ParamAngleZ: -30, ParamBodyAngleX: -10, ParamBodyAngleZ: 10 })],
    ['全极限2', P({ ParamAngleX: -30, ParamAngleY: -30, ParamAngleZ: 30, ParamBodyAngleX: 10, ParamBodyAngleZ: -10 })],
    ['双手上', P({ ParamArmLA: 10, ParamArmRA: 10 })], ['双手内', P({ ParamArmLA: -10, ParamArmRA: -10 })],
    ['手上+身歪', P({ ParamArmLA: 10, ParamArmRA: 10, ParamBodyAngleZ: 10 })], ['手内+转头', P({ ParamArmLA: -10, ParamArmRA: -10, ParamAngleX: 30 })],
  ],
};
for (const f of [-1, 0, 1]) for (const o of [0, 0.25, 0.5, 0.75, 1]) SETS.mouth.push([`形${f} 开${o}`, { ParamMouthForm: f, ParamMouthOpenY: o }]);
const MOTIONS = ['Wave', 'Hop', 'Stretch', 'Flinch', 'Nod', 'Shake', 'Tilt', 'Swing'];

async function sheet(files, out, cols, label = []) {
  const { execFileSync } = require('child_process');
  execFileSync('python3', ['-c', `
import sys,json
from PIL import Image, ImageDraw, ImageFont
fs=json.loads(sys.argv[1]); out=sys.argv[2]; cols=int(sys.argv[3]); labels=json.loads(sys.argv[4])
ims=[Image.open(f).convert('RGB') for f in fs]
w,h=ims[0].size
rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(w*cols,(h+22)*rows),'white'); d=ImageDraw.Draw(S)
try: font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',16)
except Exception: font=None
for i,im in enumerate(ims):
    x,y=(i%cols)*w,(i//cols)*(h+22)
    S.paste(im,(x,y+22)); d.text((x+6,y+2),labels[i] if i<len(labels) else '',fill='black',font=font)
S.save(out)`, JSON.stringify(files), out, String(cols), JSON.stringify(label)]);
}

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell', args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const pg = await b.newPage({ viewport: { width: 400, height: 534 } });
  await pg.goto('http://localhost:8737/pview.html?m=' + M);
  const ready = await pg.evaluate(() => window.ready);
  if (ready !== 'ok') throw new Error(ready);
  const ids = await pg.evaluate(() => { const c = window.model.internalModel.coreModel; return c._parameterIds || c.getModel().parameters.ids; });
  const missing = new Set();
  await pg.evaluate(() => {
    const mm = window.model;
    mm.internalModel.eyeBlink = undefined;
    window._ps = {};
    mm.internalModel.on('beforeModelUpdate', () => { for (const [k, v] of Object.entries(window._ps)) window.setParam(k, v); });
  });
  const tmp = path.join(root, 'chk_tmp'); fs.mkdirSync(tmp, { recursive: true });
  const clip = { x: 40, y: 40, width: 320, height: 320 };
  for (const [name, list] of Object.entries(SETS)) {
    const files = [], labels = [];
    for (let i = 0; i < list.length; i++) {
      const [lab, ps] = list[i];
      for (const k of Object.keys(ps)) if (!ids.includes(k)) missing.add(k);
      await pg.evaluate((ps) => { window._ps = ps; window.step(600); }, ps);
      const f = path.join(tmp, `${name}_${i}.png`);
      await pg.screenshot({ path: f, clip: name === 'body' ? { x: 0, y: 0, width: 400, height: 534 } : clip });
      files.push(f); labels.push(lab);
    }
    await sheet(files, path.join(root, `check_${M}_${name}.png`), name === 'mouth' ? 5 : 6, labels);
  }
  // 连续动作：每个动作从头播，每 120ms 截一帧（画完再截）
  await pg.evaluate(() => { window._ps = {}; window.step(500); });
  for (const g of MOTIONS) {
    const files = [], labels = [];
    const ok = await pg.evaluate(async (g) => { const r = await window.model.motion(g, 0, 3); return r; }, g);
    for (let i = 0; i < 18; i++) {
      await pg.evaluate(() => window.step(120));
      const f = path.join(tmp, `mo_${g}_${i}.png`);
      await pg.screenshot({ path: f, clip: { x: 0, y: 0, width: 400, height: 534 } });
      files.push(f); labels.push(`${g} ${(i + 1) * 120}ms`);
    }
    await sheet(files, path.join(root, `check_${M}_motion_${g}.png`), 6, labels);
    if (!ok) console.log('动作没播起来：', g);
  }
  console.log('模型里没有的参数：', [...missing]);
  await b.close(); srv.close();
})().catch((e) => { console.error(e); process.exit(1); });
