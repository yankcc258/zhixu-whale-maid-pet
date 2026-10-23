// 检查立绘：每套衣服的每个表情/动作都能找到图片文件；女仆装和以前（sprites/<表情>.webp）完全一样。
import { readFileSync, existsSync } from 'node:fs';
import vm from 'node:vm';
const ctx = { isNight: () => false, pick: (a) => a[0], Intl, Date, console };
vm.createContext(ctx);
vm.runInContext(
  readFileSync('src/festivals.js', 'utf8') + readFileSync('src/outfits.js', 'utf8') + '\nthis.FESTS=FESTS;this.OUTFITS=OUTFITS;this.spriteFor=spriteFor;this.festById=festById;this.outfitInfo=outfitInfo;',
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
// 节日衣服补画的动作：写在 has 里的都要有 sprites/<节日>/<动作>.webp
for (const f of ctx.FESTS)
  for (const k of f.has || [])
    if (k !== 'idle')
      for (const fr of f.frames?.[k] || [k])
        if (!existsSync(`src/sprites/${f.id}/${fr}.webp`)) {
          console.error(`节日衣服 ${f.id} 说有 ${k}，但没有 sprites/${f.id}/${fr}.webp`);
          bad++;
        }
// 专属台词：每条都是字符串或 [台词, 表情]，表情得是画得出来的；装饰是字符串
for (const o of outfits) {
  const info = ctx.outfitInfo(o);
  for (const [kind, list] of Object.entries(info.say || {}))
    for (const x of list) {
      const [t, m] = Array.isArray(x) ? x : [x, null];
      if (typeof t !== 'string' || !t.trim()) (console.error(`${o} 的 ${kind} 台词是空的`), bad++);
      if (m && !existsSync(`src/sprites/${m === 'angry' ? 'strike' : m}.webp`)) (console.error(`${o} 的 ${kind} 台词表情 ${m} 没有图`), bad++);
    }
  for (const ch of info.fx || []) if (typeof ch !== 'string') (console.error(`${o} 的装饰不是字符串`), bad++);
}
// 除了女仆装，别的衣服任何动作都不能露出女仆装的图
const maidFiles = new Set(moods.map((m) => `sprites/${m === 'angry' ? 'strike' : m}.webp`));
for (const o of outfits.filter((o) => o !== 'maid'))
  for (const m of moods.filter((m) => !ctx.festById(m)))
    for (const f of [ctx.spriteFor(o, m)].flat())
      if (maidFiles.has(f) && f !== `sprites/${o}.webp`) {
        console.error(`${o} 的 ${m} 变回了女仆装：${f}`);
        bad++;
      }
if (bad) process.exit(1);
console.log(`立绘检查通过：${outfits.length} 套衣服 × ${moods.length} 个表情/动作都有图，女仆装和以前一致，其他衣服不会变回女仆装。`);
