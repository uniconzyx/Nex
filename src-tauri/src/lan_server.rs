//! 局域网 HTTP 判题服务（Axum）
//! ============================================================================
//! 背景：Android APK 是「瘦客户端」——移动端不跑 go-judge 沙箱，而是通过同一
//! Wi-Fi 请求 Windows 桌面端判题。桌面端在 Tauri invoke 之外再开一个 HTTP 服务。
//!
//! 与 Tauri invoke 的关系（关键设计）：
//!   * `judge_batch_core()` 是**唯一**的批量判题实现。
//!     Tauri 命令 `judge-batch` 与 HTTP 路由 `POST /api/judge` 共用它，
//!     保证两条通道语义完全一致（含空 stdins 的兜底行为）。
//!   * invoke 只服务本机 WebView；HTTP 服务监听 `0.0.0.0` 供局域网设备访问。
//!
//! 路由：
//!   GET  /api/ping        连通性探测（手机端填完 IP 后先 ping 一下）
//!   POST /api/judge       批量判题，返回与入参等长同序的 Verdict[]
//!   GET  /api/environment 环境探测（bonus：手机端据此弹引导）
//!
//! 安全边界（务必读懂）：
//!   本服务执行**任意提交的代码**。go-judge 沙箱在位时由 JobObject/RLIMIT 兜底；
//!   一旦降级为 mock 模式（本地直跑、无任何隔离），把 8080 暴露在局域网等于
//!   把宿主任意代码执行能力送给同网段任何设备。因此默认 mock 模式下拒绝
//!   `/api/judge`（503），只保留 `/api/ping` 让客户端能给出准确提示。
//!   该开关按 Router 实例持有（`LanState::allow_mock_over_lan`），
//!   不做进程级全局变量——否则并发测试之间会互相干扰。
//! ============================================================================

use std::net::{SocketAddr, UdpSocket};
use std::sync::Arc;

use axum::extract::rejection::JsonRejection;
use axum::extract::State;
use axum::http::{header, Method, StatusCode};
use axum::response::{Html, IntoResponse, Response};
use axum::routing::{get, post};
use axum::Json;
use serde::Deserialize;
use serde_json::json;
use tokio::sync::Mutex;
use tower_http::cors::{Any, CorsLayer};

use crate::environment;
use crate::judge_client::Verdict;
use crate::sandbox::JudgeManager;

/// 局域网服务默认端口。`GET /api/ping` 供手机端测试连通性。
pub const DEFAULT_LAN_PORT: u16 = 8080;

/// mock 模式（无 go-judge、本地直跑无隔离）下是否仍受理局域网判题的**默认值**。
/// 默认 `false`：降级路径没有资源/网络隔离，不对局域网开放。
/// 仅当你在完全可信的内网自娱自乐时才考虑打开。
pub const ALLOW_MOCK_OVER_LAN: bool = false;

/// 判题服务共享状态。与 Tauri `app.manage()` 注册的是**同一个** `Arc`，
/// 因此 HTTP 通道与 invoke 通道看到的是同一份 go-judge 生命周期状态。
pub type SharedManager = Arc<Mutex<JudgeManager>>;

// ---------------- 公共判题逻辑：Tauri 命令与 HTTP 路由共用 ----------------

/// 批量判题核心实现（抽离自原 `main.rs` 的 `judge-batch` 命令体）。
///
/// C++/Java 首用例编译并 `copyOutCached` 出 fileId，后续用例复用，只编译一次。
///
/// * `stdins` 为空数组 / `None` 时，按「一条空 stdin 的用例」处理，
///   避免前端漏传时静默返回空结果。
/// * 返回值与入参 `stdins` 等长同序（`judge_batch` 内部保证）。
pub async fn judge_batch_core(
    manager: &SharedManager,
    lang: &str,
    code: &str,
    stdins: Option<Vec<String>>,
) -> Vec<Verdict> {
    let mgr = manager.lock().await;
    let owned: Vec<String> = stdins
        .filter(|v| !v.is_empty())
        .unwrap_or_else(|| vec![String::new()]);
    let borrowed: Vec<Option<&str>> = owned.iter().map(|s| Some(s.as_str())).collect();
    mgr.judge_batch(lang, code, borrowed).await
}

