use std::collections::HashMap;

use crate::config::AppConfig;
use crate::error::{NexError, Result};
use crate::payload::{CmdResult, CmdSpec, CopyIn, FileSpec, RunRequest, RunResponse, RunResponseWire, Status};

/// 判题结果（前端可识别的判定）。
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(tag = "verdict", rename_all = "snake_case")]
pub enum Verdict {
    Accepted {
        stdout: String,
        time_ms: u64,
        memory_kb: u64,
    },
    CompileError {
        stderr: String,
    },
    RuntimeError {
        stderr: String,
        signal: Option<String>,
    },
    TimeLimitExceeded,
    MemoryLimitExceeded,
    OutputLimitExceeded,
    IllegalSyscall {
        msg: String,
    },
    /// 宿主墙钟看门狗触发（go-judge 的 cpu_limit 防不住 sleep/死循环）
    WallTimeout,
    /// 降级模式：无 go-judge 时本地直跑的回显结果
    Mock {
        stdout: String,
    },
}

/// stdout / stderr 收集上限（16MB / 4MB）：给足学习场景输出，又防恶意刷爆内存。
const STDOUT_MAX: u64 = 16 * 1024 * 1024;
const STDERR_MAX: u64 = 4 * 1024 * 1024;

/// 编译阶段资源上限（**刻意比运行阶段宽**）：
/// - MinGW g++ 编译 `<bits/stdc++.h>` 峰值内存可超 300MB，javac 冷启动也慢；
/// - 编译进程由宿主持墙钟看门狗（`wall_timeout_secs`）兜底，放宽不会失控；
/// - 曾经用运行级 256MB 编译，重头文件程序被 job object **静默杀掉**，
///   表现为 compile_error 且 stderr 为空，极难排查。
const COMPILE_CPU_NS: u64 = 10_000_000_000; // 10s CPU
const COMPILE_MEM: u64 = 1024 * 1024 * 1024; // 1GB

/// 输出占位文件（让 go-judge 捕获该流）。
/// v1.13.3 起 `name` + `max` **必须同时给**：只给 name 会落入
/// `convertCmdFile` 的 default 分支，直接 400 "file type is not valid for cmd"。
fn out(name: &str, max: u64) -> FileSpec {
    FileSpec::Out {
        name: name.to_string(),
        max,
    }
}

/// 输入文件（作为命令 stdin）。v1.13.3 的 content 是**原文**（上游零拷贝不解码）。
fn in_stdin(stdin: &str) -> FileSpec {
    FileSpec::In {
        content: Some(stdin.to_string()),
        name: Some("stdin".to_string()),
        file_id: None,
        max: None,
    }
}

/// 构造 go-judge 的 `files` 数组（按位置映射 fd）：
/// index0=stdin（占位或真实输入），index1=stdout，index2=stderr。
fn stdfiles(stdin: Option<&str>) -> Vec<FileSpec> {
    let stdin_slot = match stdin {
        Some(s) => in_stdin(s),
        None => in_stdin(""), // 空 stdin：输入文件（content 为空），go-judge 映射为 fd0
    };
    vec![
        stdin_slot,
        out("stdout", STDOUT_MAX),
        out("stderr", STDERR_MAX),
    ]
}

/// 把工具名解析成宿主机绝对路径（找不到则原样返回裸名）。
///
/// **为什么必须绝对路径**：winc 用 `CreateProcessAsUser` + 受限令牌创建进程，
/// 实测裸命令名（`python`）即使在 env PATH 里也报
/// "The system cannot find the file specified"（CreateProcess 的可执行文件
/// 搜索用的是**调用方**进程的 PATH，不受我们传进去的 env PATH 影响）。
/// 传绝对路径可一举绕开该语义，Linux 容器侧同样成立。
fn resolve_tool(name: &str) -> String {
    crate::environment::which_path(name).unwrap_or_else(|| name.to_string())
}

