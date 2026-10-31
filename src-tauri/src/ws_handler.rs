use std::sync::Arc;

use futures_util::{SinkExt, StreamExt};
use serde::Deserialize;
use tokio::net::TcpListener;
use tokio::sync::Mutex;
use tokio_tungstenite::accept_async;
use tokio_tungstenite::tungstenite::Message;

use crate::sandbox::JudgeManager;

#[derive(Debug, Deserialize)]
struct WsJudgeReq {
    lang: String,
    code: String,
    #[serde(default)]
    stdin: Option<String>,
}

/// 启动宿主侧 WebSocket 取消服务。
/// 前端连接 `ws://127.0.0.1:<port>/ws/run`，发送判题请求；一旦前端断开，立即强杀当前沙箱。
pub async fn start_ws_server(
    addr: std::net::SocketAddr,
    manager: Arc<Mutex<JudgeManager>>,
) -> anyhow::Result<()> {
    let listener = TcpListener::bind(addr).await?;
    eprintln!("[ws] 取消服务监听 ws://{addr}/ws/run");
    loop {
        let (stream, _) = listener.accept().await?;
        let mgr = manager.clone();
        tokio::spawn(async move {
            if let Err(e) = handle_conn(stream, mgr).await {
                eprintln!("[ws] 连接错误: {e}");
            }
        });
    }
}

/// 单连接处理：tokio::select! 监听「客户端消息」与「客户端断开」。
/// 客户端断开（reader.next() == None）即触发 kill_current，强杀正在运行的沙箱，防僵尸进程。
async fn handle_conn(
    stream: tokio::net::TcpStream,
    manager: Arc<Mutex<JudgeManager>>,
) -> anyhow::Result<()> {
    let ws = accept_async(stream).await?;
    let (mut writer, mut reader) = ws.split();

    loop {
        tokio::select! {
            // 分支 1：来自前端的消息
            msg = reader.next() => {
                match msg {
                    None => {
                        // 客户端断开（掉线 / 关闭页面）：立即强杀当前沙箱
                        let _ = manager.lock().await.kill_current().await;
                        eprintln!("[ws] 客户端断开 -> 已强杀当前沙箱");
                        break;
                    }
                    Some(Ok(Message::Text(t))) => {
                        // tungstenite 0.24: Message::Text 携带 Utf8Bytes，t.as_str() 取到 &str
                        let req: WsJudgeReq = match serde_json::from_str(t.as_str()) {
                            Ok(r) => r,
                            Err(e) => {
                                let _ = writer
                                    .send(Message::Text(format!("{{\"error\":\"{e}\"}}")))
                                    .await;
                                continue;
                            }
                        };
                        // 判题（内部含墙钟看门狗 + go-judge 强杀）
                        let verdict = {
                            let m = manager.lock().await;
                            m.judge(&req.lang, &req.code, req.stdin.as_deref()).await
                        };
                        let payload = serde_json::to_string(&verdict).unwrap_or_else(|_| "{}".to_string());
                        writer.send(Message::Text(payload)).await?;
                    }
                    Some(Ok(Message::Close(_))) => break,
                    Some(Ok(_)) => {}
                    Some(Err(e)) => return Err(e.into()),
                }
            }
        }
    }
    Ok(())
}