// ---------------- HTTP DTO ----------------

/// `POST /api/judge` 请求体。
/// `rename_all = "camelCase"` 与 `payload.rs` 的线格式习惯保持一致
/// （当前三个字段都是单词，大小写无差异；加属性是为将来加 `copyOutCached` 之类的
///  多词字段时不破坏契约）。
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JudgeHttpReq {
    pub lang: String,
    pub code: String,
    #[serde(default)]
    pub stdins: Option<Vec<String>>,
}

/// `GET /api/ping` 响应。手机端据此判断「填的 IP 通不通、沙箱在不在」。
#[derive(Debug, serde::Serialize)]
pub struct PingResp {
    pub ok: bool,
    pub service: &'static str,
    pub version: &'static str,
    /// go-judge 沙箱是否就绪（false = 降级本地直跑）
    pub go_judge: bool,
    /// 当前是否受理判题（mock 模式 + 未显式放行时为 false）
    pub accepting: bool,
}

// ---------------- Router 状态 ----------------

/// 路由状态。**每个 Router 实例一份**，不用进程级全局开关，
/// 这样测试可以各自构造「放行 / 不放行」的服务而互不影响。
#[derive(Clone)]
pub struct LanState {
    manager: SharedManager,
    allow_mock_over_lan: bool,
}

impl LanState {
    /// 用默认策略（`ALLOW_MOCK_OVER_LAN`）构造。
    pub fn new(manager: SharedManager) -> Self {
        Self {
            manager,
            allow_mock_over_lan: ALLOW_MOCK_OVER_LAN,
        }
    }

    /// 覆盖 mock 模式下的受理策略（设置页 / 测试用）。
    pub fn allow_mock_over_lan(mut self, v: bool) -> Self {
        self.allow_mock_over_lan = v;
        self
    }
}

// ---------------- 处理器 ----------------

/// `GET /api/ping` —— 连通性 + 沙箱状态探测，永不判题，零副作用。
async fn ping(State(st): State<LanState>) -> Json<PingResp> {
    // 守卫是本语句临时量，语句结束即释放，不会和后续加锁形成死锁
    let status = st.manager.lock().await.status_json();
    let go_judge = status
        .get("go_judge_available")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    Json(PingResp {
        ok: true,
        service: "nex-judge",
        version: env!("CARGO_PKG_VERSION"),
        go_judge,
        accepting: go_judge || st.allow_mock_over_lan,
    })
}

/// `POST /api/judge` —— 批量判题。
///
/// 返回体是**裸的 `Verdict[]`**（与 invoke('judge-batch') 完全一致的 JSON），
/// 前端 `GoJudgeClient` 可以共用同一套解析与 UI 映射代码。
async fn judge_http(
    State(st): State<LanState>,
    body: Result<Json<JudgeHttpReq>, JsonRejection>,
) -> Response {
    let Json(req) = match body {
        Ok(j) => j,
        Err(rej) => return bad_request_json(&format!("请求体不是合法 JSON: {rej}")),
    };

    let status = st.manager.lock().await.status_json();
    let sandboxed = status
        .get("go_judge_available")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if !sandboxed && !st.allow_mock_over_lan {
        return (
            StatusCode::SERVICE_UNAVAILABLE,
            Json(json!({
                "error": "电脑端未启用 go-judge 沙箱（降级模式），已拒绝局域网判题",
                "hint": "请在电脑端安装 go-judge：把 go-judge.exe 放到 resources/binaries/ 后重启 Nex"
            })),
        )
            .into_response();
    }

    let verdicts = judge_batch_core(&st.manager, &req.lang, &req.code, req.stdins).await;
    Json(verdicts).into_response()
}

