use std::path::PathBuf;

/// 将应用运行目录加入 Windows Defender 排除项。
///
/// 注意分层：
/// - 运行时（本函数）：尝试静默提权执行 `Add-MpPreference -ExclusionPath`，会弹 UAC，
///   用户可拒绝——拒绝则忽略，不影响功能（仅首次本机会被 Defender 扫描拖慢）。
/// - 安装期（installer.nsi，RequestExecutionLevel admin）：以管理员身份无感执行，
///   这才是“真正静默”的加白时机（见 installer/installer.nsi）。
///
/// 重要：路径末尾不要带反斜杠，否则 Add-MpPreference 解析异常。
pub fn ensure_exclusion(resource_dir: Option<PathBuf>) -> anyhow::Result<()> {
    #[cfg(windows)]
    {
        let dir = resource_dir
            .or_else(|| {
                std::env::current_exe()
                    .ok()
                    .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            })
            .unwrap_or_default();
        let mut dir = dir.to_string_lossy().replace('/', "\\");
        dir = dir.trim_end_matches('\\').to_string(); // 末尾不要反斜杠

        // Start-Process -Verb RunAs 触发提权；失败/拒绝则忽略
        let ps = format!(
            "Start-Process powershell -Verb RunAs -WindowStyle Hidden -ArgumentList '-NoProfile -Command Add-MpPreference -ExclusionPath \"{}\"'",
            dir
        );
        let _ = std::process::Command::new("powershell")
            .args(["-NoProfile", "-Command", &ps])
            .status();
        Ok(())
    }
    #[cfg(not(windows))]
    {
        let _ = resource_dir;
        Ok(())
    }
}
