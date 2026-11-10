//! 后端自拉冒烟（不启动 GUI 窗口，直接真机验证 backend_supervisor）。
//!
//! 用法（先把 :8000 上已有的后端停掉，否则会走「already running」分支）：
//!   NEX_BACKEND_CONFIG=<EXE 同目录>/nex-backend.json backend_smoke.exe
//!
//! 通过判据：ensure() 确认就绪 + /health 真的返回 200，退出码 0；否则 2。
use nex::backend_supervisor;

#[tokio::main]
async fn main() {
    eprintln!("[backend_smoke] 开始：检查 /health，不通则按配置拉起 uvicorn…");
    backend_supervisor::ensure().await;
    let ready = backend_supervisor::is_ready();

    let client = reqwest::Client::builder().no_proxy().build().unwrap();
    let ok = client
        .get("http://127.0.0.1:8000/health")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    println!("BACKEND_READY = {ready}");
    println!("HEALTH_200    = {ok}");
    std::process::exit(if ready && ok { 0 } else { 2 });
}
