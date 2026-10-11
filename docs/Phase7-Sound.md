# 阶段7 增补 · CppCat AI 助手音效系统

> 交付时间：2026-10-07
> 范围：Flutter 主端 + Web 预览版（web-preview），双端同一套声音设计

## 一、为什么做音效

CppCat 是「陪伴型」AI 助手，此前只有视觉反馈（表情动效 + 气泡）。音效补齐了
**非视觉通道**的即时反馈：发送成功、AI 开始思考、回复到达、编译通过/失败、答题对错。
对「编译」这类**等待 1~2 秒**的操作，声音比动画更能降低不确定感。

设计上遵循三条约束：

1. **CppCat 是电子喵**——轻、短、上扬为主，不用系统提示音（太"机器"）。
2. **失败音必须柔和**（下行小三度、音量 0.7）：学习者编译报错时已经在挫败状态，
   再给一声刺耳的"错误音"会加重负面情绪。
3. **绝不打扰**——见 §五「噪音控制」。

## 二、音效清单与声音设计

| 事件 | 文件名 | 音色构成 | 时长 | 音量 |
|---|---|---|---|---|
| 发送消息 | `send.wav` | 620→1040 Hz 上扬滑音（带 22Hz 微颤音） | 120 ms | 0.85 |
| 收到回复 | `receive.wav` | 880 Hz → 1170 Hz 双音上行 | 218 ms | 0.85 |
| 思考 / 编译中 | `thinking.wav` | 1318 ×2 + 1568 Hz 三连轻 ping | 285 ms | 0.55 |
| 编译通过 / 答对 | `success.wav` | C5-E5-G5 上行琶音 | 330 ms | 0.85 |
| AC / 庆祝 | `celebrate.wav` | C5-E5-G5 + C6 + 高音闪光 | 410 ms | 0.90 |
| 编译失败 / 答错 | `fail.wav` | 466 Hz → 392→349 Hz 下行小三度 | 350 ms | 0.70 |
| 点击猫咪 | `tap.wav` | 1568 Hz 极短 blip | 35 ms | 0.50 |

频率取 C 大调五度内音程（听感友好）；`success` 与 `celebrate` 用同一琶音主题、
后者延长并加高音，形成「同一句话说得更兴奋」的关系。

7 个音效合计 **151 KB**（16-bit / 44.1 kHz / 单声道），对安装包几乎无影响。

## 三、双端实现（Web Audio 实时合成 / WAV 资源）

| | Flutter 主端 | Web 预览版 |
|---|---|---|
| 实现 | `audioplayers` 播放 WAV 资源 | Web Audio API 实时合成（不加载文件） |
| 资源 | `app/assets/audio/*.wav` | 无（零资源、零请求） |
| 生成 | `app/tool/gen_audio_assets.py`（纯标准库） | — |
| 引擎 | `app/lib/core/audio/sound_service.dart` | `web-preview/index.html` 的 `CppSound` |

**合成算法两端一致**：相位累加滑音 + 5 ms attack + 指数衰减包络
（`exp(-decay · t)`），因此同一事件在两端听感相同。

### ⚠️ 三处同源（改音色必须同步）

改任何一个音效，都要同时改这四处：

1. `app/tool/gen_audio_assets.py` — `SOUNDS` 表（生成 WAV）
2. `app/assets/audio/*.wav` — 实际资源（跑生成器刷新）
3. `app/lib/core/audio/sound_service.dart` — `CppSound` 枚举
4. `web-preview/index.html` — Web Audio 引擎的 `S` 表

**这四处的一致性已自动化校验**，无需人工记忆：

```bash
python app/tool/check_dart_health.py     # [C] 音效三处同源
```

## 四、接入点清单

### Flutter 主端

| 文件 | 触发点 | 音效 |
|---|---|---|
| `features/ai/ai_page.dart` | 点击发送 / 回车 | `send` |
| | 请求发出 450 ms 后仍无响应 | `thinking` |
| | SSE 流结束 | `receive` |
| | 请求异常走降级分支 | `fail` |
| | 切换辅导模式（ChoiceChip） | `tap` |
| `widgets/cpp_cat.dart` | 点击猫咪（`MaineCoonAssistant`） | `tap` |
| | `AssistantStatus` 跃迁到 thinking/success/celebrate/fail | 对应音效 |
| `features/profile/profile_page.dart` | 设置 → 音效开关 | — |

### Web 预览版