/// 构造沙箱内命令的环境变量。
///
/// **为什么必须显式传**：go-judge 的执行体都不继承宿主机环境——Windows winc
/// 只额外透传 TMP/TEMP/LocalAppData（见 `env/winc` 的 Execve），Linux 容器
/// 同样只拿 `Cmd.Env`。裸命令名 `python` / `g++` 全靠 PATH 解析，
/// 不传 env 的直接后果是「找不到程序」。
fn build_env(tools: &[&str]) -> Vec<String> {
    // 1) 宿主机 PATH 原样注入（用户自己装的 python/g++/java 通常已在里面）
    let mut entries: Vec<String> = std::env::var_os("PATH")
        .map(|p| {
            std::env::split_paths(&p)
                .map(|x| x.to_string_lossy().into_owned())
                .collect()
        })
        .unwrap_or_default();
    // 2) 工具目录兜底：即使不在宿主机 PATH 里，也把 which 到的目录补进去
    for t in tools {
        if let Some(full) = crate::environment::which_path(t) {
            if let Some(dir) = std::path::Path::new(&full).parent() {
                let d = dir.to_string_lossy().into_owned();
                if !d.is_empty() && !entries.iter().any(|e| e.eq_ignore_ascii_case(&d)) {
                    entries.push(d);
                }
            }
        }
    }
    let joined = std::env::join_paths(entries.iter().map(std::path::PathBuf::from))
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_default();
    #[allow(unused_mut)]
    let mut env = vec![format!("PATH={joined}")];
    // 3) Windows 系统变量：很多运行时（Python 自身、JVM）启动时就要读
    #[cfg(windows)]
    for k in [
        "SYSTEMROOT",
        "WINDIR",
        "SYSTEMDRIVE",
        "COMSPEC",
        "PROCESSOR_ARCHITECTURE",
        "NUMBER_OF_PROCESSORS",
    ] {
        if let Ok(v) = std::env::var(k) {
            env.push(format!("{k}={v}"));
        }
    }
    env
}

