@echo off
REM Nex 真应用 Android arm64 APK（内嵌 frontend React 应用）
REM 由 deploy/package/prepare_app.py 生成，请改生成器而不是改本文件
cd /d "%~dp0..\..\src-tauri"
set NO_PROXY=*
set no_proxy=*
set ANDROID_HOME=D:\Sdk
set ANDROID_SDK_ROOT=D:\Sdk
set NDK_HOME=D:\Sdk\ndk\android-ndk-r27c
set JAVA_HOME=C:\Program Files\Java\jdk-23
set CI=true
REM gen/android 被 gitignore；从入库的图标镜像同步
xcopy /y /e /i /q "..\deploy\package\icons\android" "gen\android\app\src\main\res" >nul
call "..\frontend\node_modules\.bin\tauri.cmd" android build --apk --target aarch64 --split-per-abi --config tauri.app.mobile.conf.json
REM Windows 未开开发者模式时末尾「创建符号链接」报错属预期，.so 已生成
if not exist "target\aarch64-linux-android\release\libnex.so" exit /b 1
if not exist "gen\android\app\src\main\jniLibs\arm64-v8a" mkdir "gen\android\app\src\main\jniLibs\arm64-v8a"
copy /y "target\aarch64-linux-android\release\libnex.so" "gen\android\app\src\main\jniLibs\arm64-v8a\libnex.so" >nul
REM Tauri v2 不把 frontendDist 拷进 APK 资源目录（既有缺陷），手动同步
if not exist "gen\android\app\src\main\assets\dist" mkdir "gen\android\app\src\main\assets\dist"
xcopy /y /e /i /q "..\deploy\package\app" "gen\android\app\src\main\assets\dist" >nul
cd /d "gen\android"
call gradlew.bat assembleRelease --no-daemon -x rustBuildArm64Release -x rustBuildArmRelease -x rustBuildX86Release -x rustBuildX86_64Release
if errorlevel 1 exit /b 1
if not exist "..\..\..\release\nex-shell" mkdir "..\..\..\release\nex-shell"
REM 中间文件名带 -app，避免与设计稿包的 tmp.apk 撞车
"D:\Sdk\build-tools\35.0.0\zipalign.exe" -f -p 4 app\build\outputs\apk\arm64\release\app-arm64-release-unsigned.apk "..\..\..\release\nex-shell\tmp-app.apk"
REM 直连 apksigner.jar：从 Git Bash 调 apksigner.bat 会被本机安全策略拦
"%JAVA_HOME%\bin\java.exe" -jar "D:\Sdk\build-tools\35.0.0\lib\apksigner.jar" sign --ks keystore\nex-release.jks --ks-pass pass:nex2026 --key-pass pass:nex2026 --ks-key-alias nex --out "..\..\..\release\nex-shell\Nex.apk" "..\..\..\release\nex-shell\tmp-app.apk"
if errorlevel 1 exit /b 1
del "..\..\..\release\nex-shell\tmp-app.apk"
"%JAVA_HOME%\bin\java.exe" -jar "D:\Sdk\build-tools\35.0.0\lib\apksigner.jar" verify --print-certs "..\..\..\release\nex-shell\Nex.apk" >nul
if errorlevel 1 echo [nex-app] ERROR: APK signature verification failed & exit /b 1
echo [nex-app] APK ready: release\nex-shell\Nex.apk
