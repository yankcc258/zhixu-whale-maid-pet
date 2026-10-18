# 🐋 鲸鱼娘桌宠

[知序](https://yank-study-lab.yank-study-lab.workers.dev)里那只屑鲸鱼娘，搬到 Windows 桌面上。用 [Tauri 2](https://tauri.app) 做：一个透明、无边框、永远在最上层的小窗口，外加右下角托盘图标。安装包十几 MB，用 Windows 10/11 自带的 WebView2 显示。

## 现在能做什么（0.2）

- **戳她**：duang 一下吐槽。半夜和早上戳她有不一样的反应。3 秒内连戳 6 下会举「罢工」牌警告，再戳就躲进托盘（托盘里点一下叫回来）。
- **拎起来**：按住拖动时是被拎着蹬腿的样子，放下来会抱怨。
- **躲在屏幕边**：拖到屏幕左右边松手，她缩进去只露半个头。戳她会被戳脸或戳头（气鼓鼓），乱戳会生气；躲久了会偷偷玩手机；晚上在边上睡着。拖出来就恢复。
- **钻到任务栏下面睡**：睡着时把她拖到屏幕最下面，她会钻下去只露个头接着睡；戳一下或者天亮了就爬出来。
- **睡觉**（默认 23:00–6:00）：戴眼罩、身子起伏、头顶飘 Z、偶尔说梦话。戳一下迷糊地醒，十几秒内再戳就举枕头暴怒，过一会儿又睡回去。早上醒来伸懒腰。
- **摸头**：鼠标不按键，在她头上左右来回划。会眯眼享受，还能消气。
- **乱跑**：按活跃度在当前高度左右跑一趟。
- **自己冒话**：按时间段吐槽（熬夜、饭点、下午犯困、电脑开太久……），频率可调。
- **双击打开网站**（默认知序，设置里可以换）；右键菜单：打开网站、说点什么、设置、安静模式、藏进托盘。
- **鼠标穿透**：透明的地方不挡鼠标，旁边的桌面图标照常能点。
- **全屏时躲起来**：最前面是全屏程序（游戏、全屏视频）时自动隐藏，退出全屏再出来。
- **设置窗口**（右键菜单或托盘）：她怎么叫你（默认 Yank）、双击打开哪个网站（默认知序）、吐槽频率、活跃度、睡觉时间、全屏时躲起来、安静模式、开机自启、位置复位。
- 记住上次的位置；已经开着时再打开一次，不会多出第二只。

### 会不会被游戏反作弊当成外挂？

她是一个普通的置顶小窗口：不读别的程序的内存、不往游戏里注入东西、不装键盘鼠标钩子，也不需要管理员权限。全屏检测只是问 Windows「最前面的窗口有多大」。反作弊一般针对的是注入、读内存和驱动，所以风险很低；不过没法替每个游戏打包票，特别在意的话，打排位前在托盘里点「退出」最保险。

## 安装

1. 到 [Releases](https://github.com/yankcc258/zhixu-whale-maid-pet/releases/latest) 下载最新的 `ZhixuWhale_x.y.z_x64-setup.exe`（测试版在本仓库 **Actions** → 某次 `build` → **Artifacts**）。
2. 双击安装。装在当前用户下，不需要管理员权限。
3. 安装包没有签名，Windows 可能弹「已保护你的电脑」：点「更多信息」→「仍要运行」。

## 更新

装好以后不用再手动下载：鲸鱼娘启动 1 分钟后、之后每 6 小时会去本仓库的 [Releases](https://github.com/yankcc258/zhixu-whale-maid-pet/releases/latest) 看一眼。有新版本她会问「要不要更新」，点「好，更新」就自动下载、安装、重启。托盘菜单里也能手动「🔄 检查更新」。

安装包带签名，公钥写在 `tauri.conf.json` 里，签名对不上的安装包她不会装。

### 发新版本

1. 改版本号：`package.json`、`src-tauri/tauri.conf.json`、`src-tauri/Cargo.toml` 三处一致。
2. 在 `release-notes.md` 写这一版改了什么（会显示在 Release 页面和更新提示里）。
3. 合并到 main 后打标签：`git tag v0.3.0 && git push origin v0.3.0`。
4. Actions 自动打包、签名，把安装包、`.sig` 和 `latest.json` 发布到本仓库的 Releases。

需要的 Secrets：`TAURI_SIGNING_PRIVATE_KEY`、`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`（更新签名私钥和密码，私钥文件留在 Yank 自己电脑上备份）。私钥丢了的话，生成一把新的、换掉配置里的公钥，再手动装一次新版本就行。

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
| `src/` | 窗口里的网页：`index.html`、`style.css`、`pet.js`（动作）、`lines.js`（台词）、`settings.*`（设置窗口） |
| `src/sprites/` | 22 张立绘，440px 透明 WebP（不在 MIT 范围内，见 PROVENANCE.md） |
| `src-tauri/src/lib.rs` | 窗口、托盘、鼠标穿透、全屏检测、开机自启、设置窗口、打开知序（网址写死在这里） |
| `src-tauri/tauri.conf.json` | 窗口大小、透明、置顶、安装包设置 |
| `src-tauri/capabilities/` | 网页能调用哪些窗口功能（拖动、移动、隐藏……） |
| `app-icon.png` | 图标原图，`npx tauri icon app-icon.png -o src-tauri/icons` 生成各尺寸 |
| `.github/workflows/build.yml` | 在 Windows 机器上自动打包；打 `v*` 标签时签名并发布到 Releases |
| `scripts/latest-json.mjs` | 生成更新用的 `latest.json` |
| `release-notes.md` | 这一版的更新说明 |

## 路线图

- [x] 0.1 准备版：透明置顶窗口、拖动、戳、双击打开知序、托盘
- [x] 0.2：躲边、扑腾、睡觉和梦话、吵醒暴怒、摸头、乱跑、鼠标穿透、全屏时躲起来、设置窗口、开机自启
- [x] 0.3：自动更新
- [ ] 番茄钟陪学（看书的立绘已经有了）
- [ ] 爬到窗口顶上坐着、沿着任务栏跑
- [ ] 接知序数据（只读）：今天吃了什么、待复习单词、作业，用来吐槽
- [ ] 好玩的：抓鼠标、按当前窗口标题吐槽（只在本机判断）、把文件拖给她吃

## 授权与致谢

- **代码**：MIT，见 [LICENSE](LICENSE)。
- **立绘和图标**（`src/sprites/`、`app-icon.png`、`src-tauri/icons/`）：**不在 MIT 范围内**，按原样随程序分发，仅用于运行本程序。来源和说明见 [PROVENANCE.md](PROVENANCE.md)。
- 鲸鱼娘的形象参考了 [MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget) 的鲸鱼娘，谢谢原作者。本项目和 DeepSeek 官方无关。
