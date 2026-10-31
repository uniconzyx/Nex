//! 真机探测取证（Windows 本地直接运行，不依赖 Tauri 窗口上下文）。
//!
//! 这个 example 跑的就是真客户端里 `invoke('api_probe')` 时 Rust 侧执行的那段
//! `api_client::probe()` 逻辑：枚举候选地址 → 逐地址做 reachable HTTP 探测 →
//! 读取后端版本与耗时。浏览器验收（isClient=false）走不到这条路径，
//! Phase17 只能靠 Rust 单测覆盖；本 example 用于在真机上取「客户端确实探到后端」
//! 的证据，等价于把 api_probe 命令逻辑跑一遍。
//!
//! 运行：cargo run --example probe_smoke
use nex::probe;

#[tokio::main]
async fn main() {
    eprintln!("[probe_smoke] 开始真机探测（等价于客户端 invoke('api_probe')）…");
    let t = probe().await;
    println!("candidates = {:?}", t.candidates);
    println!("base_url   = {}", t.base_url);
    println!("reachable  = {}", t.reachable);
    println!("version    = {:?}", t.backend_version);
    println!("elapsed_ms = {}", t.elapsed_ms);
    // reachable=true 视为取证成功（退出码 0），否则 2。
    std::process::exit(if t.reachable { 0 } else { 2 });
}
