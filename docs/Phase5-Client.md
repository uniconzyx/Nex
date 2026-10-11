# 阶段 5 · 移动端 / Web 客户端交付

> 版本：v0.1 · 日期：2026-09-20 · 依赖：阶段 2 架构 + 阶段 3 数据模型 + 阶段 4 后端 + DeepSeek 接入
> 状态：客户端骨架完成，可对接阶段 4 后端运行；演示版可本地预览。

## 一、本次新增 / 变更

1. **DeepSeek 大模型接入**（并入阶段 5）：后端 `ai_provider.py` 新增 `DeepSeekProvider`（OpenAI 兼容协议），`AI_PROVIDER=deepseek` 即可切换；模型分级、双通道降级、SSE 流式、6K 上下文预算全部复用。
2. **缅因猫（Maine Coon）形象升级**：
   - `lib/widgets/cpp_cat.dart` 重写为缅因猫版：`CppCatMascot` 优先加载 `assets/images/cat_mascot/<mood>.webp`，缺失/减少动效时回退内置 `CustomPainter` 缅因猫；深色模式自动加青蓝发光边缘。
   - `web-preview/index.html` 的 `catSVG()` 同步升级为缅因猫（银蓝毛发、白胸前毛、蓝框半透明眼镜、猞猁耳尖、蓬松轮廓），深色模式 `drop-shadow` 发光。
   - 资源清单与制作规范见 `app/assets/images/cat_mascot/README.md`（8 种表情 + Lottie 加载动画）。

## 二、Flutter 工程结构（`app/`）

```
app/
├── pubspec.yaml                 # Flutter 3 + Riverpod + go_router + code_text_field + lottie + flutter_svg
├── lib/
│   ├── main.dart                # ProviderScope + MaterialApp.router（双主题 / 字号缩放）
│   ├── core/
│   │   ├── api/api_client.dart  # Dio 封装 + envelope 解包 + 401 旋转刷新 + ApiException
│   │   ├── auth/auth.dart       # 登录态 Provider
│   │   ├── settings/settings.dart # 主题 / 减少动效 / 字号（可访问性）
│   │   ├── storage/local_cache.dart # 离线缓存（hive）
│   │   ├── theme/{app_colors,app_theme}.dart # 蓝白设计系统 tokens
│   │   ├── router/app_router.dart # 11 页路由 + 5 Tab Shell
│   │   └── models/models.dart  # 与后端一一对应
│   ├── widgets/cpp_cat.dart     # 缅因猫形象（图片优先 + CustomPainter 兜底 + 发光）
│   └── features/
│       ├── splash/  home/  mindmap/  course/  editor/  exercises/
│       ├── ai/  wrongbook/  projects/  resources/  profile/  auth/
└── assets/images/cat_mascot/    # 缅因猫占位目录（放入真实 webp 即生效）
```

- **页面清单**：启动页、首页（进度环 + 每日一题 + 继续学习）、思维导图（四态着色 + 点击 CppCat 提示）、课程详情（代码块 + 角落猫）、在线编辑器（纯 Dart 编辑器 + 沙箱判题 + 猫状态联动）、题库（难度筛选）、AI 对话（6 模式 + 流式兜底）、错题本（间隔复习）、项目实战（三类）、资源中心（分组外链）、个人中心（徽章 + 数据图 + 设置）、登录。
- **设计系统落地**：`AppColors` / `AppTheme` 与 web 演示、Tailwind 同源；卡片 18px、按钮 14px、输入框 12px、柔和蓝微光；暗色模式双套配色与对比度。
- **可访问性**：减少动效开关、字号缩放（0.85–1.3）、触控区域充足。

## 三、可运行演示（`web-preview/index.html`）

高保真蓝白猫咪 App 演示（手机壳内 11 页 + 缅因猫 + 暗色模式 + 自动巡播）。
本地预览：`cd web-preview && python -m http.server 8788`，浏览器开 `http://localhost:8788`。

## 四、如何运行完整项目

```bash
# 1) 后端（阶段 4，含 DeepSeek）
cd server
pip install -r requirements.txt
cp .env.example .env          # AI_PROVIDER=deepseek, DEEPSEEK_API_KEY=***
uvicorn app.main:app --port 8000 --reload

# 2) Flutter 移动端
cd app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

# 3) Web 演示（无需后端即可看 UI）
cd web-preview && python -m http.server 8788
```

## 五、逻辑漏洞自查（新规则）

| # | 检查点 | 结论 |
|---|---|---|
| 1 | 缅因猫图片缺失时 App 是否崩溃 | 否：`CppCatMascot` errorBuilder 回退 CustomPainter |
| 2 | 后端未启动时各页面是否可用 | 是：所有列表页均有离线占位数据兜底 |
| 3 | 判题轮询是否可能死循环 | 否：最多 20 次 × 600ms ≈ 12s 封顶 |
| 4 | 401 刷新是否死循环 | 否：`_isRefreshCall` 排除刷新请求 + `_refreshing` 锁 |
| 5 | `withValues` 兼容性 | 需 Flutter ≥ 3.27（现代 3.x 满足）；旧版本改 `withOpacity` 即可 |
| 6 | Chip 无 `padding` 参数 | 已修正为 `labelPadding`（4 处） |
| 7 | 导图点击命中范围 | 半径 26px 命中，仅对存在节点触发 |
| 8 | 资源合规红线 | 外部题仅存元数据 + 链接，不搬运题面正文 |

> 注：Flutter 工程因本机无 SDK 未做 `flutter analyze` 编译；已逐文件做语法/接口人工核对并修正 `Chip` 隐患。真实编译请在本机 `flutter pub get` 后运行。
