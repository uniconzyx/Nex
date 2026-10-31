; ============================================================
;  Nex 安装脚本（NSIS，参考模板）
;  要点（对应优先级 3）：
;   - RequestExecutionLevel admin：以管理员权限运行，
;     这样 Add-MpPreference 才能「无感」写入 Defender 排除项，
;     不会像运行时那样弹 UAC。
;   - 安装阶段（而非运行阶段）执行 Add-MpPreference。
;   - 排除项路径末尾不带反斜杠（Defender 要求）。
;  实际打包时可直接用 Tauri 的 nsis 集成；此文件作为自定义
;  customTemplatePath 的参考，或在 CI 里独立调用 makensis。
; ============================================================
!include "MUI2.nsh"
!include "FileFunc.nsh"

Name "Nex"
OutFile "Nex-Setup.exe"
InstallDir "$PROGRAMFILES\Nex"
RequestExecutionLevel admin        ; 关键：管理员权限
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

Section "Install" SecInstall
  SetOutPath "$INSTDIR"
  ; 把 Tauri 打包产物拷入（真实场景由 Tauri 注入；这里演示结构）
  File /r "..\src-tauri\target\release\bundle\*"

  ; ---- 优先级 3：安装期静默加入 Defender 排除项 ----
  ; 路径末尾不要带反斜杠
  ExecWait 'powershell -NoProfile -WindowStyle Hidden -Command "Add-MpPreference -ExclusionPath \"$INSTDIR\""'

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Nex" \
    "DisplayName" "Nex"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Nex" \
    "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
SectionEnd

Section "Uninstall" SecUninstall
  ; 卸载时移除排除项
  ExecWait 'powershell -NoProfile -WindowStyle Hidden -Command "Remove-MpPreference -ExclusionPath \"$INSTDIR\""'
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Nex"
SectionEnd
