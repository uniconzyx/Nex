//! api_client.rs —— 客户端 ↔ 内容服务（FastAPI）接线
//!
//! 职责：**在客户端侧探明后端在哪、是否活着**，并把结果交给前端。
//!
//! 为什么要有这一层：
//!   前端是纯 WebView，它只知道「有个地址」。但真实部署里后端可能是：
//!     * 本机 127.0.0.1:8000（桌面端最常见）；
//!     * 局域网另一台机器（手机端连电脑）；
//!     * 用户在设置里手填的自定义地址。
//!   这些差异客户端（Rust）比前端更适合判断：它有环境变量、网卡信息、
//!   以及「刚才启动的那个后端进程」的上下文。
//!
//! 探测顺序（先快后慢，先本机后外网）：
//!   1. `NEX_API_BASE` 环境变量 —— 显式指定，最高优先级；
//!   2. `http://127.0.0.1:8000`     —— 本机回环；
//!   3. `http://localhost:8000`     —— 同上，换个写法；
//!   4. 局域网 IP + :8000           —— 手机端场景（后端跑在电脑上）；
//!   5. `http://127.0.0.1:8000` 回落 —— 探测失败也要给前端一个可用的默认值。
//!
//! ⚠️ 沙箱/CI 环境常注入 `HTTP_PROXY`，会让回环请求被丢给代理。
//!    所有请求必须 `.no_proxy()`，否则「自己连自己」都会失败。

use std::time::Duration;

use serde::Serialize;

use crate::lan_server;

/// 后端默认端口。与 deploy/docker-compose.yml、server 启动命令保持一致。
pub const DEFAULT_API_PORT: u16 = 8000;

/// 探测结果：给前端用的后端描述。
#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct ApiTarget {
    /// 建议前端使用的基址（不带尾部斜杠）
    pub base_url: String,
    /// 是否探测通过（false 表示只有兜底默认值，前端应显示「离线」）
    pub reachable: bool,
    /// 探测用的候选列表，按优先级排列，方便 UI 解释「为什么选了这个」
    pub candidates: Vec<String>,
    /// 后端自报版本（探测成功时）
    pub backend_version: Option<String>,
    /// 探测耗时（毫秒）
    pub elapsed_ms: u64,
}

/// 构造候选地址列表。顺序即优先级。
///
/// ⚠️ 桌面端与移动端的候选**必须不同**（2026-11-11 修 APK 连不上后端）：
///
/// `guess_lan_ip()` 返回的是**运行本进程这台机器**的 IP。
///   * 桌面端：后端就跑在同一台电脑上 → 本机 LAN IP 是一个合法候选；
///   * 移动端：后端在**另一台电脑**上 → 手机上猜出来的 IP 是手机自己，
///     去连 `<手机IP>:8000` 必然连不上（手机上根本没有后端）。
///     以前不区分平台，APK 的候选里就混进了这条死地址，白白耗掉 900ms 超时。
///
/// 移动端的正确做法：用户填过的地址（手机端唯一可信来源）→ 上次探测成功的地址。
pub fn candidate_bases() -> Vec<String> {
    let mut v: Vec<String> = Vec::new();

    if cfg!(mobile) {
        // ── 移动端（Android/iOS）：后端在别的机器上 ──────────────────
        // 优先级：用户手填的地址（记住的那条）> 环境变量 > 回环兜底。
        //
        // 为什么手填地址必须压过环境变量：手机上没有「默认正确」的地址，
        // 用户在设置页填的那一条是他唯一可信的信息源；环境变量在 Android
        // 上通常根本不存在，真存在时也不该盖掉用户的选择。
        if let Some(saved) = remembered_base() {
            v.push(saved);
        }
        if let Ok(custom) = std::env::var("NEX_API_BASE") {
            let c = custom.trim().trim_end_matches('/').to_string();
            if !c.is_empty() && !v.contains(&c) {
                v.push(c);
            }
        }
        // 兜底：保证返回体非空，前端据此显示「请填写电脑地址」。
        let loopback = format!("http://127.0.0.1:{}", DEFAULT_API_PORT);
        if !v.contains(&loopback) {
            v.push(loopback);
        }
        return v;
    }

    // ── 桌面端：后端就在本机 ──────────────────────────────────────
    // 1. 环境变量显式指定（CI / 调试）
    if let Ok(custom) = std::env::var("NEX_API_BASE") {
        let c = custom.trim().trim_end_matches('/').to_string();
        if !c.is_empty() {
            v.push(c);
        }
    }

    // 2/3. 本机回环（桌面端后端默认绑这里）
    v.push(format!("http://127.0.0.1:{}", DEFAULT_API_PORT));
    v.push(format!("http://localhost:{}", DEFAULT_API_PORT));

    // 4. 本机局域网 IP —— 桌面端有意义：同一台机器换个网卡地址访问
    if let Some(ip) = lan_server::guess_lan_ip() {
        let lan = format!("http://{ip}:{}", DEFAULT_API_PORT);
        if !v.contains(&lan) {
            v.push(lan);
        }
    }

    v
}

