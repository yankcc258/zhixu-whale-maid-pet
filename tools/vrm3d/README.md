# 希可 3D（VRM）工具
- `seeko_post.py in.vrm out.vrm [amp] [wavelen]`：VRoid 导出的 VRM 后处理——头发顶点按正弦位移做大波浪 + 发尾体积，头发贴图按 UV v（发根→发梢）渐变到浅蓝 #6BAEEE；刘海/头顶按高度把 v 夹在 ≤0.40 保持深蓝。
- `main.js` + `shot.js`：three@0.169 + @pixiv/three-vrm@3.1，esbuild 打包后用 playwright（swiftshader）无头渲染。
  `node shot.js model.vrm 前缀 mtoon [1=脸部特写]` → 前缀_front.png / 前缀_q.png（或 _face.png）。
- 贴图覆盖：`MaterialSubstr=path.png` 形式的额外参数，按材质名子串替换 baseColor 贴图。v6 用法：
  `python3 seeko_post.py seeko_v4.vrm seeko_v6.vrm 0.024 Shoes_01_CLOTH=art/3d/tex_v2/shoes_navy.png Tops_01_CLOTH_01=art/3d/tex_v2/skirt_v4.png Onepiece_00_CLOTH=art/3d/tex_v2/collar_navy.png`
  （注意 VRoid 每次导出材质编号可能变，换预设后先列一遍材质名再对。）
- `add_fins.py in.vrm out.vrm`：程序生成鲸鱼耳鳍（扇形+下沿波浪、外深蓝内浅紫贴图、复制头发 MToon 材质、双面），作为 head 骨骼子节点左右各一（右边 scale x=-1）。位置/角度在脚本底部（眼睛高度+3cm、外扫 22°、下垂 38°）。
- 完整流水线：VRoid 导出 → `seeko_post.py`（卷发/渐变/贴图覆盖）→ `add_fins.py` → 预览/桌宠。
- `add_accessories.py in.vrm out.vrm`：程序生成并挂到 head 骨骼——白色褶边女仆头饰（按头发表面拟合弧线）、后脑大蓝蝴蝶结（×1.8）、耳鳍根部两个小蓝蝴蝶结、呆毛（贝塞尔弯月形）。
- 现行流水线（v8）：VRoid 导出 seeko_v4.vrm → `seeko_post.py ... 0.024 Shoes_01_CLOTH=… Tops_01_CLOTH_01=… Onepiece_00_CLOTH=…` → `add_fins.py` → `add_accessories.py` → seeko_v8.vrm。
- 希狐现行流水线（v5）：VRoid `seeko_3d_v3_fox.vroid` 导出 → `FLUFF=0.05 seeko_post.py raw.vrm a.vrm 0.030 0.11 Shoes_01_CLOTH=… Tops_01_CLOTH_01=… Onepiece_00_CLOTH=… FoxTail_01=art/3d/tex_v2/foxtail_grad.png` → `add_accessories.py a.vrm kiko.vrm`（含狐耳内收 10°、中间刘海缩短 20%、头饰 34°–146°、小蝴蝶结在耳根外下）。不再跑 add_fins.py。
- **白狐（2026-11-03 定稿配色）**：VRoid 头发主色/猫耳/狐尾 = #D6DEEA；流水线 `TIP=F8FAFF FLUFF=0.05 seeko_post.py raw a.vrm 0.030 0.11 …同前… FoxTail_01=art/3d/tex_v2/foxtail_white.png CatEar_01=art/3d/tex_v2/ear_white_pink.png` → `AHOGE=CCD5E3,F2F5FA add_accessories.py a.vrm kiko.vrm`。`recolor_fur.py` 可把任意版本整体换毛色（dark light 两个 hex）。
- **Q 版流水线（网页立绘用）**：V-Chibi（約4頭身预设 + Head size -0.55 ≈ 3.45 头身，Hair length -0.41）导出 → `fix_chibi_morphs.py chibi.vrm 原版raw.vrm out.vrm`（把脸部 morph 按头放大比例放大，否则闭不上眼）→ `TIP=F8FAFF FLUFF=0.03 seeko_post.py … 0.016 0.10 …同覆盖…` → `ACC_SCALE=1.34 AHOGE=… add_accessories.py`。
- **立绘渲染**：`node sprite_shot.js model.vrm 输出目录 idle,happy,… [toon=1] [hs=1.35]`（sprite.js 里 PRESETS 表 = 表情权重+骨骼角度+构图；toon 加粗描边、平涂；hs 镜头放大倍率，Q 版用 1.35）→ 880px PNG，再缩成 220px WebP。
- `add_expressions.py in out`：把脸部 57 个 morph 全部挂成 VRM 自定义表情 `m_<名字>`（如 m_Fcl_MTH_SkinFung_R 单侧坏笑嘴、m_Fcl_HA_Fung1 虎牙、m_Fcl_BRW_Angry 怒眉），sprite.js 预设里可直接混用。
- `outline2d.py in.png out.webp [线宽@220px] [颜色]`：对透明渲染图加外轮廓线再缩成 220px WebP；配合 `toon=2`（头发去内线/去法线/去 matcap）得到接近手绘的平涂+外描边。第三轮用 `node sprite_shot.js kiko.vrm 目录 预设 2 1.12 0.06`。
