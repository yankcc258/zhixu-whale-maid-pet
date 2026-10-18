//! 鲸鱼娘桌宠：一个透明、无边框、永远在最上层的小窗口，外加右下角托盘图标。
//! 窗口里的动画和台词都在 src/（网页）；这里管窗口、托盘、鼠标穿透、全屏时躲起来、开机自启和「打开知序」。
//!
//! 不读别的程序的内存、不注入、不装键盘鼠标钩子。全屏检测只问 Windows「最前面的窗口有多大」。
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Mutex,
};
use std::time::Duration;
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_updater::UpdaterExt;

const ZHIXU_URL: &str = "https://yank-study-lab.yank-study-lab.workers.dev";
/// 自动检查更新的间隔
const UPDATE_EVERY: Duration = Duration::from_secs(6 * 3600);

/// 网页告诉这里「哪些地方是鲸鱼娘」（窗口内的 CSS 像素矩形 [x, y, w, h]），
/// 鼠标不在这些地方时整个窗口让鼠标穿过去。
#[derive(Default)]
struct PetState {
    rects: Mutex<Vec<[f64; 4]>>,
    ignoring: AtomicBool,
    game_mode: AtomicBool,
    game_hidden: AtomicBool,
}

/// 用默认浏览器打开网站。url 是设置里填的（只接受 http/https），没填就打开知序。
#[tauri::command]
fn open_zhixu(app: AppHandle, url: Option<String>) -> Result<(), String> {
    let url = url
        .filter(|u| (u.starts_with("https://") || u.starts_with("http://")) && u.len() < 500)
        .unwrap_or_else(|| ZHIXU_URL.to_string());
    app.opener()
        .open_url(url, None::<&str>)
        .map_err(|e| e.to_string())
}

#[tauri::command]
fn set_hit_rects(state: tauri::State<PetState>, rects: Vec<[f64; 4]>) {
    if let Ok(mut r) = state.rects.lock() {
        *r = rects.into_iter().take(8).collect();
    }
}

#[tauri::command]
fn set_game_mode(app: AppHandle, state: tauri::State<PetState>, on: bool) {
    state.game_mode.store(on, Ordering::Relaxed);
    if !on && state.game_hidden.swap(false, Ordering::Relaxed) {
        show_pet(&app, false);
    }
}

#[tauri::command]
fn autostart_get(app: AppHandle) -> bool {
    app.autolaunch().is_enabled().unwrap_or(false)
}

#[tauri::command]
fn autostart_set(app: AppHandle, on: bool) -> Result<bool, String> {
    let a = app.autolaunch();
    if on { a.enable() } else { a.disable() }.map_err(|e| e.to_string())?;
    Ok(a.is_enabled().unwrap_or(false))
}

/// 打开设置窗口。必须是 async 命令：Windows 上在同步命令里建窗口会卡住，窗口一直白屏。
#[tauri::command]
async fn open_settings(app: AppHandle) -> Result<(), String> {
    show_settings(&app)
}

fn show_settings(app: &AppHandle) -> Result<(), String> {
    if let Some(w) = app.get_webview_window("settings") {
        let _ = w.unminimize();
        let _ = w.show();
        return w.set_focus().map_err(|e| e.to_string());
    }
    WebviewWindowBuilder::new(app, "settings", WebviewUrl::App("settings.html".into()))
        .title("希可的设置")
        .inner_size(380.0, 830.0)
        .resizable(false)
        .maximizable(false)
        .always_on_top(true)
        .center()
        .build()
        .map(|_| ())
        .map_err(|e| e.to_string())
}

// ---------- 自动更新 ----------
// 新版本发在本仓库的 Releases 里（见 tauri.conf.json 的 plugins.updater），
// 安装包有签名，公钥写在配置里，签名对不上就不装。

#[derive(Clone, serde::Serialize)]
struct UpdateInfo {
    version: String,
    current: String,
    notes: Option<String>,
}

async fn find_update(app: &AppHandle) -> Result<Option<tauri_plugin_updater::Update>, String> {
    app.updater()
        .map_err(|e| e.to_string())?
        .check()
        .await
        .map_err(|e| e.to_string())
}

