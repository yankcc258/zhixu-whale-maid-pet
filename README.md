# 🐋 鲸鱼娘桌宠

[知序](https://yank-study-lab.yank-study-lab.workers.dev)里那只屑鲸鱼娘，搬到 Windows 桌面上。用 [Tauri 2](https://tauri.app) 做：一个透明、无边框、永远在最上层的小窗口，外加右下角托盘图标。安装包十几 MB，用 Windows 10/11 自带的 WebView2 显示。

## 现在能做什么（0.1 准备版）

- 戳她：duang 一下，随机吐槽。
- 按住拖动：被拎起来的样子，松手放下。
- **双击：用默认浏览器打开知序。**
- 右键：菜单（打开知序、藏起来）。
- 托盘：左键单击叫出来；右键有「打开知序 / 叫出鲸鱼娘 / 藏起来 / 退出」。
- 23:00–6:00 换成睡觉的样子。
- 已经开着时再打开一次，不会多出第二只。

## 安装

1. 打开仓库的 **Actions** → 最新一次绿色的 `build` → 页面最下面 **Artifacts** 里下载 `ZhixuWhale-setup`。打了 `v` 开头标签的版本也会出现在 **Releases** 里。
2. 解压，双击 `ZhixuWhale_x.y.z_x64-setup.exe`。装在当前用户下，不需要管理员权限。
3. 安装包没有签名，Windows 可能弹「已保护你的电脑」：点「更多信息」→「仍要运行」。

## 自己改、自己打包

```bash
npm install
npm run dev     # 开发：改 src/ 里的网页会自动刷新
npm run build   # 打包：src-tauri/target/release/bundle/nsis/ 里出现安装程序
```

Windows 上要先装 [Rust](https://rustup.rs) 和 Visual Studio 的「使用 C++ 的桌面开发」。不想装也没关系，推到 GitHub 后 Actions 会自动打包。

## 目录

| 路径 | 内容 |
| --- | --- |
| `src/` | 窗口里的网页：`index.html`、`style.css`、`pet.js`（动作和台词） |
| `src/sprites/` | 16 张立绘，440px 透明 WebP |
| `src-tauri/src/lib.rs` | 窗口、托盘、打开知序（网址写死在这里） |
| `src-tauri/tauri.conf.json` | 窗口大小、透明、置顶、安装包设置 |
| `src-tauri/capabilities/` | 网页能调用哪些窗口功能（拖动、移动、隐藏……） |
| `app-icon.png` | 图标原图，`npx tauri icon app-icon.png -o src-tauri/icons` 生成各尺寸 |
| `.github/workflows/build.yml` | 在 Windows 机器上自动打包 |

## 路线图

- [x] 0.1 准备版：透明置顶窗口、拖动、戳、双击打开知序、托盘
- [ ] 把网页版的动作搬过来：躲在屏幕边探头、拎起来扑腾、睡觉飘 Z 和梦话、吵醒暴怒、摸头、番茄钟陪学
- [ ] 在整个桌面上乱跑（沿着任务栏），透明的地方让鼠标穿过去
- [ ] 开机自启（设置里开关）
- [ ] 接知序数据（只读）：今天吃了什么、待复习单词、作业，用来吐槽
- [ ] 好玩的：抓鼠标、按当前窗口标题吐槽（只在本机判断）、把文件拖给她吃

## 授权

- **代码**：MIT，见 [LICENSE](LICENSE)。
- **立绘**（`src/sprites/`、`app-icon.png`、`src-tauri/icons/`）：© Yank，不随 MIT 授权，只供本项目和个人非商业使用。立绘是 DeepSeek 鲸鱼娘的同人形象。
