# assets/cat —— CppCat Lottie 资源放置约定

每个表情一个 Lottie JSON，文件名即表情名：

| 文件 | 表情 | 触发场景 |
|---|---|---|
| `happy.json` | 开心（默认） | 首页问候、普通对话 |
| `thinking.json` | 思考 | 编译中、AI 生成中 |
| `confused.json` | 疑惑 | 编译失败、答错 |
| `cheer.json` | 加油 | 每日首次打开、任务开始 |
| `celebrate.json` | 庆祝 | AC、成就解锁 |
| `comfort.json` | 安慰 | 连续失败、错题本 |
| `sleeping.json` | 睡觉 | 长时间空闲 |
| `loading.json` | 加载 | 页面加载 |

动作要求（PRD §14）：眨眼、摇尾巴、点头、跳跃、打勾、敲代码。
制作建议：SVG 分层导出 → After Effects + Bodymovin 出 Lottie；
或先用占位资源（如 LottieFiles 搜索 "cat coding"）跑通管线后替换正式形象。

**资源缺失时**：`CppCat` 组件自动回退到内置 SVG 简笔画（蓝白配色一致），不会崩溃。
