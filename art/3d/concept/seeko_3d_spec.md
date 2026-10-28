# 希可 3D（VRM）版 规格 v0

2026-10-28 定：桌宠从 Live2D 转 3D。目标效果 = Desktop Mate 那种能转身、能从任何方向拎起的实时互动角色。
参考图：`seeko_turnaround_2026-10-28.png`（正 / 左侧 / 背三视图）。**不要鲸鱼尾巴**，其余照图。

## 角色
- 比例：三头身半左右（头大、腿短、手臂露出），不是现在 Live2D 的两头身。
- 脸：大圆眼、蓝瞳、浅色高光，微笑弧嘴，腮红；表情要能做：happy / smug / angry / shy / sleepy / surprised / pout / wink / teary / deadpan / sparkle / puff / dazed / blush / grin（VRM Expression，先做 happy/angry/sad/relaxed/surprised + blink + 口型 aa/ih/ou/ee/oh，其余用自定义 expression）。
- 头发：蓝色长卷发到腰，前发齐刘海，两侧长发，头顶呆毛，后脑勺大蓝蝴蝶结，侧边小蓝蝴蝶结；**耳鳍**（鲸鱼耳）代替人耳。头发挂 SpringBone（前发 / 侧发 / 后发分 3～4 组，呆毛单独一组）。
- 衣服：女仆装——深蓝短泡泡袖连衣裙、白围裙（围裙上小鲸鱼图案）、白蕾丝领和裙摆、白色头饰（发带型）、黑裤袜、深蓝玛丽珍鞋。裙摆、围裙挂 SpringBone。

## 工具链
VRoid Studio（捏脸/发/体型/衣服，贴图自定义）→ 导出 VRM 1.0（减面：目标 ≤ 20k 三角、贴图合并成 1～2 张 2048）→ Blender + VRM Add-on（检查、补弹簧骨、做动作、再导出）→ 桌宠 three.js + @pixiv/three-vrm。

## 桌宠需要的
- LookAt：眼睛 + 头 + 一点上身跟鼠标（VRM LookAt 只管眼，头和身子用骨骼插值）。
- 动作（骨骼关键帧，做法沿用 motionlib 的"预备→主动作→过冲→停顿、关节错帧"）：待机 ×3、走路、挥手、蹦、害羞、吓一跳、拎起（全身被提着晃）、下落、落地、欢呼、伸懒腰、歪头、点头、摇头、踢、垂头、喘气、横拖荡、坐下（坐窗口顶上用）。
- 换装：VRM 不方便换衣，先一套；以后用多个 VRM 或 Blender 里做衣服开关。
- 渲染：MToon 卡通描边，窗口 240×260 透明背景，30 fps；像素模式照旧用后处理。
