// Tauri v2 构建脚本：处理图标、外部二进制、资源配置等。
// 注意：这里不依赖 go-judge 二进制在构建期存在——
// go-judge 通过运行时路径解析（见 config.rs::resolve_go_judge），
// 缺失时自动进入 mock/本地直跑模式，保证 `cargo build` 一定能过。
use std::path::PathBuf;

/// Windows 应用清单：依赖 Common-Controls **v6**。
///
/// 为什么必须统一由本脚本编（一个零报错的坑）：
///   Tauri 自带的清单只嵌进 **bin** 目标（`tauri-winres` → `cargo:rustc-link-arg-bins`）。
///   而 `cargo test --lib` 生成的是**另一个**测试宿主 exe，它没有清单。
///   清单里最关键的一条是依赖 `Microsoft.Windows.Common-Controls` v6：
///   没有它，Windows 只加载 System32 里的 comctl32 **v5**，
///   而 v5 不导出 `TaskDialogIndirect`（tauri-runtime-wry 的对话框要用）。
///   结果测试宿主在**加载阶段**就崩：
///       STATUS_ENTRYPOINT_NOT_FOUND (0xc0000139)
///   表现为 `cargo test` 报 "test failed, to rerun pass `--lib`"，
///   看着像代码挂了，其实是清单缺失。
///
/// 所以本脚本：把 Tauri 的默认清单换成我们这份（多一个 dpiAware），
/// 编译成 COFF 资源对象 `target/nex_manifest.o`。
/// 注意 rc 里 RT_MANIFEST 必须用**数值类型 24**（不能写字符串名 "RT_MANIFEST"，
/// 否则 windres 把资源类型存成名称、Windows 不认作 app manifest）。
/// 链接由 `.cargo/config.toml` 的全局 rustflags 链这个 .o，
/// 覆盖 **bin / lib / test 宿主 / example / integration-test 所有目标**，
/// 单一来源，彻底解决「清单只嵌 bin、example/test 缺清单」的问题。
const MANIFEST: &str = r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="Nex.Desktop" version="1.0.0.0" processorArchitecture="*"/>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type="win32"
        name="Microsoft.Windows.Common-Controls"
        version="6.0.0.0"
        processorArchitecture="*"
        publicKeyToken="6595b64144ccf1df"
        language="*"/>
    </dependentAssembly>
  </dependency>
  <application xmlns="urn:schemas-microsoft-com:asm.v3">
    <windowsSettings>
      <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true</dpiAware>
    </windowsSettings>
  </application>
</assembly>
"#;

fn main() {
    // 图标内容变化必须触发 Windows 资源重编。否则 Cargo 复用旧的
    // libresource.a，EXE 里仍是旧图标（实测 2026-11-07：换了 icon.ico，
    // 重编后 ExtractIconExW 取出来仍是蓝底白方块占位图）。
    println!("cargo:rerun-if-changed=icons/icon.ico");
    build_manifest_resource();
    // 用 Tauri 默认属性，但去掉它自带的清单（我们的那份已编进所有目标）。
    let mut win = tauri_build::WindowsAttributes::new_without_app_manifest();
    win = win.window_icon_path("icons/icon.ico");
    let attrs = tauri_build::Attributes::new().windows_attributes(win);
    tauri_build::try_build(attrs).expect("tauri-build failed");
}

/// 编译清单为 COFF 资源对象，并用 `cargo:rustc-link-arg` 链给 nex crate 的
/// **所有自身链接目标**（bin / test 宿主 / cdylib）。
///
/// 关键修正（之前 Phase17 的坑）：
///   rc 里 RT_MANIFEST 必须是**数值类型 24**，不能写成字符串名 "RT_MANIFEST"。
///   若写成字符串名，windres 把资源类型存为名称而非 24，Windows 加载器不认作
///   app manifest，SxS 不激活 → 仍加载 comctl32 v5 → 加载期崩
///   STATUS_ENTRYPOINT_NOT_FOUND (0xc0000139)。
///
/// 为什么不用 `.cargo/config.toml` 全局 rustflags：它会无差别作用于所有 crate 的
/// build script 链接（如 serde/thiserror 的 build script），那些链接的 cwd 不是
/// package root，相对路径的 .o 找不到 → 全量链接失败。这里只覆盖 nex 自身目标。
/// 取证用的 `src/bin/probe_smoke.rs` 是 nex 的 bin target，天然继承此 link-arg。
fn build_manifest_resource() {
    if std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default() != "windows" {
        return;
    }
    if std::env::var("CARGO_CFG_TARGET_ENV").unwrap_or_default() != "gnu" {
        return;
    }

    let Some(out_dir) = std::env::var("OUT_DIR").ok().map(PathBuf::from) else {
        return;
    };
    let manifest_path = out_dir.join("nex.manifest");
    let rc_path = out_dir.join("nex.rc");
    // rc 里用数值 24 表示 RT_MANIFEST（绝不能用字符串名 "RT_MANIFEST"）。
    if std::fs::write(&manifest_path, MANIFEST).is_err()
        || std::fs::write(&rc_path, "1 24 \"nex.manifest\"\n").is_err()
    {
        println!("cargo:warning=无法写出 Windows 清单/rc 文件，链接时可能缺 Common-Controls v6 清单");
        return;
    }

    let obj = out_dir.join("nex_manifest.o");
    let windres = std::env::var("WINDRES").unwrap_or_else(|_| "windres".to_string());
    match std::process::Command::new(&windres)
        .current_dir(&out_dir)
        .arg("-i")
        .arg(&rc_path)
        .arg("-o")
        .arg(&obj)
        .status()
    {
        Ok(s) if s.success() && obj.is_file() => {
            println!("cargo:rustc-link-arg={}", obj.display());
        }
        Ok(_) => println!("cargo:warning=windres 未成功编译清单资源，可能缺 Common-Controls v6 清单"),
        Err(e) => println!("cargo:warning=调用 windres 失败（{e}），可能缺 Common-Controls v6 清单"),
    }
}
