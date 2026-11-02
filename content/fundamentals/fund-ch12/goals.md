# fund-ch12 · 计算机网络：应用层与链路排查

> 学科：`fundamentals`（408 考研 · 计算机网络）
> 前置：`fund-ch11`（计算机网络：传输层与网际层）
> 独立线说明：本章只依赖**同一条线**的 ch11，不依赖任何其他学科。

## 一、这一章要解决的问题

`fund-ch11` 回答的是「数据怎么从 A 主机送到 B 主机」——IP 寻址、路由、TCP 可靠传输与拥塞控制。
本章往上再走一层：**两台主机上的「进程」之间怎么对话**。

具体要回答四件事：

1. 一个 HTTP 请求在 **HTTP/1.1 / 2 / 3** 三代协议里分别是怎么组织的？每一代要修掉上一代的什么毛病？
2. 输入 `https://example.com` 回车之后，到页面渲染出来，**这一秒里发生了什么**？
   这道题是面试高频题，更是排障的骨架——链路里每一环都能被单独验证。
3. HTTPS 的「S」加在哪一步？证书、握手、前向安全各自解决什么问题？
4. 线上出问题时，**用哪些命令、按什么顺序**把范围从「整条链路」收敛到「某一层某一环」？

## 二、学完之后你应该能做到

| 能力 | 验收方式 |
|---|---|
| 说清三代 HTTP 的核心差异与动机 | 能画出 1.1 的队头阻塞、2 的分帧多路复用、3 的 QUIC 流 |
| 完整复述 URL → 渲染的链路 | 至少 10 个环节，每环能说出「失败时怎么验证」 |
| 说清 TLS 握手的密码学取舍 | 能解释为什么必须「非对称协商 + 对称传输」 |
| 区分 Cookie / Session / Token | 能说出各自的存储位置、失效方式与安全边界 |
| 按分层定位网络故障 | 给一个「网页打不开」，能在 5 分钟内收敛到层 |

## 三、本章结构

| 文件 | 内容 |
|---|---|
| `concept/01-http-evolution.md` | HTTP/1.1 → 2 → 3：队头阻塞、多路复用、HPACK、QUIC |
| `concept/02-dns-and-url-to-render.md` | DNS 递归/迭代与缓存；从 URL 到渲染全链路 |
| `concept/03-https-and-tls.md` | 混合加密、TLS 1.2/1.3 握手、证书链、前向安全 |
| `concept/04-session-cors-and-troubleshooting.md` | Cookie/Session/Token、同源与 CORS、分层排查命令 |
| `pitfalls.md` | 10 个高频踩坑（含 408 易错口径） |
| `examples/` | 10 个 Python 模拟示例（DNS、HTTP 解析、NAT、ARP、CSMA/CD、DHCP、TLS、MAC 自学习…） |
| `exercises.json` | 8 题：基础 6 + 算法 2 |
| `interview.json` | 6 条面经 |
| `project.json` | 一个「迷你 HTTP/DNS 协议栈 + 排障剧本」项目 |

## 四、动手实践（建议顺序）

1. **抓一次真包**：`curl -v https://example.com`，逐行对照本章的握手流程；
   再用 `dig +trace example.com` 观察迭代查询的完整链条。
2. **手写解析器**：用 Python 把一段原始 HTTP 响应文本解析成 `(状态行, 头字段字典, 正文)`。
3. **模拟退化场景**：在 `examples/` 的 DNS 模拟器里把某个权威服务器标记为超时，
   观察解析器如何回退到下一个 NS，理解「为什么 DNS 常有 5 秒卡顿」。
4. **排障剧本**：给自己的项目写一份「网页打不开 / 接口超时 / 证书报错」三套逐层排查清单。

## 五、自检清单

- [ ] 我能说出 HTTP/2 修掉了 1.1 的哪一种队头阻塞，而 HTTP/3 修掉的是**另一种**
- [ ] 我能说出 DNS 递归查询与迭代查询分别发生在**哪两端**之间
- [ ] 我能解释「为什么有了非对称加密还要用对称加密」
- [ ] 我能说出 Cookie 的 `HttpOnly` / `Secure` / `SameSite` 各防什么
- [ ] 我能说出 `ping` / `traceroute` / `netstat` / `tcpdump` 分别工作在**哪一层**
## 本章 GitHub 学习路线（按阅读顺序）

> ★ 为 **2026-10-27** 的 GitHub API 快照（已逐条验证仓库存在）。
> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 376,373 | §4.2 | 讲「CDN 与边缘节点」时读 `solutions/` 的 CDN 设计：把内容推到离用户最近的节点，本质是「用空间换 RTT」，与本章「时延带宽积」的量化视角互补 |
| 2 | [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 363,641 | §3.2 | 讲「链路层排障」时读 README 的 Networking 练习：`ping`/`traceroute`/`curl -v` 各自回答什么问题，与本篇「分层排查」的顺序一致 |
| 3 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186,408 | §2.1 | 讲「HTTP 与 DNS」时读 `docs/计算机网络/` 的应用层篇：DNS 递归/迭代查询的差别、HTTP 缓存头的组合，配了抓包示例 |

## 本章 B 站视频路线（与 GitHub 互补）

> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放。
> 分工：**B 站给直觉与推导，GitHub 给源码与工程取舍**；两者冲突时以源码为准。顺序：主线课定位知识点 → 专题课补推导 → 论文精读补出处。

| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 数据结构（考研）<br><sub>王道计算机教育</sub> | [BV1b7411N798](https://www.bilibili.com/video/BV1b7411N798/) | 全章 | 主线：复杂度 → 线性表 → 栈队列 → 树 → 图 → 查找 → 排序；每个结构都配手写代码与大题模板；看完回 `ex01`（DNS 递归/迭代查询与分层缓存、TTL）核对 |
| 2 | 王道 · 计算机网络（考研）<br><sub>王道计算机教育</sub> | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | 全章 | 自顶向下或按层都行：TCP 三次握手/四次挥手、拥塞控制、IP 与路由、HTTP；看完回 `ex02`（解析原始 HTTP 报文）核对 |
| 3 | 王道 · 操作系统（考研）<br><sub>王道计算机教育</sub> | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | §4.1 Cookie / Sess… | 进程与线程、调度、同步互斥与死锁、内存管理与虚拟内存、文件系统与 IO；看完回 `ex03`（状态码语义与分类判定（含常见面试陷阱））核对 |
| 4 | 王道 · 计算机组成原理<br><sub>王道计算机教育</sub> | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | 全章 | 数据表示与运算、存储层次与 Cache、指令系统与 CPU 数据通路、总线与 IO；看完回 `ex04`（NAT 地址转换表）核对 |

## 本章配套论文与书（溯源用）

> 公式与结论的出处。只查对应章节，不必通读整本。

| # | 文献 / 章节 |
|---|---|
| 1 | 《深入理解计算机系统（第 3 版）》Bryant & O'Hallaron |
| 2 | 《算法导论（第 4 版）》Cormen 等 |
| 3 | 《计算机网络：自顶向下方法（第 8 版）》Kurose & Ross |

> 图例：`§3.2` = 本章第 3 篇 concept 文件的第 2 节。共 3 个 GitHub 来源、4 条 B 站视频、3 条文献；
> 全部链接由 `scripts/collect_links.py` + `scripts/audit_sources.py` 定期复核，失效链接会被审计器标红。
