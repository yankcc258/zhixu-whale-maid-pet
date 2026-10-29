# 希可 3D（VRM）工具
- `seeko_post.py in.vrm out.vrm [amp] [wavelen]`：VRoid 导出的 VRM 后处理——头发顶点按正弦位移做大波浪 + 发尾体积，头发贴图按 UV v（发根→发梢）渐变到浅蓝 #6BAEEE；刘海/头顶按高度把 v 夹在 ≤0.40 保持深蓝。
- `main.js` + `shot.js`：three@0.169 + @pixiv/three-vrm@3.1，esbuild 打包后用 playwright（swiftshader）无头渲染。
  `node shot.js model.vrm 前缀 mtoon [1=脸部特写]` → 前缀_front.png / 前缀_q.png（或 _face.png）。
- 贴图覆盖：`MaterialSubstr=path.png` 形式的额外参数，按材质名子串替换 baseColor 贴图。v6 用法：
  `python3 seeko_post.py seeko_v4.vrm seeko_v6.vrm 0.024 Shoes_01_CLOTH=art/3d/tex_v2/shoes_navy.png Tops_01_CLOTH_01=art/3d/tex_v2/skirt_v4.png Onepiece_00_CLOTH=art/3d/tex_v2/collar_navy.png`
  （注意 VRoid 每次导出材质编号可能变，换预设后先列一遍材质名再对。）
- `add_fins.py in.vrm out.vrm`：程序生成鲸鱼耳鳍（扇形+下沿波浪、外深蓝内浅紫贴图、复制头发 MToon 材质、双面），作为 head 骨骼子节点左右各一（右边 scale x=-1）。位置/角度在脚本底部（眼睛高度+3cm、外扫 22°、下垂 38°）。
- 完整流水线：VRoid 导出 → `seeko_post.py`（卷发/渐变/贴图覆盖）→ `add_fins.py` → 预览/桌宠。
