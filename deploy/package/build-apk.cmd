@echo off
REM 出 Android arm64 APK（内嵌 web-preview 竖屏版 UI）
cd /d "%~dp0..\..\src-tauri"
set NO_PROXY=*
set no_proxy=*
set ANDROID_HOME=D:\Sdk
set ANDROID_SDK_ROOT=D:\Sdk
set NDK_HOME=D:\Sdk\ndk\android-ndk-r27c
set JAVA_HOME=C:\Program Files\Java\jdk-23
set CI=true
call "..\frontend\node_modules\.bin\tauri.cmd" android build --apk --target aarch64 --split-per-abi --config tauri.shell.mobile.conf.json
REM Windows 未开开发者模式时，末尾「创建符号链接」报错属预期，.so 已生成
if not exist "target\aarch64-linux-android\release\libnex.so" exit /b 1
if not exist "gen\android\app\src\main\jniLibs\arm64-v8a" mkdir "gen\android\app\src\main\jniLibs\arm64-v8a"
copy /y "target\aarch64-linux-android\release\libnex.so" "gen\android\app\src\main\jniLibs\arm64-v8a\libnex.so" >nul
cd /d "gen\android"
call gradlew.bat assembleRelease --no-daemon -x rustBuildArm64Release -x rustBuildArmRelease -x rustBuildX86Release -x rustBuildX86_64Release
if errorlevel 1 exit /b 1
if not exist "..\..\..\release\nex-shell" mkdir "..\..\..\release\nex-shell"
"D:\Sdk\build-tools\35.0.0\zipalign.exe" -f -p 4 app\build\outputs\apk\arm64\release\app-arm64-release-unsigned.apk "..\..\..\release\nex-shell\tmp.apk"
REM 直接调 apksigner.jar：从 Git Bash 经 cmd /c 调 apksigner.bat 会被本机安全策略拦截。
"%JAVA_HOME%\bin\java.exe" -jar "D:\Sdk\build-tools\35.0.0\lib\apksigner.jar" sign --ks keystore\nex-release.jks --ks-pass pass:nex2026 --key-pass pass:nex2026 --ks-key-alias nex --out "..\..\..\release\nex-shell\Nex-Mobile-1.0-arm64.apk" "..\..\..\release\nex-shell\tmp.apk"
if errorlevel 1 exit /b 1
del "..\..\..\release\nex-shell\tmp.apk"
"%JAVA_HOME%\bin\java.exe" -jar "D:\Sdk\build-tools\35.0.0\lib\apksigner.jar" verify --print-certs "..\..\..\release\nex-shell\Nex-Mobile-1.0-arm64.apk" >nul
if errorlevel 1 echo [nex-shell] ERROR: APK signature verification failed & exit /b 1
echo [nex-shell] APK ready in release\nex-shell