fn info(u: &tauri_plugin_updater::Update) -> UpdateInfo {
    UpdateInfo {
        version: u.version.clone(),
        current: u.current_version.clone(),
        notes: u.body.clone(),
    }
}

/// 查一下有没有新版本（不下载）。
#[tauri::command]
async fn check_update(app: AppHandle) -> Result<Option<UpdateInfo>, String> {
    Ok(find_update(&app).await?.as_ref().map(info))
}

/// 下载、装好、重启。
#[tauri::command]
async fn install_update(app: AppHandle) -> Result<(), String> {
    let Some(u) = find_update(&app).await? else {
        return Err("已经是最新版了".into());
    };
    u.download_and_install(|_, _| {}, || {})
        .await
        .map_err(|e| e.to_string())?;
    app.restart();
}

/// 后台查更新，查到就告诉鲸鱼娘（她会问你要不要更新）。manual = 托盘里手动点的，查不到也说一声。
fn announce_update(app: AppHandle, manual: bool) {
    tauri::async_runtime::spawn(async move {
        match find_update(&app).await {
            Ok(Some(u)) => {
                show_pet(&app, false);
                let _ = app.emit_to("pet", "update-available", info(&u));
            }
            Ok(None) if manual => {
                show_pet(&app, false);
                let _ = app.emit_to("pet", "update-none", ());
            }
            Err(e) if manual => {
                show_pet(&app, false);
                let _ = app.emit_to("pet", "update-error", e);
            }
            _ => {}
        }
    });
}

/// 叫出鲸鱼娘。summoned = 用户主动叫的（托盘、再次打开），网页会说一句话。
fn show_pet(app: &AppHandle, summoned: bool) {
    if let Some(w) = app.get_webview_window("pet") {
        let _ = w.show();
        if summoned {
            let _ = w.set_focus();
            let _ = app.emit_to("pet", "summoned", ());
        }
    }
}

/// 最前面的窗口是不是盖满了整个屏幕（全屏游戏、全屏视频）。
#[cfg(windows)]
fn foreground_fullscreen(own: isize) -> bool {
    use windows::Win32::Foundation::RECT;
    use windows::Win32::Graphics::Gdi::{
        GetMonitorInfoW, MonitorFromWindow, MONITORINFO, MONITOR_DEFAULTTONEAREST,
    };
    use windows::Win32::UI::WindowsAndMessaging::{
        GetClassNameW, GetDesktopWindow, GetForegroundWindow, GetShellWindow, GetWindowRect,
    };
    unsafe {
        let fg = GetForegroundWindow();
        if fg.is_invalid() || fg.0 as isize == own || fg == GetShellWindow() || fg == GetDesktopWindow() {
            return false;
        }
        let mut cls = [0u16; 64];
        let n = GetClassNameW(fg, &mut cls).max(0) as usize;
        let class = String::from_utf16_lossy(&cls[..n]);
        if class == "WorkerW" || class == "Progman" || class == "Shell_TrayWnd" {
            return false; // 桌面和任务栏
        }
        let mut r = RECT::default();
        if GetWindowRect(fg, &mut r).is_err() {
            return false;
        }
        let mon = MonitorFromWindow(fg, MONITOR_DEFAULTTONEAREST);
        let mut mi = MONITORINFO {
            cbSize: std::mem::size_of::<MONITORINFO>() as u32,
            ..Default::default()
        };
        if !GetMonitorInfoW(mon, &mut mi).as_bool() {
            return false;
        }
        let m = mi.rcMonitor;
        r.left <= m.left && r.top <= m.top && r.right >= m.right && r.bottom >= m.bottom
    }
}
#[cfg(not(windows))]
fn foreground_fullscreen(_own: isize) -> bool {
    false
}

