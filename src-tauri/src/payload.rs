use serde::{Deserialize, Deserializer, Serialize};
use serde::de::{MapAccess, Visitor};
use std::collections::HashMap;
use std::fmt;

/// 对应 go-judge `POST /run` 的请求体。
///
/// # 线格式锚定 go-judge v1.13.3（cmd/go-judge/model/model.go）
/// 这一版相对旧版有几处**静默断层**——字段发错位置不会报错，只会被 Go 的
/// JSON 解码直接忽略，表现为「判题能跑但结果全错」：
/// 1. `copyIn` / `copyOut` / `copyOutCached` / 各种 limit 全在 **Cmd 级**；
///    发在 Request 顶层会被静默丢弃（源码进不了沙箱、编译缓存永不命中）。
/// 2. 输出占位文件必须**同时**给 `name` + `max`（`convertCmdFile` 的 default
///    分支对「只有 name」直接返 400）。
/// 3. 墙钟上限字段叫 `clockLimit`（没有 `timeLimit`）。
/// 4. 响应侧：`status` 是**字符串**（`"Accepted"`），`files` 是
///    `map[name]原文`（值不再是 `{content,size}` 对象）。
/// 5. `content`（copyIn / stdin）是**原文**不是 base64：上游 `strToBytes`
///    是零拷贝不解码；响应 `files` 的值同理（`byteArrayToString`）。
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct RunRequest {
    /// 顺序执行的命令数组。
    ///
    /// **不共享文件系统**：v1.13.3 的 worker 对 group 内每个 cmd 单独
    /// `envPool.Get()` 一个 Environment（独立 root/tmp，见 worker.go
    /// `workDoGroup`）。多 cmd 单请求只用于 pipe 管道；编译型语言必须
    /// 「编译请求拿 fileId → 运行请求 copyIn(fileId)」两次请求，
    /// 同请求放 [编译, 运行] 会让 run cmd 找不到编译产物
    /// （实测 `Internal Error: The system cannot find the file specified.`）。
    pub cmd: Vec<CmdSpec>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct CmdSpec {
    pub args: Vec<String>,
    /// 环境变量。**go-judge 不继承宿主机环境**（winc/容器执行体只透传
    /// TMP/TEMP），裸命令名（python/g++）靠 PATH 解析，必须显式注入。
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub env: Option<Vec<String>>,
    /// files[0] 作为 stdin 输入，其余作为待捕获的 stdout/stderr 输出
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub files: Option<Vec<FileSpec>>,
    /// CPU 时间上限（纳秒）
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cpu_limit: Option<u64>,
    /// 墙钟上限（纳秒）——线格式字段名 clockLimit；留空由宿主看门狗兜底
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub clock_limit: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub memory_limit: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub proc_limit: Option<u32>,
    /// 本命令的输入文件（v1.13.3 起在 Cmd 级）
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub copy_in: Option<HashMap<String, CopyIn>>,
    /// 需要回传的文件名（stdout/stderr 由 files 占位后自动收集，这里用于普通文件）
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub copy_out: Option<Vec<String>>,
    /// 需要缓存为 fileId 的文件（多测试用例复用编译产物，避免重复编译）
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub copy_out_cached: Option<Vec<String>>,
}

/// 文件描述：输入（原文内容 / fileId）或输出占位（name + max）。
///
/// **注意 v1.13.3 的原文语义**：`content` 是**原文**（不是 base64！）。
/// 上游 `strToBytes` 是零拷贝 `unsafe.Slice`，不做任何解码；旧版 REST API
/// 的 base64 约定已变。响应侧 `files` 的值同样是原文（`byteArrayToString`
/// 零拷贝），见 {@link CmdResult}。
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
// 注意：enum 上的 rename_all 只作用于**变体名**，不作用于变体里的字段。
// 要让 fileId 正确落到 field_id，必须把 rename_all 写在**每个变体上**（写在 enum 上会让
// go-judge 的 fileId 永远解析不出来 → 编译产物缓存复用失效，每用例都得重编译）。
pub enum FileSpec {
    /// 输出占位：name + max **必须同时给**（v1.13.3 `convertCmdFile` 要求，
    /// 只有 name 会落入 default 分支返 400 "file type is not valid"）。
    Out { name: String, max: u64 },
    /// 输入：原文内容（stdin 等）/ 复用缓存 fileId
    #[serde(rename_all = "camelCase")]
    In {
        #[serde(default, skip_serializing_if = "Option::is_none")]
        content: Option<String>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        file_id: Option<String>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        max: Option<u64>,
    },
}

/// Cmd 级 copyIn 的值（v1.13.3 `CmdFile`：src/content/fileId/name/max/symlink/…）。
/// `content` 为**原文**（上游零拷贝不解码 base64）；`mode` 字段上游不存在。
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct CopyIn {
    /// 源文件内容（原文，非 base64）。与 fileId 二选一。
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub content: Option<String>,
    /// 复用已缓存文件（copyOutCached 返回的 fileId），避免重复编译
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub file_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

/// go-judge `POST /run` 的响应体。
///
/// **v1.13.3 的实际形状是裸的结果数组**——`cmd_handler` 直接
/// `Encode(res.Results)`，没有包装对象。旧版是 `{"results": [...]}`。
/// 两种都吃（`RunResponseWire`），避免再被线格式漂移坑一次。
#[derive(Debug, Clone, Default)]
pub struct RunResponse {
    pub results: Vec<CmdResult>,
}

/// 响应线格式的两种历史形状。
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum RunResponseWire {
    /// v1.13.3：`[{...},{...}]`
    Bare(Vec<CmdResult>),
    /// 旧版：`{"results":[{...}]}`
    Wrapped {
        results: Vec<CmdResult>,
    },
}

impl From<RunResponseWire> for RunResponse {
    fn from(w: RunResponseWire) -> Self {
        match w {
            RunResponseWire::Bare(results) => Self { results },
            RunResponseWire::Wrapped { results } => Self { results },
        }
    }
}

/// 单条命令的执行结果。
/// `error` / `exit_status` / `run_time` 是线格式契约字段（调试与排障用），
/// 当前映射逻辑不读，故允许 dead_code。
#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct CmdResult {
    pub status: Status,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub exit_status: Option<i32>,
    #[serde(default)]
    pub time: Option<u64>, // 纳秒
    #[serde(default)]
    pub memory: Option<u64>, // 字节
    #[serde(default)]
    pub run_time: Option<u64>,
    /// v1.13.3：`map[name]原文`（值即输出文本，**不是 base64**；旧版是
    /// `{content,size}` base64 对象，已移除）
    #[serde(default)]
    pub files: Option<HashMap<String, String>>,
    #[serde(default)]
    pub file_ids: Option<HashMap<String, String>>,
}

/// 判题状态。
///
/// 内部沿用数字码（与前端/文档约定一致）：
/// `0=Accepted 1=TLE 2=MLE 3=OLE 4=IllegalSyscall 5=FileError
///  6=非零退出/信号 7=内部错误`
///
/// **线上格式随 go-judge 版本变过**，两种都吃：
/// * v1.13.x：`"status": "Accepted"`（字符串，见 envexec/run_status.go
///   的 `statusToString` 表——注意是带空格的人话，不是枚举名）
/// * 旧版：`"status": {"status": 0, "reason": null}`（数字对象）
///
/// 只认其中一种的后果：升级 go-judge 后**整个响应解析失败**，判题全变
/// RuntimeError，且报错信息完全指不到真正原因。
#[derive(Debug, Clone, Default)]
pub struct Status {
    pub status: u32,
    pub reason: Option<String>,
}

impl Status {
    /// v1.13.x 字符串 → 内部数字码（statusToString 表逐条对齐）。
    fn from_wire_str(s: &str) -> Self {
        let code = match s {
            "Accepted" => 0,
            "Time Limit Exceeded" => 1,
            "Memory Limit Exceeded" => 2,
            "Output Limit Exceeded" => 3,
            "Dangerous Syscall" => 4,
            "File Error" => 5,
            "Nonzero Exit Status" | "Signalled" => 6,
            // Invalid / Wrong Answer / Partially Correct / Judgement Failed /
            // Invalid Interaction / Internal Error
            _ => 7,
        };
        Self {
            status: code,
            reason: Some(s.to_string()),
        }
    }
}

impl<'de> Deserialize<'de> for Status {
    fn deserialize<D>(d: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct StatusVisitor;

        impl<'de> Visitor<'de> for StatusVisitor {
            type Value = Status;

            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(r#"a status string ("Accepted") or {"status":0,"reason":null}"#)
            }

            fn visit_str<E>(self, v: &str) -> Result<Status, E>
            where
                E: serde::de::Error,
            {
                Ok(Status::from_wire_str(v))
            }

            fn visit_map<A>(self, mut map: A) -> Result<Status, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut status: Option<u32> = None;
                let mut reason: Option<String> = None;
                while let Some(key) = map.next_key::<String>()? {
                    match key.as_str() {
                        "status" => status = Some(map.next_value::<u32>()?),
                        "reason" => reason = map.next_value::<Option<String>>()?,
                        _ => {
                            let _ = map.next_value::<serde_json::Value>()?;
                        }
                    }
                }
                Ok(Status {
                    status: status.unwrap_or(7),
                    reason,
                })
            }
        }

        d.deserialize_any(StatusVisitor)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 守住 go-judge v1.13.3 线格式：camelCase + Cmd 级 copyIn/copyOutCached。
    /// 曾经字段直接叫 camelCase 触发 non_snake_case 警告，改成 rename_all 方案后
    /// 必须证明序列化结果没变（否则会出现「能编译能跑、但 go-judge 收不到参数」的假通过）。
    #[test]
    fn request_serializes_to_camel_case() {
        let mut copyin: HashMap<String, CopyIn> = HashMap::new();
        copyin.insert(
            "sol.py".to_string(),
            CopyIn {
                content: Some("print(1)\n".into()),
                ..Default::default()
            },
        );
        let req = RunRequest {
            cmd: vec![CmdSpec {
                args: vec!["python".into(), "-u".into(), "sol.py".into()],
                env: Some(vec!["PATH=/usr/bin".into()]),
                files: Some(vec![
                    FileSpec::In {
                        content: Some(String::new()),
                        name: None,
                        file_id: None,
                        max: None,
                    },
                    FileSpec::Out {
                        name: "stdout".into(),
                        max: 16 * 1024 * 1024,
                    },
                    FileSpec::Out {
                        name: "stderr".into(),
                        max: 4 * 1024 * 1024,
                    },
                ]),
                cpu_limit: Some(2_000_000_000),
                clock_limit: Some(5_000_000_000),
                memory_limit: Some(384 * 1024 * 1024),
                proc_limit: Some(32),
                copy_in: Some(copyin),
                copy_out_cached: Some(vec!["a.exe".into()]),
                ..Default::default()
            }],
        };
        let json = serde_json::to_value(&req).expect("serialize");
        let cmd = &json["cmd"][0];
        for key in [
            "args",
            "env",
            "files",
            "cpuLimit",
            "clockLimit",
            "memoryLimit",
            "procLimit",
            "copyIn",
            "copyOutCached",
        ] {
            assert!(cmd.get(key).is_some(), "cmd 缺少 camelCase 字段 {key}: {json}");
        }
        assert_eq!(cmd["cpuLimit"], serde_json::json!(2_000_000_000u64));
        assert_eq!(cmd["clockLimit"], serde_json::json!(5_000_000_000u64));
        // 输出占位必须同时带 name + max（v1.13.3 的硬性要求）
        assert_eq!(cmd["files"][1]["name"], serde_json::json!("stdout"));
        assert_eq!(cmd["files"][1]["max"], serde_json::json!(16 * 1024 * 1024u64));
        // 请求顶层不应再出现这些字段（上游已移除，发了会被静默忽略）
        let obj = json.as_object().expect("object");
        assert!(!obj.contains_key("copyIn"), "copyIn 不应在请求顶层: {json}");
        assert!(!obj.contains_key("cpuLimit"), "cpuLimit 不应在请求顶层: {json}");
    }

    /// 输出占位序列化形状：name + max 缺一不可。
    #[test]
    fn out_file_spec_requires_name_and_max() {
        let f = FileSpec::Out {
            name: "stdout".into(),
            max: 1024,
        };
        let v = serde_json::to_value(&f).expect("serialize");
        assert_eq!(v["name"], serde_json::json!("stdout"));
        assert_eq!(v["max"], serde_json::json!(1024u64));
    }

    /// 反序列化同样吃 go-judge 的 camelCase 响应
    #[test]
    fn cmd_result_parses_camel_case_response() {
        let raw = r#"{"status":{"status":0,"reason":null},"exitStatus":0,"fileIds":{"a.exe":"abc123"}}"#;
        let r: CmdResult = serde_json::from_str(raw).expect("deserialize");
        assert_eq!(r.status.status, 0);
        assert_eq!(r.exit_status, Some(0));
        assert_eq!(
            r.file_ids.as_ref().and_then(|m| m.get("a.exe")).map(String::as_str),
            Some("abc123")
        );
    }

    /// v1.13.x 响应：status 是字符串、files 值是**原文**（非 base64）。
    /// 这条守住「升级 go-judge 后响应解析整体失败」的断层。
    #[test]
    fn cmd_result_parses_string_status_and_plain_files() {
        let raw = r#"{"status":"Accepted","exitStatus":0,"time":123000,"memory":20480,
            "files":{"stdout":"Hello Nex","stderr":""}}"#;
        let r: CmdResult = serde_json::from_str(raw).expect("deserialize");
        assert_eq!(r.status.status, 0, "Accepted 应映射为 0");
        assert_eq!(r.time, Some(123_000));
        let stdout = r.files.as_ref().and_then(|m| m.get("stdout")).expect("stdout");
        assert_eq!(stdout, "Hello Nex");
    }

    /// 状态字符串 → 内部数字码，逐条对齐 envexec 的 statusToString 表。
    #[test]
    fn status_string_maps_to_internal_codes() {
        let cases = [
            ("Accepted", 0u32),
            ("Time Limit Exceeded", 1),
            ("Memory Limit Exceeded", 2),
            ("Output Limit Exceeded", 3),
            ("Dangerous Syscall", 4),
            ("File Error", 5),
            ("Nonzero Exit Status", 6),
            ("Signalled", 6),
            ("Internal Error", 7),
            ("Invalid", 7),
        ];
        for (s, code) in cases {
            let raw = format!(r#"{{"status":"{s}"}}"#);
            let r: CmdResult = serde_json::from_str(&raw).expect("deserialize");
            assert_eq!(r.status.status, code, "{s} 应映射为 {code}");
        }
    }

    #[test]
    fn file_spec_in_parses_file_id() {
        let raw = r#"{"content":null,"fileId":"fid-42"}"#;
        match serde_json::from_str::<FileSpec>(raw).expect("deserialize") {
            FileSpec::In { file_id, .. } => assert_eq!(file_id.as_deref(), Some("fid-42")),
            other => panic!("应命中 In 变体，实际: {other:?}"),
        }
    }
}