/// `GET /` —— 手机浏览器测试页。
///
/// 为什么需要它：普通浏览器只能发 GET，没法 POST JSON。
/// 没有这个页面，手机打开 `http://<电脑IP>:8080` 只能 ping，无法真正判题。
/// 页面零依赖（无 CDN、无外链），fetch 打同源的 `/api/judge`。
async fn index_page() -> Html<&'static str> {
    Html(LAN_TEST_PAGE)
}

/// 手机测试页 HTML（内嵌，避免再多一个静态资源目录）。
///
/// 约定：与 `Verdict` 的 serde 线格式（`#[serde(tag="verdict",
/// rename_all="snake_case")]`）对齐——`{"verdict":"accepted","stdout":...}`。
const LAN_TEST_PAGE: &str = r#"<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Nex 判题测试</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 16px;
         background: #F8FAFC; color: #0F172A; }
  h1 { font-size: 18px; margin: 0 0 4px; }
  .sub { font-size: 12px; color: #64748B; margin-bottom: 12px; }
  #status { font-size: 13px; padding: 8px 12px; border-radius: 8px; margin-bottom: 12px;
            background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8; }
  #status.warn { background: #FFFBEB; border-color: #FDE68A; color: #B45309; }
  label { display: block; font-size: 13px; color: #475569; margin: 10px 0 4px; }
  select, textarea, button { width: 100%; font-size: 14px; padding: 10px; border-radius: 8px;
            border: 1px solid #CBD5E1; background: #fff; font-family: inherit; }
  textarea { min-height: 110px; font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
  button { margin-top: 12px; background: #3B82F6; color: #fff; border: none; font-weight: 600;
           padding: 14px; cursor: pointer; }
  button:disabled { background: #93C5FD; }
  .v { border: 1px solid #E2E8F0; border-radius: 8px; background: #fff; padding: 10px 12px;
       margin-top: 10px; font-size: 13px; }
  .badge { display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 12px;
           font-weight: 600; margin-right: 8px; }
  .ok  { background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
  .bad { background: #FEE2E2; color: #B91C1C; border: 1px solid #FECACA; }
  .meta { color: #64748B; font-size: 12px; }
  pre { background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px;
        font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }
</style>
</head>
<body>
<h1>Nex 判题测试页</h1>
<div class="sub">同一 Wi-Fi 下用手机打开即测；判题在电脑端执行</div>
<div id="status">状态获取中…</div>

<label for="lang">语言</label>
<select id="lang">
  <option value="python">Python</option>
  <option value="cpp">C++</option>
  <option value="java">Java</option>
</select>

<label for="code">代码</label>
<textarea id="code" spellcheck="false">print("Hello Nex")</textarea>

<label for="stdins">stdin（每行一条用例；留空 = 1 条空输入）</label>
<textarea id="stdins" spellcheck="false"></textarea>

<button id="run">提交判题</button>
<div id="out"></div>

<script>
var $ = function (id) { return document.getElementById(id); };
var LABELS = {
  accepted: 'Accepted', compile_error: 'CompileError', runtime_error: 'RuntimeError',
  time_limit_exceeded: 'TLE', memory_limit_exceeded: 'MLE',
  output_limit_exceeded: 'OLE', illegal_syscall: 'IllegalSyscall',
  wall_timeout: 'WallTimeout', mock: 'Mock'
};
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
  });
}
function refresh() {
  fetch('/api/ping').then(function (r) { return r.json(); }).then(function (j) {
    var el = $('status');
    var mode = j.go_judge ? '沙箱就绪（go-judge）' : '降级模式（本地直跑，无隔离）';
    var acc = j.accepting ? '受理判题' : '拒绝判题（电脑端未放行 mock）';
    el.textContent = mode + ' · ' + acc;
    el.className = j.accepting ? '' : 'warn';
  }).catch(function () { $('status').textContent = '连接失败：检查电脑 IP / 防火墙'; });
}
$('run').onclick = function () {
  var btn = $('run');
  btn.disabled = true; btn.textContent = '判题中…'; $('out').innerHTML = '';
  var raw = $('stdins').value.replace(/\r/g, '');
  var stdins = raw.trim() === '' ? [''] : raw.split('\n');
  fetch('/api/judge', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ lang: $('lang').value, code: $('code').value, stdins: stdins })
  }).then(function (r) {
    return r.text().then(function (t) { return { ok: r.ok, text: t }; });
  }).then(function (res) {
    var data;
    try { data = JSON.parse(res.text); } catch (e) { data = null; }
    var html = '';
    if (!data) {
      html = '<div class="v"><span class="badge bad">HTTP 错误</span><pre>' + esc(res.text) + '</pre></div>';
    } else if (!Array.isArray(data)) {
      html = '<div class="v"><span class="badge bad">错误</span><pre>' + esc(JSON.stringify(data, null, 2)) + '</pre></div>';
    } else {
      for (var i = 0; i < data.length; i++) {
        var v = data[i];
        var pass = v.verdict === 'accepted';
        html += '<div class="v"><span class="badge ' + (pass ? 'ok' : 'bad') + '">' +
                esc(LABELS[v.verdict] || v.verdict) + '</span>' +
                '<span class="meta">#' + (i + 1) + '</span>';
        if (pass) {
          html += ' <span class="meta">' + v.time_ms + ' ms · ' + v.memory_kb + ' KB</span>' +
                  '<pre>' + esc(v.stdout) + '</pre>';
        } else if (v.stderr) {
          html += '<pre>' + esc(v.stderr) + '</pre>';
        }
        html += '</div>';
      }
    }
    $('out').innerHTML = html;
  }).catch(function (e) {
    $('out').innerHTML = '<div class="v"><span class="badge bad">请求失败</span><pre>' + esc(e) + '</pre></div>';
  }).finally(function () {
    btn.disabled = false; btn.textContent = '提交判题';
  });
};
refresh();
</script>
</body>
</html>
"#;

/// `GET /api/environment` —— 环境探测（bonus，镜像 invoke 的 check-environment）。
async fn env_http(State(_st): State<LanState>) -> Response {
    match environment::check_environment() {
        Ok(rep) => Json(rep).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "error": e.to_string() })),
        )
            .into_response(),
    }
}

