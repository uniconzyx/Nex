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


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 373461 | 系统设计入门：性能、一致性、可用性与面试题（408 之上的系统视野） |
| [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 362479 | 完整的计算机科学自学计划：数据结构、算法、OS、网络全覆盖 |
| [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186393 | 中文技术面试必备：操作系统、计算机网络、组成原理、算法、数据库 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 青岛大学 · 王卓 数据结构与算法 | [视频](https://www.bilibili.com/video/BV1nJ411V7bd/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 王道考研 · 计算机组成原理 | [视频](https://www.bilibili.com/video/BV1ps4y1d73V/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 哈工大 · 李治军 操作系统 | [视频](https://www.bilibili.com/video/BV1d4411v7u7/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 湖南科技大学 · 计算机网络微课堂 | [视频](https://www.bilibili.com/video/BV1c4411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 清华 · 邓俊辉 数据结构与算法 | [视频](https://www.bilibili.com/video/BV1jt4y117KR/) | 本学科配套视频，建议结合本章示例与习题观看 |
