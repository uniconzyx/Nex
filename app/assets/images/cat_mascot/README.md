# CppCat 缅因猫形象资源（assets/images/cat_mascot/）

> 品种：**缅因猫（Maine Coon）** · 名字：**小蓝猫 / CppCat** · 配色：银灰底色 + 白色胸前毛 + 主蓝 `#3B82F6`

## 文件清单（8 种表情，文件名即 `CatMood.name`）

| 文件 | 表情 | 使用场景 |
|---|---|---|
| `happy.webp` | 开心 | 首页问候、通用 |
| `thinking.webp` | 思考 | 编译中、AI 思考 |
| `confused.webp` | 疑惑 | 编译失败、答错（委屈/安慰话术） |
| `cheer.webp` | 鼓励 | 鼓励语 |
| `celebrate.webp` | 庆祝 | AC 通过、成就解锁（竖大拇指） |
| `comfort.webp` | 安慰 | 错题本、失败兜底（拍拍肩膀） |
| `sleeping.webp` | 睡觉 | 空闲态、待机 |
| `loading.webp` | 加载 | 加载占位（同时优先用 Lottie） |

## 制作规范（给美术 / 图像生成的指令）

- **格式**：优先 WebP（更小），保留 PNG 透明通道备选；加载动画另出 Lottie JSON 放 `assets/cat/`。
- **极客属性**：佩戴**半透明蓝色边框**程序员眼镜（`#3B82F6` 描边，opacity≈0.75）。
- **特征**：耳尖猞猁毛、大而圆的蓝眼睛、毛发浓密蓬松、白色胸前毛。
- **色调融合**：毛发蓝灰色必须与主蓝 `#3B82F6`、背景白 `#F8FAFC` 高度融合。
- **深色模式**：提供在 `#0F172A` 背景下的发光边缘版本（或运行时用 `CppCatMascot(glow:true)` 加 `box-shadow`）。
- **尺寸**：建议 512×512 起，组件按 `size` 缩放；保持圆形可裁切构图，便于发光光晕。

## 接入方式（主人上传的图片，落盘即生效）

把图片放到本目录即可，组件会自动加载：

- **单张主图**：命名为 `maine_coon.png`（或 `.webp`），在组件里用 `CppCatMascot(imagePath: "assets/images/cat_mascot/maine_coon.png")` 或 `MaineCoonAssistant(imagePath: ...)` 显式指定。
- **8 表情分离图**：按上表命名 `<mood>.webp`，`CppCatMascot(mood: ...)` 会自动找对应文件。
- **优先级**：`imagePath` 显式路径 > `<mood>.webp` 自动命名 > 内置 CustomPainter 兜底。
- **透明通道**：建议 PNG/WebP 带透明背景，圆形裁切（`ClipOval`）后自动融入卡片。
- **蓝光融合**：`glow:true`（默认）时自动叠加主蓝 `#3B82F6` 微光 / 深色模式青蓝 `#22D3EE` 发光，与 APP 主色调融合。

> 交互组件 `MaineCoonAssistant`（见 `lib/widgets/cpp_cat.dart`）额外提供：状态→表情自动映射（`AssistantStatus`）、点击猫咪弹出弹跳提示气泡。

> 当前为占位骨架：本目录尚无真实图片，运行时显示 CustomPainter 缅因猫。
> 放入图片后重新 `flutter pub get && flutter run` 即自动启用真实形象。

## 加载逻辑（已写好，无需改）

`lib/widgets/cpp_cat.dart` 的 `CppCatMascot`：
1. 先加载显式 `imagePath` 或 `assets/images/cat_mascot/<mood>.webp`；
2. 资源缺失或「减少动效」开启 → 回退内置 `CustomPainter` 缅因猫（与 web 演示版同形象）；
3. 任何加载失败 `errorBuilder` 兜底，不崩溃。
