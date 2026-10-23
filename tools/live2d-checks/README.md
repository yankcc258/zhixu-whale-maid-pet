# 希可 Live2D 验收工具

参考 live2d-agent-kit（MIT）的检查清单写的无头浏览器截图脚本。每次改骨架、换底稿后跑一遍，逐张看图。

- `checks.js`：半睁眼（0.8～0.2、单眼、闭眼+转头）、嘴型 × 张嘴 15 种组合、头和身体反着转、转头极限、手臂组合、8 个动作每 120ms 一帧。输出 `check_<模型>_*.png`。
- `pose.js`：14 个参数极值姿势。
- `pview.html`：加载模型的测试页（需要 `node_modules` 里的 pixi.js 6、pixi-live2d-display、live2dcubismcore）。
- `caff.py` / `model.py` / `tree.py`：读写 .cmo3（解出 main.xml、改完写回），打印变形器树。

用法：`RT=<模型运行包目录> node checks.js seeko`