/// JSON 解析失败 → 400 + 可读提示（手机端调试时比 axum 默认的纯文本友好得多）。
fn bad_request_json(msg: &str) -> Response {
    (
        StatusCode::BAD_REQUEST,
        Json(json!({
            "error": msg,
            "hint": "期望: {\"lang\":\"python\",\"code\":\"print(1)\",\"stdins\":[\"\"]}"
        })),
    )
        .into_response()
}

// ---------------- 组装 ----------------

/// 构建路由（策略由 `state` 指定）。
///
/// 生产入口统一走 {@link start_lan_server_with}；测试直接调这里，
/// 可以给每个用例配不同的 mock 放行策略而互不干扰。
pub fn build_router_with(state: LanState) -> axum::Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST, Method::OPTIONS])
        .allow_headers([header::CONTENT_TYPE, header::AUTHORIZATION, header::ACCEPT]);

    axum::Router::new()
        .route("/", get(index_page))
        .route("/api/ping", get(ping))
        .route("/api/judge", post(judge_http))
        .route("/api/environment", get(env_http))
        .layer(cors)
        .with_state(state)
}

/// 启动局域网服务（阻塞到服务结束），策略由调用方通过 `LanState` 指定。
///
/// CORS 放开 `Any`：手机端 WebView 的 origin 是 `http(s)://tauri.localhost`
/// （随 Tauri 版本变化），固定白名单容易漏；如需收紧，把 `Any` 换成具体 origin。
pub async fn start_lan_server_with(addr: SocketAddr, state: LanState) -> anyhow::Result<()> {
    let listener = tokio::net::TcpListener::bind(addr).await?;
    let app = build_router_with(state);
    axum::serve(listener, app).await?;
    Ok(())
}