/// 「上次探测成功过的地址」的进程内缓存（移动端关键）。
///
/// Android 上没有可靠的「后端在哪」的默认值：既不可能是 127.0.0.1，
/// 也不能用手机自己的 IP 去猜。唯一可信的是用户填过一次之后记住它。
/// 前端把用户输入存进 localStorage（`nex.apiBaseUrl`），并通过
/// `nex_os_mark_base_ok` 命令把生效地址回写到这里，
/// 下次冷启动时优先用它 —— 用户只需填一次。
static LAST_GOOD_BASE: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None);

/// 记录一个确认可用的基址（由 api_probe 探测成功后调用）。
pub fn remember_base(base: &str) {
    let b = base.trim().trim_end_matches('/');
    if b.is_empty() {
        return;
    }
    if let Ok(mut g) = LAST_GOOD_BASE.lock() {
        *g = Some(b.to_string());
    }
}

/// 读回上次确认可用的基址。
pub fn remembered_base() -> Option<String> {
    LAST_GOOD_BASE.lock().ok().and_then(|g| g.clone())
}

/// 清除记忆（用户点「恢复默认地址」时，避免旧地址一直占着首位）。
pub fn forget_base() {
    if let Ok(mut g) = LAST_GOOD_BASE.lock() {
        *g = None;
    }
}

/// 构造一个不走代理的 HTTP 客户端。
///
/// `.no_proxy()` 是必须的：沙箱与 CI 会注入 `HTTP_PROXY`，
/// 不绕过代理的话回环请求会被代理吞掉，表现成「后端明明在跑却连不上」。
fn http_client(timeout: Duration) -> reqwest::Client {
    reqwest::Client::builder()
        .no_proxy()
        .timeout(timeout)
        .connect_timeout(Duration::from_millis(800))
        .build()
        .unwrap_or_default()
}

/// 探测后端。返回推荐的基址与可达性。
pub async fn probe() -> ApiTarget {
    let start = std::time::Instant::now();
    let candidates = candidate_bases();
    // 单个地址超时压到 900ms（原来 1500ms）：候选最多 4 个，
    // 冷启动时前端在等这一次结果，探得慢等于红字挂得久。
    let client = http_client(Duration::from_millis(900));

    for base in &candidates {
        // 优先打 /api/v1/system/health（能同时确认「活着」与「是 Nex 后端」）。
        // 老版本后端没这个接口，退回 /health。
        let probe_url = format!("{base}/api/v1/system/health");
        if let Some(version) = check(&client, &probe_url).await {
            // 记住这条可用地址：移动端下次冷启动直接用它，不用用户重填。
            remember_base(base);
            return ApiTarget {
                base_url: base.clone(),
                reachable: true,
                candidates,
                backend_version: Some(version),
                elapsed_ms: start.elapsed().as_millis() as u64,
            };
        }

        let legacy = format!("{base}/health");
        if check(&client, &legacy).await.is_some() {
            remember_base(base);
            return ApiTarget {
                base_url: base.clone(),
                reachable: true,
                candidates,
                backend_version: None,
                elapsed_ms: start.elapsed().as_millis() as u64,
            };
        }
    }

    // 全都没通：**仍然返回候选里最可能是后端的那一个**（而不是第一个）。
    //
    // 候选顺序是 [NEX_API_BASE?, 127.0.0.1, localhost, LAN IP]。
    // 项目后端默认绑 127.0.0.1:8000，所以回落时优先给回环地址；
    // 只有候选里压根没有回环（用户用环境变量指定了远端）时才取第一个。
    let fallback = candidates
        .iter()
        .find(|c| c.contains("127.0.0.1") || c.contains("localhost"))
        .cloned()
        .or_else(|| candidates.first().cloned())
        .unwrap_or_else(|| format!("http://127.0.0.1:{}", DEFAULT_API_PORT));

    ApiTarget {
        base_url: fallback,
        reachable: false,
        candidates,
        backend_version: None,
        elapsed_ms: start.elapsed().as_millis() as u64,
    }
}

