//! 鲸鱼娘桌宠：一个透明、无边框、永远在最上层的小窗口，外加右下角托盘图标。
//! 窗口里的动画和台词都在 src/（网页），这里只管窗口、托盘和「打开知序」。
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager,
};
use tauri_plugin_opener::OpenerExt;

const ZHIXU_URL: &str = "https://yank-study-lab.yank-study-lab.workers.dev";

/// 用默认浏览器打开知序。
#[tauri::command]
fn open_zhixu(app: AppHandle) -> Result<(), String> {
    app.opener()
        .open_url(ZHIXU_URL, None::<&str>)
        .map_err(|e| e.to_string())
}

fn show_pet(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("pet") {
        let _ = w.show();
        let _ = w.set_focus();
    }
}

pub fn run() {
    tauri::Builder::default()
        // 已经开着时再双击图标，只把鲸鱼娘叫出来，不开第二只
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| show_pet(app)))
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![open_zhixu])
        .setup(|app| {
            let open = MenuItem::with_id(app, "open", "🌐 打开知序", true, None::<&str>)?;
            let show = MenuItem::with_id(app, "show", "🐋 叫出鲸鱼娘", true, None::<&str>)?;
            let hide = MenuItem::with_id(app, "hide", "🙈 藏起来", true, None::<&str>)?;
            let sep = PredefinedMenuItem::separator(app)?;
            let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &show, &hide, &sep, &quit])?;
            TrayIconBuilder::with_id("whale")
                .icon(app.default_window_icon().cloned().expect("缺少图标"))
                .tooltip("鲸鱼娘")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => {
                        let _ = open_zhixu(app.clone());
                    }
                    "show" => show_pet(app),
                    "hide" => {
                        if let Some(w) = app.get_webview_window("pet") {
                            let _ = w.hide();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    // 左键单击托盘图标：叫出鲸鱼娘
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_pet(tray.app_handle());
                    }
                })
                .build(app)?;

            // 第一次打开放在屏幕右下角（主显示器，留出任务栏）
            if let Some(w) = app.get_webview_window("pet") {
                if let Ok(Some(m)) = w.primary_monitor() {
                    let scale = m.scale_factor();
                    let size = m.size().to_logical::<f64>(scale);
                    let pos = m.position().to_logical::<f64>(scale);
                    let win = w.outer_size()?.to_logical::<f64>(scale);
                    let _ = w.set_position(tauri::LogicalPosition::new(
                        pos.x + size.width - win.width - 24.0,
                        pos.y + size.height - win.height - 64.0,
                    ));
                }
                let _ = w.show();
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("鲸鱼娘启动失败");
}
