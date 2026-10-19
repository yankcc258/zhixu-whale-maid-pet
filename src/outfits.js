// 衣服和立绘：希可现在穿哪套、某个表情/动作该显示哪张图。
// 立绘都是整张图（不分层）。每套衣服只画了一部分动作，缺的按下面的规则「回退」：
//   1. 这套衣服画了这个动作 → 用它
//   2. alias 里写了用哪张代替（比如睡衣没画「开心」，就用「屑笑」）→ 用那张
//   3. 换衣服很难画的动作（被拎起来、跑、探头、睡觉……，见 BORROW）→ 借女仆装的整张图
//   4. 其他（只是表情不一样）→ 用这套衣服的待机图，配上 CSS 动画（duang、抖、呼吸）
// 文件放在 sprites/<衣服>/<动作>.webp；女仆装就是 sprites/ 下面原来那些图。
// 新画的衣服：加一项到 OUTFITS，把画好的动作写进 has，缺的写 alias，其他的自动回退。
const BORROW = new Set([
  'dangle', 'run', 'sleep', 'sleepy', 'wake', 'peek', 'peekPhone', 'peekCheek', 'peekHead', 'peekAngry', 'peekSleep',
  'peekBottom', 'sleepBottom', 'read', 'onigiri', 'umbrella', 'hot', 'cold', 'angry', 'wave', 'newyear', 'surprised', 'pat',
]);
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
// 节日/季节衣服（festivals.js 里那些）每套只有一张待机图：表情都用它，难的动作借女仆装
const outfitInfo = (id) => OUTFITS[id] || festById(id) || OUTFITS.maid;
const outfitName = (id) => outfitInfo(id).name;
// 某套衣服的某个动作 → 图片路径（跑步这种多帧的返回数组）
function spriteFor(outfit, m) {
  if (festById(m)) return `sprites/${m}.webp`; // 指名要某套节日衣服的那张
  const o = OUTFITS[outfit];
  if (o?.has) {
    const k = o.has.includes(m) ? m : o.alias?.[m];
    if (k && o.has.includes(k)) {
      const fr = o.frames?.[k];
      return fr ? fr.map((f) => `sprites/${outfit}/${f}.webp`) : `sprites/${outfit}/${k}.webp`;
    }
    if (!BORROW.has(m)) return `sprites/${outfit}/idle.webp`;
  } else if (festById(outfit) && !BORROW.has(m)) return `sprites/${outfit}.webp`;
  return `sprites/${m === 'angry' ? 'strike' : m}.webp`; // 女仆装
}
