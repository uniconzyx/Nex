// Nex 原生桌面端入口（Tauri v2 + go-judge Sidecar）
//
// 应用主体在 src/lib.rs：Android 复用同一个 lib（cdylib + mobile_entry_point），
// 这里只保留桌面进程的薄壳入口。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    nex::run()
}
