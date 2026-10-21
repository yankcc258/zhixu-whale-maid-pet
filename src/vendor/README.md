# 第三方运行库（Live2D 用）

这些文件原样放在这里，**不在本项目的 MIT 范围内**，各自按自己的许可分发：

| 文件 | 是什么 | 许可 |
|---|---|---|
| `live2dcubismcore.min.js` | Live2D Cubism Core 4.2.2（读 `.moc3`） | Live2D Proprietary Software License Agreement（文件属于其中的 Redistributable Code）：https://www.live2d.com/eula/live2d-proprietary-software-license-agreement_en.html 。个人、非商用使用。商用或年收入超过规定额度时要另外和 Live2D 签约。 |
| `pixi.min.js` | PixiJS 6.5.10 | MIT |
| `pixi-unsafe-eval.min.js` | @pixi/unsafe-eval 6.5.10（不用 `eval` 也能跑，配合 CSP） | MIT |
| `cubism4.min.js` | pixi-live2d-display 0.4.0（Cubism 4 部分） | MIT，内含 Live2D Cubism Framework（Live2D Open Software License） |

`src/live2d/seeko/` 是希可的 Live2D 模型（由 Cubism Editor 导出），和立绘一样不在 MIT 范围内。