/// 构造 `POST /run` 请求体（go-judge v1.13.3 线格式）。
///
/// 与旧版的**关键差异**（发错位置不报错、只会被静默忽略）：
/// * `copyIn` / `copyOutCached` / 各 limit 全部在 **Cmd 级**——请求顶层字段
///   已被上游移除，发顶层等于没发（源码进不了沙箱、编译缓存永不命中）；
/// * 墙钟上限字段是 `clockLimit`（没有 `timeLimit`）；
/// * `env` 必须显式给（winc/容器不继承宿主机环境，见 {@link build_env}）。
///
/// `cached_file_id`：Some 时表示复用已编译产物（C++/Java 多测试用例），仅放一个 run cmd。
pub fn build_request(
    lang: &str,
    code: &str,
    stdin: Option<&str>,
    cfg: &AppConfig,
    cached_file_id: Option<&str>,
) -> Result<RunRequest> {
    let cpu = cfg.cpu_limit_ns;
    let mem = cfg.memory_limit_bytes;
    let proc = cfg.proc_limit;
    // 墙钟上限（纳秒）——**刻意比宿主看门狗大 1s**，原因见下：
    // 1. go-judge 的 waiter 在 `clockLimit` 为 0 时会**回退拿 CPU 限制当墙钟
    //    限制**（worker/waiter.go：`if clockTimeLimit == 0 { clockTimeLimit = timeLimit }`），
    //    导致 sleep(30) 这类零 CPU 程序在 CPU 限制时刻被误杀（实测 2.01s 准时死）。
    // 2. 显式给「看门狗 + 1s」后分工干净：CPU 死循环由 job object 在 cpuLimit
    //    处触发 END_OF_JOB_TIME → 干净的 TimeLimitExceeded；墙钟卡死由宿主
    //    看门狗先杀（WallTimeout + kill_tree + supervisor 重启 go-judge），
    //    go-judge 的 clockLimit 只当二级保险，永不被抢先。
    // 3. winc 上 waiter 触发的墙钟击杀只能观察到 `Nonzero Exit Status`
    //    （run_single.go 的事后 CPU 检查管不到墙钟），所以更不能让 go-judge
    //    的墙钟限制抢在看门狗前面出手。
    let clock = (cfg.wall_timeout_secs + 1) * 1_000_000_000;

    match lang {
        "python" | "py" => {
            let mut copyin = HashMap::new();
            copyin.insert(
                "sol.py".to_string(),
                CopyIn {
                    content: Some(code.to_string()),
                    ..Default::default()
                },
            );
            let mut env = build_env(&["python"]);
            // Windows 上 Python 默认按本地代码页写管道，强制 UTF-8 防中文输出乱码
            env.push("PYTHONIOENCODING=utf-8".into());
            env.push("PYTHONUTF8=1".into());
            Ok(RunRequest {
                cmd: vec![CmdSpec {
                    args: vec![resolve_tool("python"), "-u".into(), "sol.py".into()],
                    env: Some(env),
                    files: Some(stdfiles(stdin)),
                    cpu_limit: Some(cpu),
                    clock_limit: Some(clock),
                    memory_limit: Some(384 * 1024 * 1024), // Python/numpy 给足内存
                    proc_limit: Some(proc),
                    copy_in: Some(copyin),
                    ..Default::default()
                }],
            })
        }
        "c" => {
            // 纯 C：必须用 gcc + .c 后缀。
            //
            // ⚠️ 为什么不能和 cpp 合并成 g++：
            //   * `int *p = malloc(sizeof(int));` 在 C 里合法，g++ 会报
            //     "invalid conversion from 'void*' to 'int*'"——学生写的是对的，
            //     却看到编译错误；
            //   * C99 变长数组 `int a[n]` 在 g++ 里直接不合法；
            //   * `void f()` 在 C 里是「参数未指定」，在 C++ 里是「无参」，
            //     语义不同会导致链接期或运行期行为差异。
            //   gcc 会按 `.c` 后缀自动选 C 标准，无需额外 -std。
            if let Some(fid) = cached_file_id {
                let mut copyin = HashMap::new();
                copyin.insert(
                    "a.exe".to_string(),
                    CopyIn {
                        file_id: Some(fid.to_string()),
                        ..Default::default()
                    },
                );
                Ok(RunRequest {
                    cmd: vec![CmdSpec {
                        args: vec!["a.exe".into()],
                        env: Some(build_env(&[])),
                        files: Some(stdfiles(stdin)),
                        cpu_limit: Some(cpu),
                        clock_limit: Some(clock),
                        memory_limit: Some(mem),
                        proc_limit: Some(proc),
                        copy_in: Some(copyin),
                        ..Default::default()
                    }],
                })
            } else {
                let mut copyin = HashMap::new();
                copyin.insert(
                    "main.c".to_string(),
                    CopyIn {
                        content: Some(code.to_string()),
                        ..Default::default()
                    },
                );
                Ok(RunRequest {
                    cmd: vec![CmdSpec {
                        args: vec![
                            resolve_tool("gcc"),
                            "-O2".into(),
                            "main.c".into(),
                            "-o".into(),
                            "a.exe".into(),
                        ],
                        env: Some(build_env(&["gcc"])),
                        files: Some(stdfiles(None)),
                        cpu_limit: Some(COMPILE_CPU_NS),
                        clock_limit: Some(clock),
                        memory_limit: Some(COMPILE_MEM),
                        proc_limit: Some(proc),
                        copy_in: Some(copyin),
                        copy_out_cached: Some(vec!["a.exe".to_string()]),
                        ..Default::default()
                    }],
                })
            }
        }
        "cpp" | "c++" => {
            if let Some(fid) = cached_file_id {
                // 复用编译产物：单 run cmd（copyIn 走 fileId）
                let mut copyin = HashMap::new();
                copyin.insert(
                    "a.exe".to_string(),
                    CopyIn {
                        file_id: Some(fid.to_string()),
                        ..Default::default()
                    },
                );
                Ok(RunRequest {
                    cmd: vec![CmdSpec {
                        args: vec!["a.exe".into()],
                        env: Some(build_env(&[])),
                        files: Some(stdfiles(stdin)),
                        cpu_limit: Some(cpu),
                        clock_limit: Some(clock),
                        memory_limit: Some(mem),
                        proc_limit: Some(proc),
                        copy_in: Some(copyin),
                        ..Default::default()
                    }],
                })
            } else {
                // 只发编译 cmd：`copyOutCached` 把 a.exe 存进 go-judge 全局
                // filestore 并回传 fileId，运行侧再用 `copyIn(fileId)` 拉回来。
                //
                // **为什么不能把 [编译, 运行] 放进同一请求**（曾经的坑）：
                // v1.13.3 的 worker.go `workDoGroup` 对 group 内**每个 cmd
                // 都单独 `envPool.Get()` 一个 Environment**（源码 282-296 行），
                // 每个 Environment 有独立的 root/tmp。同一请求里 cmd[1] 的
                // 沙箱里**没有** cmd[0] 编译出的 a.exe —— 实测 run cmd 直接
                // `Internal Error: The system cannot find the file specified.`。
                // go-judge 编译型语言的正确 pattern 就是「编译、运行两次请求」，
                // 多 cmd 单请求只用于 pipe 管道，不共享文件系统。
                let mut copyin = HashMap::new();
                copyin.insert(
                    "main.cpp".to_string(),
                    CopyIn {
                        content: Some(code.to_string()),
                        ..Default::default()
                    },
                );
                // 编译阶段放宽资源：MinGW g++ 编译 <bits/stdc++.h> 峰值可超
                // 300MB，256MB 会被 job object 静默杀掉（表现为 compile_error
                // 且 stderr 为空，极具误导性）。编译由宿主持墙钟看门狗兜底。
                Ok(RunRequest {
                    cmd: vec![CmdSpec {
                        args: vec![
                            resolve_tool("g++"),
                            "-O2".into(),
                            "main.cpp".into(),
                            "-o".into(),
                            "a.exe".into(),
                        ],
                        env: Some(build_env(&["g++"])),
                        files: Some(stdfiles(None)),
                        cpu_limit: Some(COMPILE_CPU_NS),
                        clock_limit: Some(clock),
                        memory_limit: Some(COMPILE_MEM),
                        proc_limit: Some(proc),
                        copy_in: Some(copyin),
                        copy_out_cached: Some(vec!["a.exe".to_string()]),
                        ..Default::default()
                    }],
                })
            }
        }
        "java" => {
            if let Some(fid) = cached_file_id {
                let mut copyin = HashMap::new();
                copyin.insert(
                    "Main.class".to_string(),
                    CopyIn {
                        file_id: Some(fid.to_string()),
                        ..Default::default()
                    },
                );
                Ok(RunRequest {
                    cmd: vec![CmdSpec {
                        args: vec![resolve_tool("java"), "Main".into()],
                        env: Some(build_env(&["java"])),
                        files: Some(stdfiles(stdin)),
                        cpu_limit: Some(cpu),
                        clock_limit: Some(clock),
                        memory_limit: Some(512 * 1024 * 1024), // JVM 需显式内存
                        proc_limit: Some(proc),
                        copy_in: Some(copyin),
                        ..Default::default()
                    }],
                })
            } else {
                // 同 C++：只发编译 cmd，fileId 由 copyOutCached 回传，
                // 运行侧 copyIn(fileId)（同请求多 cmd 不共享 fs，见 cpp 分支注释）。
                let mut copyin = HashMap::new();
                copyin.insert(
                    "Main.java".to_string(),
                    CopyIn {
                        content: Some(code.to_string()),
                        ..Default::default()
                    },
                );
                Ok(RunRequest {
                    cmd: vec![CmdSpec {
                        args: vec![resolve_tool("javac"), "Main.java".into()],
                        env: Some(build_env(&["javac"])),
                        files: Some(stdfiles(None)),
                        cpu_limit: Some(COMPILE_CPU_NS),
                        clock_limit: Some(clock),
                        memory_limit: Some(COMPILE_MEM),
                        proc_limit: Some(proc),
                        copy_in: Some(copyin),
                        copy_out_cached: Some(vec!["Main.class".to_string()]),
                        ..Default::default()
                    }],
                })
            }
        }
        other => Err(NexError::Judge(format!("unsupported language: {other}"))),
    }
}

