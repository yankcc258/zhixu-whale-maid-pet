// 检查立绘：每套衣服的每个表情/动作都能找到图片文件；女仆装和以前（sprites/<表情>.webp）完全一样。
import { readFileSync, existsSync } from 'node:fs';
import vm from 'node:vm';
const ctx = { isNight: () => false, pick: (a) => a[0], Intl, Date, console };
vm.createContext(ctx);
vm.runInContext(
  readFileSync('src/festivals.js', 'utf8') + readFileSync('src/outfits.js', 'utf8') + '\nthis.FESTS=FESTS;this.OUTFITS=OUTFITS;this.spriteFor=spriteFor;',
  ctx,
);
const moods = [...new Set([...readFileSync('src/pet.js', 'utf8').matchAll(/'([a-zA-Z]+)'/g)].map((m) => m[1]))].filter((m) =>
  existsSync(`src/sprites/${m === 'angry' ? 'strike' : m}.webp`),
);
const outfits = [...Object.keys(ctx.OUTFITS), ...ctx.FESTS.map((f) => f.id)];
let bad = 0;
for (const o of outfits)
  for (const m of moods) {
    const src = ctx.spriteFor(o, m);
    for (const f of [src].flat())
      if (!existsSync('src/' + f)) {
        console.error(`缺图：${o} / ${m} → ${f}`);
        bad++;
      }
  }
for (const m of moods) {
  const was = `sprites/${m === 'angry' ? 'strike' : m}.webp`;
  if (ctx.spriteFor('maid', m) !== was) {
    console.error(`女仆装变了：${m} → ${ctx.spriteFor('maid', m)}（以前是 ${was}）`);
    bad++;
  }
}
for (const [id, o] of Object.entries(ctx.OUTFITS))
  for (const k of o.has || [])
    for (const f of o.frames?.[k] || [k])
      if (!existsSync(`src/sprites/${id}/${f}.webp`)) {
        console.error(`衣服 ${id} 说有 ${k}，但没有 sprites/${id}/${f}.webp`);
        bad++;
      }
if (bad) process.exit(1);
console.log(`立绘检查通过：${outfits.length} 套衣服 × ${moods.length} 个表情/动作都有图，女仆装和以前一致。`);
