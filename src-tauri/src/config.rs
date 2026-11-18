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
    let found = [
        parent.join("binaries").join(name),
        parent.join("resources").join("binaries").join(name),
        parent.join(name),
    ]
    .into_iter()
    .find(|cand| cand.exists());

    // 单文件分发兜底：外部路径都没有时，把编译期嵌入的 go-judge 释放到临时目录。
    // #[cfg(windows)] 保证 Android 端不会把这 21MB 编进 libnex.so（APK 50MB 护栏）。
    #[cfg(windows)]
    if found.is_none() {
        return extract_embedded_go_judge();
    }
    found
}

// ===========================================================================
// 单文件分发：内嵌 go-judge（仅 Windows 桌面端）
// ---------------------------------------------------------------------------
// 目标：桌面端只带一个 Nex.exe，不再拖一个 21MB 的 binaries/go-judge.exe。
// 做法：编译期用 include_bytes! 把 go-judge 编进 .rodata；首次运行释放到
//       %TEMP%/nex-embedded-go-judge/，后续启动按字节长度校验复用（版本升级后
//       长度变化会自动重新释放，无需维护硬编码大小）。
// 失败策略：任何一步失败都返回 None，上层照常降级 mock，绝不影响应用启动。
// ===========================================================================

/// 编译期嵌入的 go-judge 字节。整个函数受 #[cfg(windows)] 保护——Android 编译时
/// 此函数被 cfg 剥离，include_bytes! 不会展开，APK 体积零影响。
#[cfg(windows)]
fn embedded_go_judge_bytes() -> &'static [u8] {
    // config.rs 位于 src-tauri/src/；CARGO_MANIFEST_DIR 即 src-tauri/。
    include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"), "/binaries/go-judge.exe"))
}

/// 释放内嵌 go-judge 到临时目录，返回可执行文件路径。
#[cfg(windows)]
fn extract_embedded_go_judge() -> Option<PathBuf> {
    let bytes = embedded_go_judge_bytes();
    if bytes.is_empty() {
        eprintln!("[judge] 内嵌 go-judge 为空，跳过");
        return None;
    }
    let expected = bytes.len() as u64;

    // 释放目录用公共 TEMP：单文件 exe 放桌面时不在旁边生成文件。
    // 目录名带长度后缀 -> go-judge 版本升级后自然隔离，旧文件不误用。
    let dir = std::env::temp_dir().join(format!("nex-judge-{}", expected));
    let target = dir.join("go-judge.exe");

    // 复用：存在且长度一致即认为可用（同一份 EXE 内的字节恒定，长度即指纹）。
    if let Ok(meta) = std::fs::metadata(&target) {
        if meta.len() == expected {
            return Some(target);
        }
    }

    // 原子落地：先写进程专属临时文件，再 rename 覆盖，避免多实例并发写坏。
    if std::fs::create_dir_all(&dir).is_err() {
        return None;
    }
    let staging = dir.join(format!("go-judge.{}.tmp", std::process::id()));
    if std::fs::write(&staging, bytes).is_err() {
        let _ = std::fs::remove_file(&staging);
        return None;
    }
    match std::fs::rename(&staging, &target) {
        Ok(_) => {
            eprintln!(
                "[judge] 已释放内嵌 go-judge ({} bytes) -> {}",
                expected,
                target.display()
            );
            Some(target)
        }
        Err(_) => {
            // rename 失败（罕见：目标被占用）时，若目标已可用就仍复用。
            let _ = std::fs::remove_file(&staging);
            if std::fs::metadata(&target)
                .map(|m| m.len() == expected)
                .unwrap_or(false)
            {
                Some(target)
            } else {
                None
            }
        }
    }
}
