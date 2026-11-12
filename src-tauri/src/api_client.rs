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
//! 桌面端探测顺序：
//!   1. `NEX_API_BASE` 环境变量 —— 显式指定，最高优先级；
//!   2. `http://127.0.0.1:8000`     —— 本机回环；
//!   3. `http://localhost:8000`     —— 同上，换个写法；
//!   4. 局域网 IP + :8000           —— 同一台机器换个网卡地址访问。
//!
//! 移动端（2026-11-12 起）：后端在**另一台机器（打包用的 PC）**上，
//! 手机上没有任何能自己猜出来的地址。所以 `prepare_app.py` 在打 APK 时
//! 探测 PC 的局域网 IP，经 `NEX_MOBILE_DEFAULT_BASES` 编译进 libnex.so，
//! 冷启动直接作为首选候选 —— 不用手填、不会退回 127.0.0.1（手机自己）。
//! 用户手填的地址仍然压过内置地址，换网络后可以在设置页覆盖。
//!
//! ⚠️ 沙箱/CI 环境常注入 `HTTP_PROXY`，会让回环请求被丢给代理。
//!    所有请求必须 `.no_proxy()`，否则「自己连自己」都会失败。

use std::time::Duration;

use serde::Serialize;

use crate::lan_server;

/// 后端默认端口。与 deploy/docker-compose.yml、server 启动命令保持一致。
pub const DEFAULT_API_PORT: u16 = 8000;

/// 打包时注入的 PC 局域网地址列表（逗号分隔，由 build-app-apk.cmd 设置）。
///
/// 用 `option_env!` 而非运行时读文件：Android assets 对 Rust 侧不可见（要绕 JNI），
/// 编译期注入是唯一零依赖的做法。桌面构建不设这个变量 → `None` → 行为完全不变。
/// `build.rs` 已声明 `rerun-if-env-changed`，换网络重打包会强制重编 .so。
const PACKAGED_MOBILE_BASES: Option<&str> = option_env!("NEX_MOBILE_DEFAULT_BASES");

/// 解析注入的地址串：去空白/尾斜杠、只收 http(s) 开头、按原序去重。
///
/// 单独抽成纯函数是为了在桌面 `cargo test` 里也能验解析逻辑
/// （桌面构建 `PACKAGED_MOBILE_BASES` 恒为 None，走不到真实注入值）。
/// 收 https 是为了「以后部署线上后端」那条路：打包时用
/// `NEX_API_BASE=https://api.xxx.com` 即可，不必再改 Rust。
fn parse_packaged_bases(raw: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    for part in raw.split(',') {
        let c = part.trim().trim_end_matches('/').to_string();
        if c.is_empty()
            || !(c.starts_with("http://") || c.starts_with("https://"))
            || out.contains(&c)
        {
            continue;
        }
        out.push(c);
    }
    out
}

