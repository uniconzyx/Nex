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
/// 并用 `cargo:rustc-link-arg` 编给**所有**链接目标
/// （bin / 测试宿主 / cdylib），保证 test 与 build 运行时行为一致。
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
    build_manifest_resource();
    // 用 Tauri 默认属性，但去掉它自带的清单（我们的那份已编进所有目标）。
    let mut win = tauri_build::WindowsAttributes::new_without_app_manifest();
    win = win.window_icon_path("icons/icon.ico");
    let attrs = tauri_build::Attributes::new().windows_attributes(win);
    tauri_build::try_build(attrs).expect("tauri-build failed");
}

/// 编译清单为 COFF 资源对象，并链给所有链接目标。
///
/// - GNU 工具链：windres 编译 .rc → .o，再 `cargo:rustc-link-arg`。
/// - MSVC 工具链：Tauri 已用 mt.exe 正确嵌 bin 清单；MSVC 链接器会自动
///   生成外置 .manifest，测试宿主同样能解析到 v6 控件，无需额外处理。
fn build_manifest_resource() {
    if std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default() != "windows" {
        return;
    }
    if std::env::var("CARGO_CFG_TARGET_ENV").unwrap_or_default() == "msvc" {
        return;
    }

    let Some(out_dir) = std::env::var("OUT_DIR").ok().map(PathBuf::from) else {
        return;
    };
    let manifest_path = out_dir.join("nex.manifest");
    let rc_path = out_dir.join("nex.rc");
    if std::fs::write(&manifest_path, MANIFEST).is_err() {
        println!("cargo:warning=无法写出 Windows 清单文件，cargo test 可能报 STATUS_ENTRYPOINT_NOT_FOUND");
        return;
    }
    if std::fs::write(&rc_path, "1 RT_MANIFEST \"nex.manifest\"\n").is_err() {
        println!("cargo:warning=无法写出 rc 文件，cargo test 可能报 STATUS_ENTRYPOINT_NOT_FOUND");
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
        Ok(_) => {
            println!("cargo:warning=windres 未成功编译清单资源，Windows 下 cargo test 可能报 STATUS_ENTRYPOINT_NOT_FOUND");
        }
        Err(e) => {
            println!("cargo:warning=调用 windres 失败（{e}），Windows 下 cargo test 可能报 STATUS_ENTRYPOINT_NOT_FOUND");
        }
    }
}