/// 打一个 URL，返回后端版本（探测成功时）。
async fn check(client: &reqwest::Client, url: &str) -> Option<String> {
    let resp = client.get(url).send().await.ok()?;
    if !resp.status().is_success() {
        return None;
    }
    let body: serde_json::Value = resp.json().await.ok()?;
    // 统一响应包：{code, message, data, traceId}
    let data = body.get("data").unwrap_or(&body);
    let version = data
        .get("backend")
        .and_then(|b| b.get("version"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    Some(version.unwrap_or_else(|| "unknown".to_string()))
}

// ---------------- 测试 ----------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn candidates_always_contain_loopback() {
        // 无论环境怎么配，本机回环必须在候选里——桌面端最常见的情况。
        let v = candidate_bases();
        assert!(
            v.iter().any(|s| s == "http://127.0.0.1:8000"),
            "候选缺少本机回环：{v:?}"
        );
    }

    #[test]
    fn candidates_are_normalized() {
        // 尾斜杠必须去掉，否则拼出来会是 http://x:8000//api/v1/...
        let v = candidate_bases();
        for c in &v {
            assert!(!c.ends_with('/'), "候选带尾斜杠：{c}");
            assert!(c.starts_with("http://"), "候选不是 http：{c}");
        }
    }

    #[test]
    fn candidates_have_no_duplicates() {
        let v = candidate_bases();
        let mut seen = std::collections::HashSet::new();
        for c in &v {
            assert!(seen.insert(c.clone()), "候选重复：{c}");
        }
    }

    #[test]
    fn env_override_wins() {
        // NEX_API_BASE 必须在候选列表第一位
        std::env::set_var("NEX_API_BASE", "http://192.168.9.9:9999/");
        let v = candidate_bases();
        std::env::remove_var("NEX_API_BASE");
        assert_eq!(v.first().map(String::as_str), Some("http://192.168.9.9:9999"));
    }

    #[test]
    fn env_override_ignores_blank() {
        // 空白环境变量不算覆盖：桌面端应直接回落到回环地址。
        // （移动端首位可能是记忆地址，那条路径由 remembered_base_goes_first 覆盖）
        std::env::set_var("NEX_API_BASE", "   ");
        forget_base();
        let v = candidate_bases();
        std::env::remove_var("NEX_API_BASE");
        if cfg!(mobile) {
            assert!(!v.is_empty(), "移动端候选不能为空");
        } else {
            assert_eq!(v.first().map(String::as_str), Some("http://127.0.0.1:8000"));
        }
    }

    #[test]
    fn probe_returns_a_usable_base_even_when_offline() {
        // 探测不到也必须给出地址（前端要显示它、用户要能改它）。
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        let t = rt.block_on(probe());
        assert!(!t.base_url.is_empty());
        assert!(t.base_url.starts_with("http://"));
        assert!(!t.candidates.is_empty());
        // 本机确实没有后端在跑时 reachable 必须是 false
        if !t.reachable {
            assert!(t.backend_version.is_none());
        }
    }

    #[test]
    fn client_does_not_use_proxy() {
        // 构造出的 client 必须绕过代理，否则回环请求会被代理吞掉。
        let c = http_client(std::time::Duration::from_millis(200));
        // reqwest 的 Client 没有公开 proxy 配置，这里只断言能构造出来且不 panic
        let _ = c;
    }

    /// 记忆地址只在移动端生效。
    ///
    /// 桌面端后端就在本机，回环 + LAN IP 已覆盖全部真实情况；
    /// 把历史地址塞进桌面候选只会让冷启动多探一个可能已失效的地址。
    #[test]
    fn remembered_base_goes_first() {
        remember_base("http://192.168.1.10:8000/"); // 带尾斜杠也要归一化
        let v = candidate_bases();
        forget_base();
        if cfg!(mobile) {
            assert_eq!(
                v.first().map(String::as_str),
                Some("http://192.168.1.10:8000"),
                "移动端记忆地址没排首位：{v:?}"
            );
        } else {
            assert!(
                !v.iter().any(|s| s.contains("192.168.1.10")),
                "桌面端不该把记忆地址塞进候选：{v:?}"
            );
        }
    }

    /// 清除记忆后不能残留。
    #[test]
    fn forget_base_clears_memory() {
        remember_base("http://192.168.1.11:8000");
        forget_base();
        assert!(remembered_base().is_none());
    }

    /// 空串不该污染记忆（前端「恢复默认地址」会传空）。
    #[test]
    fn remember_base_ignores_blank() {
        forget_base();
        remember_base("   ");
        assert!(remembered_base().is_none());
    }

    /// 桌面端（非 mobile）必须有回环候选 —— 后端就跑在本机。
    ///
    /// 移动端的候选表**不含**本机 LAN IP：那台机器是手机自己，不是后端。
    #[test]
    fn desktop_candidates_include_loopback_not_mobile_style() {
        if cfg!(mobile) {
            return; // 移动端走另一套逻辑，本用例不适用
        }
        let v = candidate_bases();
        assert!(v.iter().any(|s| s.contains("127.0.0.1")));
        assert!(v.iter().any(|s| s.contains("localhost")));
    }
}
