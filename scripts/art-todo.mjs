// 列出每套衣服还缺哪些常用动作立绘，按「一年里穿几天」排，先画最常穿的。
// 用法：node scripts/art-todo.mjs            看清单
//       node scripts/art-todo.mjs --md > ART-TODO.md   生成给画图用的清单
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const ctx = { isNight: () => false, pick: (a) => a[0], Intl, Date, console };
vm.createContext(ctx);
vm.runInContext(
  readFileSync('src/lines.js', 'utf8') + readFileSync('src/festivals.js', 'utf8') + readFileSync('src/outfits.js', 'utf8') +
    '\nthis.FESTS=FESTS;this.OUTFITS=OUTFITS;this.outfitHas=outfitHas;this.outfitInfo=outfitInfo;this.ART_CORE=ART_CORE;',
  ctx,
);
const NAMES = { happy: '开心', smug: '屑笑（得意）', angry: '生气', pat: '被摸头', dangle: '被拎起来（蹬腿）', surprised: '吓一跳', peek: '从右边探头', wave: '挥手', run: '跑步（两帧）' };
// 一年里大概穿几天：成套的衣服按用途估，节日按日期数
const daysOf = (id) => {
  const f = ctx.FESTS.find((x) => x.id === id);
  if (!f) return { pajamas: 365, winter: 60, gym: 30, jog: 30, lab: 30, yukata: 20 }[id] ?? 0;
  if (f.kind === 'manual') return 28;
  let n = 0;
  for (let d = new Date(2027, 0, 1); d.getFullYear() === 2027; d.setDate(d.getDate() + 1)) if (f.when(d)) n++;
  return n;
};
const rows = [...Object.keys(ctx.OUTFITS).filter((o) => o !== 'maid'), ...ctx.FESTS.map((f) => f.id)]
  .map((id) => ({ id, name: ctx.outfitInfo(id).name, days: daysOf(id), missing: ctx.ART_CORE.filter((m) => !ctx.outfitHas(id).includes(m)) }))
  .filter((r) => r.missing.length)
  .sort((a, b) => b.days - a.days);
const md = process.argv.includes('--md');
if (md) {
  console.log('# 希可立绘补图清单\n\n`node scripts/art-todo.mjs --md` 生成。按一年里穿几天排，越靠前越值得先画。\n');
  console.log('画图要求见 `src/sprites/README.md`：1024 以上正方形、透明或纯白背景、没有影子和文字，**人物大小和位置跟这套衣服的待机图一样**。');
  console.log('文件名 `<衣服>_<动作>_<表情>.png`（比如 `halloween_pat_happy.png`），传到 `art-inbox` 分支的 `art/inbox/`。\n');
}
for (const r of rows) {
  const list = r.missing.map((m) => (md ? `${NAMES[m]}（\`${r.id}_${m}\`）` : m)).join(md ? '、' : ' ');
  console.log(md ? `- **${r.name}**（\`${r.id}\`，一年约 ${r.days} 天）：${list}` : `${r.name.padEnd(6, '　')} ${String(r.days).padStart(3)} 天  缺：${list}`);
}
