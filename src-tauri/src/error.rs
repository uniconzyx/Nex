use thiserror::Error;

/// Nex 统一错误类型。命令边界会转成 String 返回前端。
#[derive(Debug, Error)]
pub enum NexError {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("http error: {0}")]
    Http(#[from] reqwest::Error),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("sidecar error: {0}")]
    Sidecar(String),

    #[error("judge error: {0}")]
    Judge(String),

    /// 宿主墙钟看门狗触发（用户写了死循环 / sleep），已强杀沙箱
    #[error("wall-clock timeout: sandbox killed")]
    Watchdog,
}

pub type Result<T> = std::result::Result<T, NexError>;
