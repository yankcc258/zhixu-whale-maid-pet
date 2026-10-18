// 发布版不弹出黑色命令行窗口
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    zhixu_whale_pet_lib::run()
}