/// 后台小循环：每 60ms 看一次鼠标在不在鲸鱼娘身上，决定窗口要不要让鼠标穿过去；每秒看一次有没有全屏程序。
fn watch(app: AppHandle) {
    std::thread::spawn(move || {
        let mut tick: u32 = 0;
        loop {
            std::thread::sleep(Duration::from_millis(60));
            tick = tick.wrapping_add(1);
            let Some(w) = app.get_webview_window("pet") else { continue };
            let state = app.state::<PetState>();

            if tick % 16 == 0 && state.game_mode.load(Ordering::Relaxed) {
                #[cfg(windows)]
                let own = w.hwnd().map(|h| h.0 as isize).unwrap_or(0);
                #[cfg(not(windows))]
                let own = 0;
                let full = foreground_fullscreen(own);
                if full && w.is_visible().unwrap_or(false) {
                    state.game_hidden.store(true, Ordering::Relaxed);
                    let _ = w.hide();
                } else if !full && state.game_hidden.swap(false, Ordering::Relaxed) {
                    let _ = w.show();
                }
            }

            if !w.is_visible().unwrap_or(false) {
                continue;
            }
            let (Ok(c), Ok(p), Ok(scale)) = (w.cursor_position(), w.outer_position(), w.scale_factor()) else {
                continue;
            };
            let (x, y) = ((c.x - p.x as f64) / scale, (c.y - p.y as f64) / scale);
            let inside = state
                .rects
                .lock()
                .map(|r| r.iter().any(|[rx, ry, rw, rh]| x >= *rx && x <= rx + rw && y >= *ry && y <= ry + rh))
                .unwrap_or(true);
            // ignoring == inside 说明状态要翻转
            if state.ignoring.load(Ordering::Relaxed) == inside {
                if w.set_ignore_cursor_events(!inside).is_ok() {
                    state.ignoring.store(!inside, Ordering::Relaxed);
                }
            }
        }
    });
}

pub fn run() {
    tauri::Builder::default()
        // 已经开着时再打开一次：只把鲸鱼娘叫出来，不开第二只
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| show_pet(app, true)))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, None))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(PetState {
            game_mode: AtomicBool::new(true),
            ..Default::default()
        })
        .invoke_handler(tauri::generate_handler![
            open_zhixu,
            set_hit_rects,
            set_game_mode,
            check_update,
            install_update,
            autostart_get,
            autostart_set,
            open_settings
        ])
        .setup(|app| {
            let open = MenuItem::with_id(app, "open", "🌐 打开网站", true, None::<&str>)?;
            let show = MenuItem::with_id(app, "show", "🐋 叫出希可", true, None::<&str>)?;
            let hide = MenuItem::with_id(app, "hide", "🙈 藏起来", true, None::<&str>)?;
            let settings = MenuItem::with_id(app, "settings", "⚙️ 设置", true, None::<&str>)?;
            let update = MenuItem::with_id(app, "update", "🔄 检查更新", true, None::<&str>)?;
            let sep = PredefinedMenuItem::separator(app)?;
            let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &show, &hide, &settings, &update, &sep, &quit])?;
            TrayIconBuilder::with_id("whale")
                .icon(app.default_window_icon().cloned().expect("缺少图标"))
                .tooltip("希可（鲸鱼娘）")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    // 网站地址在网页的设置里，交给鲸鱼娘的窗口去开
                    "open" => {
                        let _ = app.emit_to("pet", "open-site", ());
                    }
                    "show" => show_pet(app, true),
                    "hide" => {
                        if let Some(w) = app.get_webview_window("pet") {
                            let _ = w.hide();
                        }
                    }
                    "settings" => {
                        let _ = show_settings(app);
                    }
                    "update" => announce_update(app.clone(), true),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_pet(tray.app_handle(), true);
                    }
                })
                .build(app)?;

            // 第一次打开放在主屏幕右下角；之后网页会把她挪回上次的位置
            if let Some(w) = app.get_webview_window("pet") {
                if let Ok(Some(m)) = w.primary_monitor() {
                    let scale = m.scale_factor();
                    let area = m.work_area();
                    let size = area.size.to_logical::<f64>(scale);
                    let pos = area.position.to_logical::<f64>(scale);
                    let win = w.outer_size()?.to_logical::<f64>(scale);
                    let _ = w.set_position(tauri::LogicalPosition::new(
                        pos.x + size.width - win.width - 16.0,
                        pos.y + size.height - win.height,
                    ));
                }
                let _ = w.show();
            }
            watch(app.handle().clone());
            // 启动 1 分钟后查一次更新，之后每 6 小时查一次
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                std::thread::sleep(Duration::from_secs(60));
                loop {
                    announce_update(handle.clone(), false);
                    std::thread::sleep(UPDATE_EVERY);
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("鲸鱼娘启动失败");
}
