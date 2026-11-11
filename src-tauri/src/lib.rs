// Nex 应用核心（Windows 桌面 + Android 共用）
//
// 结构说明（Tauri v2 移动端要求）：
//   - 应用真正的主体放在 lib（crate-type 含 cdylib），Android 的 Rust 侧
//     通过 JNI 调用 `#[mobile_entry_point] fn run()`。
//   - 桌面端的 main.rs 只是薄壳：`fn main() { nex::run() }`。
//   - 两边共用同一份 setup / 命令注册，保证 .exe 与 .apk 行为一致。
// 桌面端专用：开机自动拉起本机 FastAPI 后端（Android 瘦客户端不需要）
#[cfg(windows)]
pub mod backend_supervisor;
mod api_client;
// 暴露给 examples/ 做真机探测取证（不改动应用行为，仅重导出）。
pub use crate::api_client::{probe, ApiTarget};
mod config;
mod defender;
mod environment;
mod error;
mod judge_client;
mod lan_server;
mod payload;
mod sandbox;
mod ws_handler;

use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::Mutex;

use tauri::Manager;

use crate::config::AppConfig;
use crate::sandbox::JudgeManager;
use crate::ws_handler::start_ws_server;

/// 启动诊断日志：写到 exe 同级的 nex-boot.log（同时 stderr 一份）。
/// 用文件是为了在无桌面的会话里也能确证「窗口有没有真的开始加载」。
#[allow(dead_code)]
pub(crate) fn boot_log(msg: &str) {
    eprintln!("[boot] {msg}");
    let path = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.join("nex-boot.log")))
        .unwrap_or_else(|| std::path::PathBuf::from("nex-boot.log"));
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
    {
        use std::io::Write;
        let _ = writeln!(f, "{msg}");
        let _ = f.flush();
    }
}

// ---------------- Tauri 命令（前端 IPC） ----------------

#[tauri::command]
async fn judge(
    lang: String,
    code: String,
    stdin: Option<String>,
    manager: tauri::State<'_, Arc<Mutex<JudgeManager>>>,
) -> Result<judge_client::Verdict, String> {
    let mgr = manager.lock().await;
    Ok(mgr.judge(&lang, &code, stdin.as_deref()).await)
}

/// 批量判题：C++/Java 首用例编译并 copyOutCached 出 fileId，后续用例复用，避免重复编译。
/// 前端多测试用例场景务必走这个命令，而不是循环调用 `judge`（否则每用例都重新编译）。
///
/// 实现已抽离为 `lan_server::judge_batch_core`，与局域网 HTTP 路由
/// `POST /api/judge` 共用同一份逻辑，保证两条通道行为一致。
#[tauri::command]
async fn judge_batch(
    lang: String,
    code: String,
    stdins: Option<Vec<String>>,
    manager: tauri::State<'_, Arc<Mutex<JudgeManager>>>,
) -> Result<Vec<judge_client::Verdict>, String> {
    Ok(lan_server::judge_batch_core(manager.inner(), &lang, &code, stdins).await)
}

#[tauri::command]
async fn judge_ws_url(
    manager: tauri::State<'_, Arc<Mutex<JudgeManager>>>,
) -> Result<String, String> {
    let mgr = manager.lock().await;
    Ok(mgr.ws_url())
}

#[tauri::command]
async fn check_environment() -> Result<environment::EnvReport, String> {
    environment::check_environment().map_err(|e| e.to_string())
}

#[tauri::command]
async fn get_status(
    manager: tauri::State<'_, Arc<Mutex<JudgeManager>>>,
) -> Result<serde_json::Value, String> {
    let mgr = manager.lock().await;
    Ok(mgr.status_json())
}

