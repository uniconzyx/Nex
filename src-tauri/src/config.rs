use std::path::PathBuf;
use tauri::Manager;

/// 全局运行配置。全部从 App 资源/环境解析，便于在 setup 阶段一次性构造。
#[derive(Clone, Debug)]
pub struct AppConfig {
    /// go-judge 可执行文件绝对路径。None => 自动降级为本地直跑（mock）模式。
    pub go_judge_path: Option<PathBuf>,
    /// 宿主侧 WebSocket 取消服务端口
    pub ws_port: u16,
    /// 是否允许沙箱网络。默认 false（全局 --enable-network=false）。
    pub enable_network: bool,
    /// CPU 时间上限（纳秒），传给 go-judge cpuLimit
    pub cpu_limit_ns: u64,
    /// 内存上限（字节），传给 go-judge memoryLimit
    pub memory_limit_bytes: u64,
    /// 进程数上限，传给 go-judge procLimit
    pub proc_limit: u32,
    /// 宿主墙钟看门狗（秒）——防 sleep / 死循环的最后一道闸
    pub wall_timeout_secs: u64,
    /// 是否为降级模式（无 go-judge）
    pub mock_mode: bool,
}

impl AppConfig {
    /// 在 Tauri setup 阶段加载。优先从 resources/binaries/<name> 解析 go-judge。
    pub fn load(app: &impl Manager<tauri::Wry>) -> Self {
        let go_judge_path = resolve_go_judge(app);
        let mock_mode = go_judge_path.is_none();
        Self {
            go_judge_path,
            ws_port: 14520,
            enable_network: false, // 默认全局禁用网络（优先级 1.2）
            cpu_limit_ns: 2_000_000_000, // 2s CPU
            memory_limit_bytes: 256 * 1024 * 1024,
            proc_limit: 32,
            wall_timeout_secs: 5,
            mock_mode,
        }
    }
}

/// 解析 go-judge 二进制：resource_dir/binaries/go-judge(.exe)。
/// 找不到再退回 exe 同级探测（便携 zip：exe + binaries/go-judge.exe）。
/// 都没有才返回 None（降级为本地直跑），保证 `cargo build` 不依赖二进制存在。
fn resolve_go_judge(app: &impl Manager<tauri::Wry>) -> Option<PathBuf> {
    let name = if cfg!(target_os = "windows") {
        "go-judge.exe"
    } else {
        "go-judge"
    };
    if let Ok(base) = app.path().resource_dir() {
        let p = base.join("binaries").join(name);
        if p.exists() {
            return Some(p);
        }
    }
    detect_go_judge()
}

/// 不依赖 Manager 的探测（用于环境检测 / 运行时自查）。
/// 在 current_exe 同级的 binaries / resources/binaries 下查找 go-judge。
pub fn detect_go_judge() -> Option<PathBuf> {
    let name = if cfg!(target_os = "windows") {
        "go-judge.exe"
    } else {
        "go-judge"
    };
    let exe = std::env::current_exe().ok()?;
    let parent = exe.parent()?;
    [
        parent.join("binaries").join(name),
        parent.join("resources").join("binaries").join(name),
        parent.join(name),
    ]
    .into_iter()
    .find(|cand| cand.exists())
}
