// 衣服和立绘：希可现在穿哪套、某个表情/动作该显示哪张图。
// 立绘都是整张图（不分层）。每套衣服只画了一部分动作，缺的按下面的顺序找，**绝不换回女仆装**：
//   1. 这套衣服画了这个动作 → 用它
//   2. alias 里写了用哪张代替（比如睡衣没画「屑笑」以外的坏笑，就用「屑笑」）→ 用那张
//   3. NEAR 里相近的动作（探头 ↔ 其他探头、迷糊 → 睡觉……）这套衣服有 → 用那张
//   4. 用这套衣服的待机图顶上，靠 CSS 动画演：被拎起来照样蹬腿、跑步照样蹦、
//      躲在屏幕边就把整张图往屏幕外推一半（standIn），看起来也是在探头
// 文件放在 sprites/<衣服>/<动作>.webp；女仆装就是 sprites/ 下面原来那些图（什么动作都有）。
// 新画的衣服：加一项到 OUTFITS，把画好的动作写进 has，缺的写 alias，其他的自动回退。
const NEAR = {
  peekPhone: 'peek', peekCheek: 'peek', peekHead: 'peek', peekAngry: 'peek', peek: 'peekSleep', peekSleep: 'peek',
  sleepBottom: 'sleep', sleepy: 'sleep', wake: 'angry', angry: 'wake', excited: 'happy', surprised: 'happy',
  smirk: 'smug', bleh: 'smug', newyear: 'happy', hot: 'meh', cold: 'meh', umbrella: 'idle', onigiri: 'happy',
};
const DOCKED = new Set(['peek', 'peekPhone', 'peekCheek', 'peekHead', 'peekAngry', 'peekSleep']);
const BOTTOM = new Set(['peekBottom', 'sleepBottom']);
const OUTFITS = {
  maid: { name: '女仆装' }, // 原来所有的立绘
  pajamas: {
    name: '睡衣',
    off: '晚上', // 不是日子却穿着时说「明明不是晚上……」
    when: () => isNight(),
    has: ['idle', 'sleepy', 'wake', 'smug', 'pat', 'sleep', 'peekSleep', 'dangle', 'happy', 'wave', 'read'],
    alias: { peek: 'peekSleep', peekPhone: 'peekSleep', peekCheek: 'peekSleep', peekHead: 'peekSleep', smirk: 'smug', bleh: 'smug', excited: 'happy', meh: 'idle', pout: 'idle', surprised: 'sleepy', angry: 'wake' },
  },
  yukata: {
    name: '浴衣',
    off: '夏天',
    when: (d) => inRange(d, 701, 831),
    has: ['idle', 'wave', 'smug', 'angry', 'pat', 'happy', 'run', 'peek', 'dangle', 'read', 'onigiri', 'surprised', 'sleep'],
    frames: { run: ['run1', 'run2'] }, // 跑步两帧轮流换
    alias: {
      smirk: 'smug', bleh: 'smug', meh: 'idle', pout: 'angry', excited: 'happy', wake: 'angry',
      peekPhone: 'peek', peekCheek: 'peek', peekHead: 'peek', peekAngry: 'peek',
    },
  },
};
// 节日/季节衣服（festivals.js 里那些）每套只有一张待机图：什么动作都用它
const outfitInfo = (id) => OUTFITS[id] || festById(id) || OUTFITS.maid;
const outfitName = (id) => outfitInfo(id).name;
const outfitHas = (id) => (id === 'maid' ? null : OUTFITS[id]?.has || ['idle']);
// 这套衣服的某个动作实际用哪张（女仆装返回 null：什么都有）
function outfitKey(outfit, m) {
  const has = outfitHas(outfit);
  if (!has) return null;
  if (has.includes(m)) return m;
  const a = OUTFITS[outfit]?.alias?.[m];
  if (a && has.includes(a)) return a;
  for (let k = NEAR[m], n = 0; k && n < 3; k = NEAR[k], n++) if (has.includes(k)) return k;
  return 'idle';
}
// 某套衣服的某个动作 → 图片路径（跑步这种多帧的返回数组）
function spriteFor(outfit, m) {
  // 指名要某套节日衣服的那张（抽签、季节闲逛）：只在穿着女仆装或正好是那套时换，别的衣服不换
  if (festById(m)) return outfit === 'maid' || outfit === m ? `sprites/${m}.webp` : spriteFor(outfit, 'idle');
  const k = outfitKey(outfit, m);
  if (k === null) return `sprites/${m === 'angry' ? 'strike' : m}.webp`; // 女仆装
  if (festById(outfit)) return `sprites/${outfit}.webp`;
  const fr = OUTFITS[outfit].frames?.[k];
  return fr ? fr.map((f) => `sprites/${outfit}/${f}.webp`) : `sprites/${outfit}/${k}.webp`;
}
// 躲在边上却没有探头图、只能拿整张图顶上时：'side' 往屏幕外推一半，'bottom' 往下沉一半
function standInFor(outfit, m) {
  const k = outfitKey(outfit, m);
  if (k === null || festById(m)) return '';
  if (DOCKED.has(m) && !DOCKED.has(k)) return 'side';
  if (BOTTOM.has(m) && !BOTTOM.has(k)) return 'bottom';
  return '';
}
