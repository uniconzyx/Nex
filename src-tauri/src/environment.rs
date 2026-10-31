use serde::Serialize;
use std::process::Command;

use crate::config::detect_go_judge;

/// 单语言检测结果
#[derive(Debug, Clone, Serialize)]
pub struct LangStatus {
    pub name: String,
    pub available: bool,
    pub path: Option<String>,
    pub version: Option<String>,
}

/// 环境总览（前端引导用）
#[derive(Debug, Clone, Serialize)]
pub struct EnvReport {
    pub languages: Vec<LangStatus>,
    pub go_judge: bool,
    pub go_judge_path: Option<String>,
}

fn probe(name: &str, version_arg: &str) -> (bool, Option<String>, Option<String>) {
    match Command::new(name).arg(version_arg).output() {
        Ok(o) if o.status.success() => {
            let v = String::from_utf8_lossy(&o.stdout)
                .lines()
                .next()
                .map(|s| s.trim().to_string());
            let p = which_path(name);
            (true, p, v)
        }
        _ => (false, None, None),
    }
}

/// 简单 PATH 探测，返回可执行文件绝对路径（若有）。
/// judge_client 构造沙箱 env 时也用它（找工具目录补 PATH）。
pub(crate) fn which_path(name: &str) -> Option<String> {
    if let Ok(paths) = std::env::var("PATH") {
        let ext = if cfg!(windows) { "exe" } else { "" };
        for dir in std::env::split_paths(&paths) {
            let candidate = if ext.is_empty() {
                dir.join(name)
            } else {
                dir.join(name).with_extension(ext)
            };
            if candidate.exists() {
                return Some(candidate.to_string_lossy().into_owned());
            }
        }
    }
    None
}

/// 命令 `check_environment`：检测 gcc/g++/python/java/go-judge 是否可用，供前端优雅引导。
///
/// gcc 与 g++ 分开探测：判题台的语言下拉框有独立的 C 选项，
/// 只装 MinGW 的 g++ 时 gcc 通常也在，但用户完全可能只装其一——
/// 前端要能精确告诉用户「C 缺编译器」而不是笼统的「编译器缺失」。
pub fn check_environment() -> anyhow::Result<EnvReport> {
    let (ca, cp, cv) = probe("gcc", "--version");
    let (ga, gp, gv) = probe("g++", "--version");
    let (pa, pp, pv) = probe("python", "--version");
    let (ja, jp, jv) = probe("java", "-version");

    let languages = vec![
        LangStatus {
            name: "gcc".into(),
            available: ca,
            path: cp,
            version: cv,
        },
        LangStatus {
            name: "g++".into(),
            available: ga,
            path: gp,
            version: gv,
        },
        LangStatus {
            name: "python".into(),
            available: pa,
            path: pp,
            version: pv,
        },
        LangStatus {
            name: "java".into(),
            available: ja,
            path: jp,
            version: jv,
        },
    ];

    let gj = detect_go_judge();
    Ok(EnvReport {
        languages,
        go_judge: gj.is_some(),
        go_judge_path: gj.map(|p| p.to_string_lossy().into_owned()),
    })
}
