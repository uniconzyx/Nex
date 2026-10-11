# fund-ch04 · 图

> 先修：fund-ch03（树与二叉树）。衔接：fund-ch05（查找与哈希）、fund-ch06（排序与复杂度）。
> 面试权重：★★★★★（图论是算法面试的分水岭，拓扑排序 / 最短路 / 并查集几乎必考）

## 本章目标

学完你应该能：

1. **在三种存储结构间做工程取舍**：邻接矩阵 / 邻接表 / 十字链表，说清各自的空间量级与「查边」代价，
   并能从「稠密 vs 稀疏」「需要反向边吗」两个维度给出选择依据。
2. **把 DFS 与 BFS 还原成栈与队列**：理解二者不是两种「遍历写法」，而是两种**不同的搜索序**，
   因而分别适合连通性/回溯与无权最短路。
3. **证明 Dijkstra 的贪心正确性，并说清它为什么不能处理负权**：能举出反例，知道何时改用
   Bellman-Ford、何时用 Floyd、何时应先做 Johnson 重赋权。
4. **用并查集把动态连通性压到近似 O(1)**：理解路径压缩 + 按秩合并为什么能把最坏 O(log n)
   压成反阿克曼函数级别，以及它为什么是 Kruskal 的正确搭档。
5. **写出拓扑排序的两种形式**（Kahn 入度法 与 DFS 后序逆序），并能用它们判环、排课、解依赖。

## 复杂度目标（面试要能脱口而出）

| 算法 | 时间 | 空间 | 备注 |
|---|---|---|---|
| DFS / BFS（邻接表） | O(V + E) | O(V) | 邻接矩阵退化为 O(V²) |
| 拓扑排序 Kahn | O(V + E) | O(V) | 入度为 0 的队列 |
| Dijkstra（朴素） | O(V²) | O(V) | 稠密图反而更好 |
| Dijkstra（二叉堆） | O((V+E) log V) | O(V+E) | 稀疏图主流 |
| Bellman-Ford | O(VE) | O(V) | 可判负环 |
| Floyd | O(V³) | O(V²) | 全源，V ≤ 几百 |
| Kruskal | O(E log E) | O(V+E) | 并查集主导 |
| Prim（堆） | O((V+E) log V) | O(V+E) | 稠密图可用朴素 O(V²) |


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
