# mw-ch04 教学动画 · 缓存设计与三大经典问题

《凯喵Code试炼录》mw-ch04 的成片与全部源码。7 个镜头、合计 **82.8s**，覆盖
【概念原理】S01/S02/S04、【工作实战】S03/S05、【试题交互】S06、【收束】S07。

分镜脚本见 [`../../storyboards/mw-ch04.md`](../../storyboards/mw-ch04.md)（阶段一产物，含逐镜四层解剖）。

## 1. 成片清单（`out/final/`）

| 镜 | 文件 | 时长 | 技术栈 | 内容 | 素材依据 |
|---|---|---|---|---|---|
| S01 | `S01-taxonomy.mp4` | 11.0s | Manim | 请求→缓存→DB 流线，在「未命中」处分岔，落成「存在性 × 失效粒度」二维表的三格 | `concept/01 §①`、`02 §①`、`02 §②` |
| S02 | `S02-bloom.mp4` | 12.3s | Manim | 512 位 bit 数组、3 次哈希置位、`user:999` 假阳性、误判率随 k 的 U 形曲线 | `ex02`/`ex03`、`concept/01 §①` |
| S03 | `S03-breakdown.mp4` | 16.0s | Remotion | 液态玻璃 IDE 里 `GetUser` 逐行敲出；200 并发打穿过期 key（DB 200）→ 加 `singleflight` 后 DB 只 +1 | `ex04`/`ex05`（勘误后：200 vs 1） |
| S04 | `S04-ttl-jitter.mp4` | 10.5s | Manim | 统一 TTL 的 1000 高尖峰 vs `rand(0,300)` 抖动后摊成 31 档、峰值 46（同量尺虚线对照） | `ex07`（1000→46，−95.4%） |
| S05 | `S05-write-order.mp4` | 15.0s | Remotion | 写线程/读线程双栏交错：先删缓存 6/10 残留旧值 vs 先更库 1/10 | `ex09`（同口径同分母 10 种交错） |
| S06 | `S06-quiz.mp4` | 14.0s | Remotion | 三连 BOSS 战：三道真题依次作答，答对削一层血，答错膨胀+掉碎片 | `exercises.json`（答案均 B） |
| S07 | `S07-recap.mp4` | 4.0s | Remotion | 速查卡：问题 → 解法 → 代价 | 全章收束 |

> 与分镜计划的 86s 相比实到 82.8s：S03/S05/S06/S07 完全对齐，概念三镜按成片节奏微调。

## 2. 视觉契约

| 项 | 值 |
|---|---|
| 背景 | `#EBF4FA` → `#F9FBFD` 竖向渐变 |
| 主色 | 冰蓝 `#5DB4E5`、深灰蓝 `#2B3E50` |
| 语义色 | 青绿 `#31D0AA`=正确、柔红 `#F87171`=错误（只用于判定，不做装饰） |
| 字体 | 正文微软雅黑；代码/数值 JetBrains Mono（`fonts/` 随仓库带 ttf） |
| 凯喵 | 右下角头像 + 台词气泡，只在「即将出错 / 结论翻面」时说话 |

Manim 没有真高斯模糊，玻璃感用「白卡 + 低透明度偏移投影 + 细描边」模拟；
Remotion 侧也**去掉了 `backdrop-filter`**（软渲染下太慢且会拖垮逐帧导出）。

## 3. 复现渲染

### 3.1 Manim（S01 / S02 / S04）

```bash
cd manim
env -u PYTHONPATH ../../.venv/Scripts/python.exe -m manim -qm \
    --media_dir ../out/manim_media s04_ttl_jitter.py S04TtlJitter
# 产物：../out/manim_media/videos/s04_ttl_jitter/720p30/S04TtlJitter.mp4
```

前置：`viz/animations/.venv`（Python 3.11 + Manim CE 0.22.1）。**无 LaTeX**，
所以全部用 `Text`（Pango）+ Unicode，禁止 `MathTex`；上下标用 `style.sup()` 手工拼。
`env -u PYTHONPATH` 不能省——宿主 PYTHONPATH 会把 Manim 的 import 顶掉。

### 3.2 Remotion（S03 / S05 / S06 / S07）

```bash
cd remotion
npm ci                      # 首次
npm run render:all          # 四镜直出到 ../out/final/
```

`package.json` 里写死了系统 Edge 路径（本机无 Chrome），换机器时改
`--browser-executable` 或装 `npx remotion browser ensure`。

## 4. 踩过的坑（改代码前先看）

1. **`highlight()` 数字死循环**（`components.tsx`）：③ 分支只识别 `[A-Za-z_]`，
   而 ④ 分支的推进条件用 `!isWord()`、`isWord` 又包含数字 —— 遇到 `5*time.Minute`
   的 `5` 时两个分支都不前进，主线程卡死。表现为 Remotion 在**任意帧**报
   `waitForReady timeout`/"Timed out evaluating page function"，与帧号无关。
   修法：把数字并进 ③ 分支。
2. **`mono()` 不能喂中文**：JetBrains Mono 无 CJK 字形，会渲染成叠字/方框。
   中英混排一律 `mix()`（内部按 ASCII 段切 `t2f`）。
3. **`kaimao(at=...)` 的 `at` 是整组中心**，长台词 + 偏左坐标会把气泡推出画框
   （S04 首版就被裁掉半句）。`style.kaimao()` 现在统一按画框钳制。
4. **`Text.set_max_width()` 是整体缩放，不是自动换行**。缩到 0.7 以下字就糊，
   宁可把 `width` 传大、台词写短。
5. **Manim 时长靠 `run_time` + `self.wait()` 累加**，不是声明式的；改动画要重新数秒。
6. **`Chip` 只装短标签（≤6 汉字）**：像素级量过，12px 时排版宽度正确（8 字 96px，
   胶囊 113px = 字宽 + padding），但白字压在高饱和色底上笔画会粘连，长中文放进去
   就读不清了。状态说明改用「纯文字 + 语义色」或「色点 + 正文」。字号下限取 12px。

## 5. 素材勘误

`examples/` 里 5 个例子存在自相矛盾（顺序模拟冒充并发、`now=50>=100`、
延迟双删分母不同、`ex09` 与 `ex10` 的判脏口径打架），已按「只改 example、真题不动」
的裁决修正，改动与前后对照见 [`../../../content/middleware/mw-ch04/examples/ERRATA.md`](../../../content/middleware/mw-ch04/examples/ERRATA.md)
（原文件留有 `.bak`）。