/// 取 go-judge 回传的文件内容。
/// v1.13.3 起 `files` 的值是**原文**（上游 `byteArrayToString` 零拷贝，无 base64）。
fn decode_file(r: &CmdResult, name: &str) -> String {
    match &r.files {
        Some(m) => m.get(name).cloned().unwrap_or_default(),
        None => String::new(),
    }
}

/// 将 go-judge 的单条 cmd 结果映射为运行期 Verdict。
/// 编译型语言的「编译」是独立请求（见 {@link build_request}），
/// 用 {@link map_compile_result}；本函数只映射「运行用户程序」的结果。
fn map_results(results: &[CmdResult]) -> Verdict {
    if results.is_empty() {
        return Verdict::RuntimeError {
            stderr: "empty judge response".into(),
            signal: None,
        };
    }
    let run = &results[0];
    let st = run.status.status;
    match st {
        0 => Verdict::Accepted {
            stdout: decode_file(run, "stdout"),
            time_ms: run.time.unwrap_or(0) / 1_000_000,
            memory_kb: run.memory.unwrap_or(0) / 1024,
        },
        1 => Verdict::TimeLimitExceeded,
        2 => Verdict::MemoryLimitExceeded,
        3 => Verdict::OutputLimitExceeded,
        4 => Verdict::IllegalSyscall {
            msg: run.status.reason.clone().unwrap_or_else(|| "illegal syscall".into()),
        },
        _ => Verdict::RuntimeError {
            // 进程没起来时 stderr 为空，但 result.error 有真因
            // （如 "The system cannot find the file specified."）
            stderr: non_empty(decode_file(run, "stderr"), run.error.as_deref()),
            signal: run.status.reason.clone(),
        },
    }
}