| 函数 | 触发点 | 音效 |
|---|---|---|
| `gotoPage()` | 页面切换（同页重复点击不响） | `tap` |
| `mount()` | 点击任意 CppCat 头像 | `tap` |
| `sendChat()` | 发送 / 打字机输出结束 | `send` / `receive` |
| `runJudgeDemo()` | 编译开始 / 失败 / AC | `thinking` / `fail` / `celebrate` |
| `answer()` | 答对 / 答错 | `success` / `fail` |
| 设置页 | 音效开关 | `tap`（并联动 `CppSound.setEnabled`） |

## 五、噪音控制（关键设计）

音效做不好就是骚扰。以下每条都是刻意的：

1. **「思考中」延迟 450 ms 才响**：模型快速响应时只响 `send`→`receive` 两声；
   三声叠在一起会很乱。若 450 ms 内已开始吐字，计时器被取消。
2. **按状态跃迁发声，而非按渲染发声**：`didUpdateWidget` 里比较 `oldWidget.status`，
   同状态重复传入不响——否则父级每次 rebuild 都会喵一声。
3. **`idle` / `loading` / `sleeping` 不配声音**：这些状态在滚动/进场时高频出现。
4. **`CatLoader` 刻意不接音效**：它散落在 7 处（题库、课程、编辑器…），
   接上去会变成"每翻一页响一次"。
5. **`MaineCoonAssistant.sound` 开关**：列表里批量渲染多只猫咪时可关掉，
   避免"多猫齐鸣"。
6. **独立于「减少动效」的单独开关**：动效与声音是两种不同的无障碍偏好，
   合并会让"想安静但要看动画"的用户无法表达。默认开启。
7. **失败连续 3 次即整体静音**：桌面/Web 等平台若无音频后端，
   只报一次日志，不刷屏、不抛异常。

## 六、已知限制

1. **本机无 flutter/dart 工具链**，Flutter 侧代码**未经编译验证**——已用静态检查
   （`check_dart_health.py`）覆盖 import 路径、枚举引用、音效同源三类问题，
   但类型/API 签名无法本地校验，已逐条比对 pub.dev 文档：
   * `AudioCache.load/loadAll` 的参数是 `String fileName`（**不是** `Source`），v1 初版曾写错，已修；
   * `unawaited` 来自 `dart:async`，已补导入。
2. **Web 端首次播放需用户手势**：浏览器自动播放策略要求 `AudioContext` 在用户
   交互后创建/恢复。本实现的首次发声场景（点发送、点猫咪、切页）本身就带手势，
   故不会出现"静默失败"；但**页面刚加载时不会有声音**，属预期。
3. 新增依赖 `audioplayers: ^6.1.0`，需执行 `flutter pub get` 后生效。

## 七、逻辑自查（本轮）

1. **同文件并发 Edit 会互相覆盖** —— 本轮给 `web-preview/index.html` 做 10 处音效接入时，
   同一批发出的多个编辑只有 3 处真正落盘（后写覆盖前写，且工具均报"成功"）。
   **修正**：改为"脚本一次性原子替换 + 每处断言恰好命中 1 次"，7 处缺失全部补齐。
   **教训**：同一文件的多处修改要么串行、要么走脚本，不能靠同批并行编辑。
2. **发现并修复两个既存编译错误**（与音效无关，是前端长期未构建掩盖的）：
   * `lib/widgets/*.dart` 用 `../../core/...` 引 core（多一层，解析到不存在的 `app/core/`），
     共 3 处；
   * `CatMood.sad` 被 `ai_quiz_page.dart`、`ai_insight_page.dart` 引用，但枚举里没有 `sad`。
   两者都会导致编译失败。已修，并新增静态检查脚本防止复发。
3. **API 用法必须查证，不能凭记忆**：`AudioCache.load()` 初版误传 `AssetSource`，
   靠查 pub.dev 文档发现签名是 `String fileName`。在无法编译的环境下，
   **"查文档"是唯一可靠的验证手段**。
4. **音效不能挂在渲染路径上**：初版曾考虑在 `CatLoader` 播 `thinking`，
   推演后发现它散落 7 处会造成噪音，改为只在显式业务动作（发送请求）触发。

## 八、复现 / 维护

```bash
# 音效资源（改完声音设计后必跑）
python app/tool/gen_audio_assets.py

# 一致性 + 静态健康检查
python app/tool/check_dart_health.py

# 试听：直接打开 web-preview/index.html，点「AI」页发消息即可
```