/// 探测内容服务（FastAPI）在哪、是否可达。
/// 前端拿到后把 base_url 交给 api.ts 的 registerBaseResolver，
/// 于是前端的所有请求都打到客户端确认过的地址上。
///
/// 探测不通时**也会返回 base_url**（候选列表第一个），前端照样注册它 ——
/// 「不通就不注册」会让前端一直用自己那份兜底地址，而冷启动时那份地址
/// 从没被验证过，正是「连不上 http://127.0.0.1:8000」的老根因。
#[tauri::command]
async fn api_probe() -> Result<api_client::ApiTarget, String> {
    // 桌面端：等后台把本机后端拉起来再探。
    //
    // 等待上限给到 12s（原来 6s）：uvicorn 冷启动要加载题库 + 建索引，
    // 实测 3~10s，慢机器更久。只等 6s 会稳定地在「差一点就起来」的时候返回
    // reachable=false，前端于是把兜底地址钉死。
    // 等不到也只是多花这 12s（前端此时本来就是「连不上」状态，不更差）。
    #[cfg(windows)]
    backend_supervisor::wait_ready(std::time::Duration::from_secs(12)).await;
    let t = api_client::probe().await;
    // 落盘探测证据：候选地址 / 是否可达 / 后端版本 / 耗时。
    // 真客户端（浏览器里 isClient() 为 false）跑不到这条路径，
    // 之前 Phase17 只能靠 Rust 单测覆盖；写进启动日志才能在人工验收时
    // 确认「客户端确实自己探到了后端」，而不是碰巧用了默认地址。
    boot_log(&format!(
        "[api_probe] candidates={:?} base={} reachable={} version={:?} elapsed={}ms",
        t.candidates, t.base_url, t.reachable, t.backend_version, t.elapsed_ms
    ));
    Ok(t)
}

/// 前端告诉 Rust「这个地址可用」——移动端的关键补丁。
///
/// 手机上没有任何可用的默认后端地址：127.0.0.1 指向手机自己，
/// LAN IP 猜出来的也是手机自己。用户必须在设置页填一次电脑的地址
/// （如 `http://192.168.1.10:8000`）。前端把它存进 localStorage 之后
/// 再调这个命令，Rust 记在进程内，下次 api_probe 会把它排到候选首位，
/// 不会再拿一条死地址去耗超时。
///
/// 传空串 = 清除记忆（用户点「恢复默认地址」时）。
#[tauri::command]
fn nex_os_mark_base_ok(base: String) -> Result<(), String> {
    if base.trim().is_empty() {
        api_client::forget_base();
    } else {
        api_client::remember_base(&base);
    }
    boot_log(&format!("[api_base] marked ok: {base}"));
    Ok(())
}

