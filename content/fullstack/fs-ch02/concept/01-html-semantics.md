# 01 · HTML 语义化：从「机器可读」到「可访问」

## 一、理论根基：语义化不是「好看」，而是「机器可读」

从计算机科学视角，**语义（semantics）** 指标记（markup）携带的*含义*，而非*呈现*。HTML 的设计目标是描述文档结构（类似 LaTeX 的 `\section`/`\emph`），呈现交给 CSS。语义化的本质是：

- **可访问性（a11y）**：屏幕阅读器、键盘导航依赖「结构」而非「视觉」。一个用 `<div class="nav">` 堆出的导航，对辅助技术是「无名方块」；用 `<nav>` 则是「地标（landmark）」。
- **可发现性（SEO）**：爬虫通过标题层级、结构化数据理解页面主题权重。
- **可维护性**：语义标签即文档，团队协作时意图自解释。

> 设计哲学（W3C）：「The `div` element is a generic container. Authors are **strongly encouraged** to use语义 elements ([`article`](https://html.spec.whatwg.org/multipage/sections.html), [`nav`](https://html.spec.whatwg.org/multipage/sections.html), …) instead.」

## 二、实现机制：解析器与「无障碍树」

博士视角要看**浏览器到底构建了什么**：

1. **HTML 解析器**（`html.spec.whatwg.org` 的 "tokenization + tree construction"）把字节流 → 字符 → token → **DOM 树**。解析是**增量、容错**的（著名的「标准错误处理」：未闭合标签自动补）。
2. **可达性树（Accessibility Tree / AXTree）** 是 DOM 的一个*语义投影*：浏览器把每个 DOM 节点映射为 AXNode，赋予 `role`/`name`/`state`。`<nav>` → role=`navigation`；`<main>` → role=`main`；`<article>` → role=`article`。`<div>` 默认 role=`generic`，**不可作为地标**。
3. **地标映射（landmark roles）**：`header`→`banner`（限 body 直接子级）、`nav`→`navigation`、`main`→`main`、`footer`→`contentinfo`、`aside`→`complementary`、`section[aria-label]`→`region`。
4. 语义标签与类的*对象类型*也不同（Blink 实现）：`<div>` 是 `HTMLDivElement`，`<article>` 是 `HTMLElement`，`<a>` 是 `HTMLAnchorElement`——运行时 API 能力随之不同（如 `a.href` 会解析为绝对 URL）。

## 三、工程实践：程序员怎么写

- **地标骨架**：一页一个 `<header><nav><main><footer>`；导航用 `<nav>`；正文一段独立内容用 `<article>`；侧栏用 `<aside>`。
- **标题层级**：`h1`→`h6` 表达大纲层级，不要为「字号」跳级（需要小字号用 CSS）。
- **表单可访问**：`<label for="id">` 关联控件；分组用 `<fieldset><legend>`；必填用 `required` + `aria-required`（详见 ex02）。
- **语义增强**：`time`、`figure/figcaption`、`dl` 等表达特定结构；微数据用 `itemprop` 或 JSON-LD。

## 四、边界与陷阱

- `<section>` 若**无可达名称**（无 `aria-label`/`aria-labelledby`/标题），不会成为 `region` 地标——「用了 section 就有地标」是误解。
- 给元素加 `role` 会**覆盖**其原生语义（如 `<a role="button">` 不再是链接），需自行补键盘交互，易踩可访问性坑。
- 过度嵌套 `<article>`/`<section>` 反而让 AXTree 噪声变大，影响读屏体验。

## 五、可运行示例（结构正确即可，浏览器渲染验证）

```html
<body>
  <header><h1>站点标题</h1></header>
  <nav aria-label="主导航"><ul><li><a href="/">首页</a></li></ul></nav>
  <main>
    <article>
      <h2>文章标题</h2>
      <p>正文段落，<time datetime="2026-09-23">2026-09-23</time> 发布。</p>
    </article>
  </main>
  <aside>相关链接</aside>
  <footer>© 2026</footer>
</body>
```

> 关键结论：语义标签的价值不在「长什么样」，而在「机器（读屏/爬虫/运行时 API）如何理解」。在 DevTools → Accessibility 面板可直观看到 AXTree 中的 role 与 name。

---

## 三视角解析

### 🧑‍💻 程序员视角
- 别用 `div` 堆布局：语义标签（`header/nav/main/article/aside/footer`）自带 landmark，屏幕阅读器与搜索引擎直接受益。
- 表单控件必须配 `<label for>`，图片必须写 `alt`（装饰性图片用 `alt=""`）——这是可访问性的底线要求。
- 在 React/Vue 里同样要写语义标签，组件化不等于放弃语义。

### 🎓 博士生视角
- DOM 与**无障碍树（Accessibility Tree）**是同一文档的两种投影：浏览器把语义标签映射为可导航的 landmark 节点，辅助技术消费的是后者。
- 语义化让文档从「视觉呈现」回归「结构描述」，符合 Web 的分层设计（内容/结构/表现/行为分离）。
- 结构与 SEO 的关系不是玄学：爬虫与辅助技术使用同一套结构信息，语义化同时改善二者。

### 📚 考研者视角
- **408 网络交叉**：HTML 是 HTTP 响应的**应用层**载荷，`Content-Type: text/html` 决定浏览器按 HTML 解析；这是「应用层协议与内容表示」的直接案例。
- 若考软件工程/Web 方向，常考「Web 标准与三层结构」——结构（HTML）/表现（CSS）/行为（JS）分离是标准答案。
- 记忆锚点：**语义化 = 让机器（屏幕阅读器、爬虫）也能理解结构**，不是给开发者看的排版技巧。