/// 编译 cmd 的专用映射：**一切非零状态都归 CompileError**。
///
/// 与运行期映射的区别：
/// - g++ 编译失败（Nonzero Exit）时 stderr 有真实错误信息，必须透出；
/// - 编译被 CPU/内存限制杀掉时 stderr **必然为空**（job object 直接 Terminate），
///   此时要给人话提示，不能甩一个空串 CompileError 让用户以为是平台坏了；
/// - status 0 只表示「编译通过」，stdout/time 无意义，调用方只会当门禁用。
fn map_compile_result(r: &CmdResult) -> Verdict {
    if r.status.status == 0 {
        return Verdict::Accepted {
            stdout: String::new(),
            time_ms: 0,
            memory_kb: 0,
        };
    }
    let hint = match r.status.status {
        1 => "编译超时（CPU 限制）".to_string(),
        2 => "编译超限（内存限制，可减少 include 或拆分编译单元）".to_string(),
        _ => String::new(),
    };
    let msg = non_empty(decode_file(r, "stderr"), r.error.as_deref());
    Verdict::CompileError {
        stderr: if msg.is_empty() { hint } else { msg },
    }
}

/// stderr 为空时用 error 兜底——「进程没起来」这类故障 stderr 必然为空，
/// 不看 error 字段就是「RuntimeError 但没有任何信息」。
fn non_empty(primary: String, fallback: Option<&str>) -> String {
    if !primary.is_empty() {
        return primary;
    }
    fallback.unwrap_or_default().to_string()
}

/// 封装 go-judge REST 客户端
pub struct JudgeClient {
    base: String,
    http: reqwest::Client,
}

impl JudgeClient {
    pub fn new(base: impl Into<String>) -> Self {
        Self {
            base: base.into(),
            // 只打 127.0.0.1 回环，必须绕代理：沙箱/CI 常注入 HTTP_PROXY，
            // 请求被丢给代理后轻则连不上、重则响应体被中间层动手脚
            //（表现为莫名其妙的「error decoding response body」）。
            http: reqwest::Client::builder()
                .no_proxy()
                .build()
                .unwrap_or_default(),
        }
    }

    /// 单词条请求判题（Python 路径 / 编译型语言的运行阶段）。
    /// 请求里只应有一个「运行」cmd；编译走 {@link run_cached}。
    pub async fn run(&self, req: &RunRequest) -> Result<Verdict> {
        let url = format!("{}/run", self.base);
        let resp = self.http.post(&url).json(req).send().await.map_err(NexError::Http)?;
        if !resp.status().is_success() {
            return Err(NexError::Judge(format!("go-judge http {}", resp.status())));
        }
        let body = parse_run_response(resp).await?;
        Ok(map_results(&body.results))
    }

    /// 编译请求（C++/Java 首步）：单编译 cmd + copyOutCached。
    /// 返回 (编译判定, 缓存 file_id)。编译失败判定必为 CompileError 且带真实 stderr。
    pub async fn run_cached(&self, req: &RunRequest) -> Result<(Verdict, Option<String>)> {
        let url = format!("{}/run", self.base);
        let resp = self.http.post(&url).json(req).send().await.map_err(NexError::Http)?;
        if !resp.status().is_success() {
            return Err(NexError::Judge(format!("go-judge http {}", resp.status())));
        }
        let body = parse_run_response(resp).await?;
        let verdict = match body.results.first() {
            Some(r) => map_compile_result(r),
            None => Verdict::RuntimeError {
                stderr: "empty judge response".into(),
                signal: None,
            },
        };
        let fid = body
            .results
            .first()
            .and_then(|r| r.file_ids.as_ref())
            .and_then(|m| m.get("a.exe").or_else(|| m.get("Main.class")).cloned());
        Ok((verdict, fid))
    }
}

/// 解析 `/run` 响应。
///
/// 先取文本再反序列化（而不是 `resp.json()`）：解析失败时能看到 body 片段。
/// 线格式随 go-judge 版本漂移过（status 字符串化、files 去 base64），
/// 直接 `.json()` 只会甩一句 "error decoding response body"，把真正原因吞掉。
async fn parse_run_response(resp: reqwest::Response) -> Result<RunResponse> {
    let text = resp.text().await.map_err(NexError::Http)?;
    // v1.13.3 的 /run 响应是**裸结果数组**（无 {"results":...} 包装）；
    // RunResponseWire 同时兼容旧版包装形状。
    let wire: RunResponseWire = serde_json::from_str(&text).map_err(|e| {
        let snippet: String = text.chars().take(300).collect();
        NexError::Judge(format!(
            "go-judge 响应解析失败: {e}; body[:300]={snippet}"
        ))
    })?;
    Ok(wire.into())
}

#[allow(dead_code)]
fn _status_marker(_: Status) {}