/// 应用入口：桌面由 main.rs 调用，Android 由 `mobile_entry_point` 生成的 JNI 桥调用。
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // 桌面端：后台确保本机 FastAPI 后端可用（不阻塞窗口创建）。
            #[cfg(windows)]
            backend_supervisor::spawn_ensure();

            // 窗口就绪 + WebView 加载结果落盘。
            //
            // 为什么必须记：2026-11-11 出现过「窗口起来了、里面全黑」的情况，
            // 从外部完全看不出是 WebView 没加载、JS 崩了、还是 CSP 拦了资源。
            // 前端一旦渲染失败，它自己也没机会写日志（脚本根本没跑起来），
            // 所以这条证据只能由 Rust 侧在网络/加载层记下来。
            #[cfg(windows)]
            {
                use tauri::Manager;
                if let Some(win) = app.get_webview_window("main") {
                    boot_log(&format!(
                        "[window] created label=main visible={:?} size={:?} url={:?}",
                        win.is_visible().ok(),
                        win.inner_size().ok().map(|s| (s.width, s.height)),
                        win.url().ok().map(|u| u.to_string())
                    ));
                    // 兜底：某些会话里窗口以最小化状态创建（后台启动时容易命中），
                    // 用户会以为「程序没开」。这里保证第一次显示一定是正常尺寸。
                    let _ = win.unminimize();
                    let _ = win.show();
                    let _ = win.set_focus();

                } else {
                    boot_log("[window] WARN: 找不到 main 窗口");
                }
            }

            // 优先级 3：Defender 排除项（Windows 静默提权；真正无感在 NSIS 安装期）
            if let Err(e) = defender::ensure_exclusion(app.path().resource_dir().ok()) {
                eprintln!("[defender] 跳过排除项: {e}");
            }

            // 加载配置（自动解析 go-judge 路径，缺失则 mock 模式）
            let cfg = AppConfig::load(app);

            // 启动 JudgeManager（Sidecar + supervisor）
            let manager = Arc::new(Mutex::new(JudgeManager::new(cfg)));
            let mgr_start = manager.clone();
            // 用 drop 显式丢弃 JoinHandle：意图就是「分离（detach）后台任务」
            drop(tauri::async_runtime::spawn(async move {
                if let Err(e) = mgr_start.lock().await.start().await {
                    eprintln!("[judge] 启动失败(将进入 mock): {e}");
                }
            }));
            app.manage(manager.clone());

            // 优先级 1：局域网 HTTP 判题服务（Android 瘦客户端经同一 Wi-Fi 访问）
            //   POST /api/judge 与 invoke('judge-batch') 共用 judge_batch_core。
            //   首次监听 0.0.0.0 时 Windows 会弹防火墙提示，需允许「专用网络」。
            //   逃生开关：NEX_ALLOW_MOCK_LAN=1 可在无 go-judge 的降级模式下也放行
            //   局域网判题（无隔离，仅限可信内网做演示）。
            let mut lan_state = lan_server::LanState::new(manager.clone());
            let allow_mock = std::env::var("NEX_ALLOW_MOCK_LAN")
                .is_ok_and(|v| v == "1" || v.eq_ignore_ascii_case("true"));
            if allow_mock {
                lan_state = lan_state.allow_mock_over_lan(true);
                eprintln!("[lan] ⚠️ 已放行 mock 模式局域网判题（无沙箱隔离，仅限可信内网/演示用）");
            }
            drop(tauri::async_runtime::spawn(async move {
                let addr = SocketAddr::from(([0, 0, 0, 0], lan_server::DEFAULT_LAN_PORT));
                if let Err(e) = lan_server::start_lan_server_with(addr, lan_state).await {
                    eprintln!(
                        "[lan] 启动失败: {e}\n      （手机端将无法判题；常见原因：8080 被占用 / Windows 防火墙拦截）"
                    );
                }
            }));
            if let Some(ip) = lan_server::guess_lan_ip() {
                eprintln!(
                    "[lan] 局域网判题服务: http://{}:{}  （手机端在同一 Wi-Fi 下填写此地址）",
                    ip,
                    lan_server::DEFAULT_LAN_PORT
                );
            }

            // 优先级 2：WebSocket 取消服务（客户端掉线强杀沙箱）
            let ws_mgr = manager.clone();
            drop(tauri::async_runtime::spawn(async move {
                let addr: std::net::SocketAddr = "127.0.0.1:14520".parse().unwrap();
                if let Err(e) = start_ws_server(addr, ws_mgr).await {
                    eprintln!("[ws] 服务启动失败: {e}");
                }
            }));

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            judge,
            judge_batch,
            judge_ws_url,
            check_environment,
            get_status,
            api_probe,
            nex_os_mark_base_ok
        ])
        .build(tauri::generate_context!())
        .expect("error while building Nex")
        .run(|app_handle, event| {
            // App 退出：彻底清理 go-judge 进程树，防僵尸
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(mgr) = app_handle.try_state::<Arc<Mutex<JudgeManager>>>() {
                    let mgr = mgr.inner().clone();
                    tauri::async_runtime::spawn(async move {
                        let _ = mgr.lock().await.stop().await;
                    });
                }
            }
        });
}
