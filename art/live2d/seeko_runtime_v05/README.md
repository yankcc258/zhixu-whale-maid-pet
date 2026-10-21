# 希可 Live2D 运行包（seeko_v05）

由 `seeko_v05.cmo3` 导出（Cubism Editor 5.3.04，导出目标 SDK 4.2 兼容），露娜整理表情和动作。

## 文件
- `seeko.model3.json`：入口
- `seeko.moc3`、`seeko.2048/texture_00.png`（2048×2048 一张）
- `seeko.physics3.json`：前发、侧发、后发 3 组物理（输入：头部角度 X/Z、身体角度 X/Z）
- `seeko.cdi3.json`：参数名表
- `expressions/`：happy、smug、angry、shy、sleepy、surprised、pout（名字和桌宠心情一致）
- `motions/`：Idle（8 秒循环）、Nod（点头）、Shake（摇头）、Swing（被拎起来甩头）

## 参数（已绑定）
| ID | 用途 | 范围 |
|---|---|---|
| ParamAngleX / Y / Z | 头左右转 / 上下 / 歪头 | -30 ~ 30 |
| ParamBodyAngleX / Z | 身体左右转 / 左右歪 | -10 ~ 10 |
| ParamBreath | 呼吸 | 0 ~ 1 |
| ParamEyeLOpen / ParamEyeROpen | 眨眼（0 闭 1 开） | 0 ~ 1 |
| ParamEyeLSmile / ParamEyeRSmile | 闭眼时变成 ^^ 笑眼 | 0 ~ 1 |
| ParamEyeBallX / Y | 眼珠（看鼠标） | -1 ~ 1 |
| ParamMouthOpenY | 张嘴：0 是 :3，0.5 微张，1 大张 | 0 ~ 1 |
| ParamMouthForm | 1 时张嘴变成 O 型（吓一跳） | -1 ~ 1 |
| ParamCheek | 脸红加深 | 0 ~ 1 |
| ParamBrowLY / RY | 眉毛上下（被刘海挡住，效果很小） | -1 ~ 1 |
| ParamHairFront / Side / Back | 头发摆动（由物理驱动） | -1 ~ 1 |

Groups：EyeBlink = 两个眼睛开闭；LipSync = ParamMouthOpenY。

## 已知限制
- 闭眼时眼角有一点很淡的残留描边（放大才看得见，桌宠尺寸下看不出）
- 眉毛被刘海挡住，生气/委屈主要靠眼神、脸红和歪头表现
- 半眯眼（眼皮盖下来）还没做，屑笑暂时用 ^^ 笑眼
- 身体前后（BodyAngleY）、眉毛角度/形状、手臂参数还没绑定