/// 猜测本机局域网 IPv4（用于启动日志，方便手机端填写）。
///
/// 技巧：向一个公网 IP `connect` 一个 UDP socket。UDP connect 只做路由决策、
/// **不发包**，因此离线也能算出「系统会选哪张网卡出口」，比枚举网卡可靠。
pub fn guess_lan_ip() -> Option<std::net::IpAddr> {
    let sock = UdpSocket::bind("0.0.0.0:0").ok()?;
    sock.connect("8.8.8.8:80").ok()?;
    Some(sock.local_addr().ok()?.ip())
}

// ---------------- 测试：真实 HTTP 请求走一遍 ----------------

#[cfg(test)]
mod tests {
    use super::*;

    /// 起一个监听 127.0.0.1 随机端口的测试服务，返回 base URL。
    async fn spawn_test_server(state: LanState) -> String {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            axum::serve(listener, build_router_with(state)).await.unwrap();
        });
        format!("http://{addr}")
    }

    /// HTTP 客户端。
    ///
    /// ⚠️ 必须 `no_proxy()`：CI / 沙箱环境常注入 `HTTP_PROXY`，
    /// 不关掉的话请求 127.0.0.1 会被丢给代理，连不上自己刚起的服务。
    fn http() -> reqwest::Client {
        reqwest::Client::builder().no_proxy().build().unwrap()
    }

    fn mock_manager() -> SharedManager {
        Arc::new(Mutex::new(JudgeManager::new(crate::sandbox::mock_config(20))))
    }

    /// python 是否可用（mock 路径依赖它）
    async fn python_ok() -> bool {
        tokio::process::Command::new("python")
            .arg("-c")
            .arg("print('ok')")
            .output()
            .await
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    /// ping 必须永远可用（mock 模式也不例外），并如实报告沙箱状态。
    #[tokio::test]
    async fn ping_reports_mock_mode_as_not_accepting() {
        let base = spawn_test_server(LanState::new(mock_manager())).await;
        let resp = http().get(format!("{base}/api/ping")).send().await.unwrap();

        assert!(resp.status().is_success(), "ping 应永远可用");
        let body: serde_json::Value = resp.json().await.unwrap();
        assert_eq!(body["ok"], serde_json::json!(true));
        assert_eq!(body["service"], serde_json::json!("nex-judge"));
        // mock 配置 -> 无 go-judge -> 不接受判题
        assert_eq!(body["go_judge"], serde_json::json!(false));
        assert_eq!(body["accepting"], serde_json::json!(false));
    }

    /// 默认策略下，mock 模式拒绝判题（503 + 可读 JSON，不是裸 500）。
    #[tokio::test]
    async fn judge_rejected_in_mock_mode_returns_503() {
        let base = spawn_test_server(LanState::new(mock_manager())).await;
        let resp = http()
            .post(format!("{base}/api/judge"))
            .json(&serde_json::json!({
                "lang": "python",
                "code": "print(1)",
                "stdins": [""],
            }))
            .send()
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::SERVICE_UNAVAILABLE);
        let body: serde_json::Value = resp.json().await.unwrap();
        assert!(
            body["error"].as_str().unwrap_or("").contains("go-judge"),
            "错误信息应说明缺 go-judge，实际: {body}"
        );
        assert!(body["hint"].is_string(), "应带安装提示");
    }

    /// 请求体不是合法 JSON -> 400（而不是 500 或静默 200）。
    /// 这条同时验证了 DTO 字段名：能走到 503/200 才说明 lang/code/stdins 解析成功。
    #[tokio::test]
    async fn judge_rejects_malformed_json_with_400() {
        let base = spawn_test_server(LanState::new(mock_manager())).await;
        let resp = http()
            .post(format!("{base}/api/judge"))
            .header("content-type", "application/json")
            .body("这不是 JSON")
            .send()
            .await
            .unwrap();

        assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    }

    /// 放行 mock 后，局域网 HTTP 的结果必须与 `judge_batch_core` 完全一致
    /// —— 证明两条通道真的是同一份逻辑，而不是各写一遍。
    #[tokio::test]
    async fn judge_over_lan_matches_core_when_allowed() {
        if !python_ok().await {
            eprintln!("[skip] python 不可用");
            return;
        }
        let mgr = mock_manager();
        let base = spawn_test_server(LanState::new(mgr.clone()).allow_mock_over_lan(true)).await;

        let resp = http()
            .post(format!("{base}/api/judge"))
            .json(&serde_json::json!({
                "lang": "python",
                "code": "print(6*7)",
                "stdins": ["", ""],
            }))
            .send()
            .await
            .unwrap();

        assert!(resp.status().is_success(), "放行后应正常判题");
        let via_http: Vec<Verdict> = resp.json().await.unwrap();
        let via_core = judge_batch_core(&mgr, "python", "print(6*7)", Some(vec![String::new(), String::new()])).await;

        assert_eq!(via_http.len(), 2);
        assert_eq!(
            serde_json::to_value(&via_http).unwrap(),
            serde_json::to_value(&via_core).unwrap(),
            "HTTP 通道与 core 的返回必须逐字节一致"
        );
    }

    /// `stdins: []` 与 invoke 命令一致：兜底成「一条空 stdin 的用例」。
    #[tokio::test]
    async fn judge_empty_stdins_falls_back_to_single_case() {
        if !python_ok().await {
            eprintln!("[skip] python 不可用");
            return;
        }
        let base = spawn_test_server(LanState::new(mock_manager()).allow_mock_over_lan(true)).await;
        let resp = http()
            .post(format!("{base}/api/judge"))
            .json(&serde_json::json!({ "lang": "python", "code": "print(6*7)", "stdins": [] }))
            .send()
            .await
            .unwrap();

        let verdicts: Vec<Verdict> = resp.json().await.unwrap();
        assert_eq!(verdicts.len(), 1, "空 stdins 应兜底为 1 条用例");
        // 注意：本地直跑（mock）路径成功时返回的是 Accepted，而不是 Verdict::Mock
        // （Mock 变体只在拿不到结果时兜底）。别在这里写错判据。
        match &verdicts[0] {
            Verdict::Accepted { stdout, .. } => assert_eq!(stdout.trim(), "42"),
            other => panic!("本地直跑应 Accepted，实际: {other:?}"),
        }
    }

    /// CORS：手机端 WebView 的 origin 是 `http://tauri.localhost`，
    /// 预检（OPTIONS）与普通请求都必须放行，否则 fetch 会被浏览器策略拦掉。
    #[tokio::test]
    async fn cors_allows_mobile_webview_origin() {
        let base = spawn_test_server(LanState::new(mock_manager())).await;
        let client = http();

        // 预检
        let pre = client
            .request(reqwest::Method::OPTIONS, format!("{base}/api/judge"))
            .header("origin", "http://tauri.localhost")
            .header("access-control-request-method", "POST")
            .send()
            .await
            .unwrap();
        assert!(pre.status().is_success(), "预检应被放行");
        assert_eq!(
            pre.headers()
                .get("access-control-allow-origin")
                .and_then(|v| v.to_str().ok()),
            Some("*"),
            "预检应返回 access-control-allow-origin"
        );

        // 普通 GET 也带 CORS 响应头
        let get = client
            .get(format!("{base}/api/ping"))
            .header("origin", "http://tauri.localhost")
            .send()
            .await
            .unwrap();
        assert_eq!(
            get.headers()
                .get("access-control-allow-origin")
                .and_then(|v| v.to_str().ok()),
            Some("*"),
        );
    }

    /// `/api/environment` 镜像 invoke 的 check-environment，移动端用于引导弹窗。
    #[tokio::test]
    async fn environment_endpoint_returns_report() {
        let base = spawn_test_server(LanState::new(mock_manager())).await;
        let resp = http()
            .get(format!("{base}/api/environment"))
            .send()
            .await
            .unwrap();

        assert!(resp.status().is_success());
        let body: serde_json::Value = resp.json().await.unwrap();
        // EnvReport 的关键字段（Rust 侧 snake_case，未做 rename）
        assert!(body.get("languages").is_some(), "应含 languages: {body}");
        assert!(body.get("go_judge").is_some(), "应含 go_judge: {body}");
    }
}