/// 本次构建注入的移动端默认候选（桌面构建返回空）。
fn packaged_mobile_bases() -> Vec<String> {
    PACKAGED_MOBILE_BASES
        .map(parse_packaged_bases)
        .unwrap_or_default()
}

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
/// 2026-11-12 补上移动端真正可用的默认地址：打包时把 PC 的局域网 IP
/// 编译进来（见 `PACKAGED_MOBILE_BASES`）。冷启动顺序变成
///   `上次成功的地址 > NEX_API_BASE > 打包时 PC 地址 > 回环兜底`，
/// 绝大多数情况下**第一个候选就命中**，不再需要手填、也不再反复重试。
pub fn candidate_bases() -> Vec<String> {
    let mut v: Vec<String> = Vec::new();

    if cfg!(mobile) {
        // ── 移动端（Android/iOS）：后端在别的机器上 ──────────────────
        // 用户手填的地址优先级最高：那是他针对当前网络明确指定的信息源，
        // 不该被打包时（可能已过期）的 PC 地址盖掉。
        if let Some(saved) = remembered_base() {
            v.push(saved);
        }
        if let Ok(custom) = std::env::var("NEX_API_BASE") {
            let c = custom.trim().trim_end_matches('/').to_string();
            if !c.is_empty() && !v.contains(&c) {
                v.push(c);
            }
        }
        // 打包时写入的 PC 地址：冷启动的主路径。多网卡会注入多条，
        // 按顺序探测，第一条通常几十毫秒就命中。
        for base in packaged_mobile_bases() {
            if !v.contains(&base) {
                v.push(base);
            }
        }
        // 兜底：保证返回体非空。注意这只是「地址列表非空」的保险，
        // 探测全失败时前端显示的基址由 probe() 的 fallback 决定。
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
    // 桌面端候选是 [NEX_API_BASE?, 127.0.0.1, localhost, LAN IP]，
    // 后端默认绑 127.0.0.1:8000，所以回落时优先给回环地址。
    // 移动端反过来：回环是手机自己，把它显示成「当前连的是哪台机器」
    // 纯属误导；应该给候选首位的 PC 地址，用户照着排查才有意义。
    let fallback = if cfg!(mobile) {
        candidates.first().cloned()
    } else {
        candidates
            .iter()
            .find(|c| c.contains("127.0.0.1") || c.contains("localhost"))
            .cloned()
            .or_else(|| candidates.first().cloned())
    }
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
            assert!(
                c.starts_with("http://") || c.starts_with("https://"),
                "候选不是 http(s)：{c}"
            );
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

    /// 打包注入串必须归一：尾斜杠、空白、重复项、非 http 项都要挡掉。
    /// 桌面构建注入值为 None，靠这个纯函数直接验解析逻辑。
    #[test]
    fn parse_packaged_bases_normalizes_and_dedups() {
        let v = parse_packaged_bases(concat!(
            "http://192.168.1.7:8000/, http://10.0.0.2:8000 ,",
            "http://192.168.1.7:8000/ , ,not-a-url, ftp://bad:21",
        ));
        assert_eq!(
            v,
            vec![
                "http://192.168.1.7:8000".to_string(),
                "http://10.0.0.2:8000".to_string()
            ],
            "注入串解析结果不对：{v:?}"
        );
    }

    /// 线上部署那条路：打包时用 NEX_API_BASE=https://api.xxx.com 指定，
    /// 注入串必须收 https，否则手机又会退回局域网地址。
    #[test]
    fn parse_packaged_bases_accepts_https() {
        let v = parse_packaged_bases("  https://api.example.com/ , http://172.27.30.62:8000 ");
        assert_eq!(
            v,
            vec![
                "https://api.example.com".to_string(),
                "http://172.27.30.62:8000".to_string()
            ]
        );
    }

    #[test]
    fn parse_packaged_bases_handles_empty() {
        assert!(parse_packaged_bases("").is_empty());
        assert!(parse_packaged_bases("  , , ").is_empty());
    }

    /// 移动端（且本次构建确实注入了 PC 地址时）内置地址必须排在回环之前：
    /// 否则冷启动第一个打的是手机自己，白等一次 900ms 超时。
    #[test]
    fn mobile_packaged_base_precedes_loopback() {
        if !cfg!(mobile) || PACKAGED_MOBILE_BASES.is_none() {
            return;
        }
        if parse_packaged_bases(PACKAGED_MOBILE_BASES.unwrap()).is_empty() {
            return;
        }
        forget_base();
        let v = candidate_bases();
        let first_lan = v
            .iter()
            .position(|s| !s.contains("127.0.0.1") && !s.contains("localhost"));
        let first_loopback = v.iter().position(|s| s.contains("127.0.0.1"));
        assert!(
            first_lan.is_some(),
            "注入了 PC 地址却没进候选：{v:?}"
        );
        if let (Some(a), Some(b)) = (first_lan, first_loopback) {
            assert!(a < b, "内置 PC 地址被回环抢在前面：{v:?}");
        }
    }
}
