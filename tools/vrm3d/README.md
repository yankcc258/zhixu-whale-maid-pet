# 希可 3D（VRM）工具
- `seeko_post.py in.vrm out.vrm [amp] [wavelen]`：VRoid 导出的 VRM 后处理——头发顶点按正弦位移做大波浪 + 发尾体积，头发贴图按 UV v（发根→发梢）渐变到浅蓝 #6BAEEE；刘海/头顶按高度把 v 夹在 ≤0.40 保持深蓝。
- `main.js` + `shot.js`：three@0.169 + @pixiv/three-vrm@3.1，esbuild 打包后用 playwright（swiftshader）无头渲染。
  `node shot.js model.vrm 前缀 mtoon [1=脸部特写]` → 前缀_front.png / 前缀_q.png（或 _face.png）。
