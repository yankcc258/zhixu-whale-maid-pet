# 希可的立绘

全部是整张图（不分层），440px 正方形透明 WebP。

## 放在哪

- `sprites/<表情>.webp`：女仆装（最早的那批），比如 `happy.webp`、`peek.webp`
- `sprites/<节日>.webp`：节日/季节衣服，每套一张待机图，id 见 `src/festivals.js`
- `sprites/<衣服>/<动作>.webp`：成套的衣服，比如 `pajamas/sleep.webp`、`yukata/run1.webp`
- `sprites/<节日>/<动作>.webp`：节日/季节衣服补画的动作（待机图还是 `sprites/<节日>.webp`），在 `festivals.js` 那一项写上 `has`

还缺哪些图：`npm run art-todo`（按一年里穿几天排），给 AI 画图的提示词模板在根目录 `ART-TODO.md`。
- `../fx/<名字>-<编号>.webp`：飘落的装饰（雪花、樱花瓣、枫叶、星星、雨滴、蝙蝠），64px

## 缺图怎么办

见 `src/outfits.js` 开头的注释：先找这套衣服画好的，再找 alias 里的代替，难画的动作借女仆装，
只是表情不同的就用这套衣服的待机图。`npm run check` 会检查每套衣服的每个动作都能找到图。

## 新画一套衣服

1. 原图传到 `art-inbox` 分支的 `art/inbox/`（不要合并那个分支）。
2. 画图要求：1024 以上的正方形，透明或纯白背景，地上不画影子，不写字；
   **人物大小和位置跟女仆装待机图一样**（底边贴近画布底，头顶高度一致）。
   探头：从右边边缘探出来，扒着边缘的手指贴着画布右边。
3. 文件名 `<衣服>_<动作>_<表情>`，比如 `pajamas_peek_sleepy`；跑步这种多帧的加 `_f1`、`_f2`。
4. 在 `OUTFITS` 里加一项：`name`、`has`（画了哪些）、`alias`（缺的用哪张代替）、
   可选 `frames`（多帧）、`when` 和 `off`（什么时候算应季，不应季时她会嘴硬）。
