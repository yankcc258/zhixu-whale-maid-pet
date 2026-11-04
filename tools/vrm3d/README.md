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

## 11-03 白狐 v4 流水线（正常比例主线）
```
CURL=s TIP=F8FAFF FLUFF=0.045 python3 seeko_post.py raw.vrm a.vrm 0.034 0.20 \
  Shoes_01_CLOTH=tex_v2/shoes_mj.png Tops_01_CLOTH_01=tex_v2/skirt_v4.png Tops_01_CLOTH=tex_v2/dress_top_v3.png \
  Onepiece_00_CLOTH=tex_v2/collar_navy.png FoxTail_01=tex_v2/foxtail_white.png CatEar_01=tex_v2/ear_white_soft.png
AHOGE=CCD5E3,F2F5FA python3 add_accessories.py a.vrm b.vrm        # 头饰/蝴蝶结/呆毛
WBOW=1.5 python3 body_accessories.py b.vrm c.vrm                   # 腰后白蝴蝶结 + 白腕口
TAIL_UP=11 python3 kiko_style.py c.vrm kiko_white_v4.vrm           # 浅色柔描边 + 尾巴弯曲 rest pose
```
- `CURL=s`：分层大 S 卷（相位沿头部平滑，振幅向发梢增大；不要用按束取整的相位，会翻面）
- `kiko_style.py`：头发/耳/尾/呆毛描边 #97A6C4 宽 0.0003，去 matcap 亮条，shade 0.80/0.83/0.90；尾骨 2–5 rest 旋转侧 14°/上 11°（递减）
- Q 版线路（fix_chibi_morphs / outline2d / V-Chibi）已搁置：2D 立绘改由特蕾莎手绘重画

## 动捕路线（11-03 晚）
- 桌宠 `src/vrm.js` 支持 VRMA（`MOTIONS` 表：动作名 → `vrm/motion/*.vrma`，有文件优先播动捕，crossfade，播完接回弹簧关键帧）。
- `fbx2vrma.py model.vrm motion.fbx out.vrma [--start --end --step --fps]`：云端无头 Blender（`pip install bpy bpy-vrm-format`）把 Mixamo FBX 重定向到 VRM 人形骨骼并导出 VRMA。原理：每根骨骼取 Mixamo 的世界空间旋转增量（pose·rest⁻¹）套到 VRM 对应骨骼，髋骨位移按髋高缩放；两边只要都是 T-pose 就能对上。用 three.js 的 Samba Dancing.fbx 验证通过（kiko_mocap_samba_test.png）。
- `make_vrma.py out.vrma`：最小 VRMA 生成器（测播放路径用）。

## Blender 无头流水线（11-03 晚）
- `pip install bpy==5.2.3 bpy-vrm-format` 后 `bpy.ops.import_scene.vrm / export_scene.vrm / vrma` 可用。往返测试：后处理模型进出 Blender，饰品/57 表情/40 弹簧骨全保留（roundtrip_cmp.png）。
- `seeko_post.py` 新增 `N:<材质子串>=normal.png` 覆盖法线贴图；`Body_00_SKIN=body_tights.png` 丝袜（罗纹 9px 周期 ±3.5、胫骨光泽、炭灰底色）。
- `add_accessories.py` 头饰褶边改成 alpha 裁出的圆扇贝 + 眼孔（材质 MASK，无描边）。
- `blender_lace.py`：沿裙摆加蕾丝条的尝试——**未成**：VRoid 裙子网格比可见布料长（长度靠贴图 alpha），按 alpha 边界找到的下摆（z≈0.50–0.58）比渲染里的荷叶边还低 10cm，还没弄清（可能荷叶边是 CLOTH_04、渲染姿态裙骨影响）。下次思路：直接按裙子弹簧骨末端的位置做环，并作为 Body 网格的新 primitive 复用其 skin（JOINTS_0 指向最近的裙骨）。

## 备份与重建（11-05，主人电脑重装系统后）
- `art/3d/vrm/kiko_white_raw1.vrm` = VRoid 导出的原始模型（整条流水线的起点）；`kiko_white_v12.vrm` = 当前成品（未打包）。
- ⚠️ VRoid 存档 `seeko_3d_v3_fox.vroid` 只在主人电脑上，**没有进仓库**；只要 raw1.vrm 在，模型就能完全重建，但想回 VRoid 改发型/体型需要那个 .vroid。
- 重建 v12（在 tools/vrm3d 目录，贴图在 art/3d/tex_v2 与 art/3d/tex_hd）：
```
CURL=s TIP=F8FAFF FLUFF=0.045 python3 seeko_post.py raw1.vrm a.vrm 0.034 0.20 \
  Shoes_01_CLOTH=tex_hd/tex_current_shoes.png Tops_01_CLOTH_01=tex_hd/tex_current_skirt.png Tops_01_CLOTH=tex_hd/tex_current_dress_top.png \
  Onepiece_00_CLOTH=tex_hd/tex_current_collar.png FoxTail_01=tex_hd/tex_current_tail.png CatEar_01=tex_hd/tex_current_ears.png \
  Body_00_SKIN=tex_v2/body_socks.png Hair_00_HAIR=tex_hd/tex_current_hair_front.png HairBack_00_HAIR=tex_hd/tex_current_hair_back.png \
  Face_00_SKIN=tex_hd/tex_current_face.png EyeIris_00_EYE=tex_hd/tex_current_iris.png
AHOGE=CCD5E3,F2F5FA python3 add_accessories.py a.vrm b.vrm
WBOW=1.5 WBOW_UP=0.085 WBOW_OUT=0.015 python3 body_accessories.py b.vrm c.vrm
TAIL_UP=11 python3 kiko_style.py c.vrm d.vrm
python3 add_expressions.py d.vrm kiko_white_v12.vrm
python3 pack_vrm.py kiko_white_v12.vrm ../../src/vrm/kiko.vrm 2048   # 桌宠里用的打包版
```
- 动作源文件：`art/3d/motion/src_fbx/*.fbx`（Mixamo）→ `fbx2vrma.py` → `art/3d/motion/vrma/`。
