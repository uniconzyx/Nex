# fund-ch18 学习目标：并查集与字符串高级

> 一句话引出：如何 O(α(n)) 回答"这两个点连通吗"？模式匹配如何跳过无效比对？

## 一、知识目标
1. 掌握并查集（Disjoint Set Union）的父指针森林表示，理解 find 路径压缩与 union 按秩(rank)/按大小(size)合并两大优化及其对树高的约束。
2. 理解并查集单次操作近乎常数（反阿克曼 α(n)）的均摊复杂度，能解释"为什么工程上可视为 O(1)"。
3. 掌握 KMP 的 next / nextval 数组定义、手推方法与匹配过程，理解其本质是"用失配信息跳过已匹配前缀"。
4. 了解 BM（坏字符/好后缀）、字符串哈希 Rabin-Karp、Trie 字典树与 AC 自动机的基本思想与典型应用。
5. 说清并查集、KMP 与 ch02 串、ch03 树、ch04 图的关系：并查集维护等价类划分（图的连通分量），KMP/Trie 是串的进阶结构。

## 二、能力目标
- 能徒手写出带路径压缩 + 按秩合并的并查集，并用于连通分量计数、Kruskal 判环、冗余连接等问题。
- 能对任意模式串手推 next 与 nextval，并写出 KMP 匹配主流程。
- 能为"大规模文本去重 / 前缀匹配 / 敏感词过滤"等真实场景选型并落地（哈希、Trie、AC 自动机）。

## 三、三视角导航
| 视角 | 本章重点 |
|---|---|
| 🧑‍💻 程序员 | 用并查集做微服务调用环检测；用 Trie 做前缀匹配/敏感词过滤；用 Rabin-Karp 做大规模文本去重 |
| 🎓 博士生 | 反阿克曼函数的势函数证明、KMP 与有限自动机的等价性、AC 自动机 fail 指针的 DFA 实质 |
| 📚 考研者 | 408 高频：并查集时间复杂度、KMP next 手推、Trie 应用、并查集与图的连通性联系 |

## 四、前置
本章前置：fund-ch02（栈队列串）、fund-ch03（树）、fund-ch04（图）。

## 本章 GitHub 学习路线（按阅读顺序）
> ★ 为 GitHub 星数（2026-10-28 经 GitHub REST API 实取，非估算）。

| # | 仓库 | ★ | 对应本章 | 读什么 / 怎么用 |
|---|---|---|---|---|
| 1 | [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | 376373 | §1.1 动态连通性：只合不拆的集合问题为什么值得专门造结构 | 读 README 里「一致性 / 分区」相关段落：并查集回答的「两个点是否连通」，在分布式里就是「两个节点是否在同一分区」——本章强调「只合不拆」这个前提，正是分布式分区一旦合并就很难安全拆分的原因；对照 §4.2「BM 的坏字符/好后缀规则与 AC 自动机的失配跳转」可以看出，两者都在利用「已经知道的信息」避免从头再来 |
| 2 | [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) | 363641 | §2.1 朴素匹配失配后为什么要回退整段：KMP 想省掉的到底是什么 | 读 README 的 Algorithmic complexity 与 String searching 相关条目：它把 KMP 放在「已匹配前缀可复用」这一族里，与 Rabin-Karp 的「滚动哈希」并列；本章 §3.2「Rabin-Karp 滚动哈希与 Trie」正是这条并列线的另一半——KMP 复用「结构」、RK 复用「计算」，两条路都在绕开「每换一个起点就重比一遍」 |
| 3 | [CyC2018/CS-Notes](https://github.com/CyC2018/CS-Notes) | 186408 | §2.2 next 数组就是公共前后缀长度表，以及它的两种下标口径 | 读 `docs/算法/` 字符串一节：它给了 next 数组的逐位推演，适合考前对照手推三遍固化手感；但要注意教材的两种口径（next[0]=-1 与 next[1]=0）在代码里差一位，本章 §2.2 专门标了这件事——换口径而不换循环边界，就会在第一个字符失配时越界访问 |
| 4 | [torvalds/linux](https://github.com/torvalds/linux) | 254007 | §1.2 按秩合并与路径压缩：两行优化如何把复杂度压到反阿克曼 | 读 `lib/union_find.c` 与 `mm/` 里基于并查集的结构：看路径压缩与按秩合并如何在生产代码里被实现——内核的合并规则是「小秩挂大秩」，且为了并发安全把「按秩」弱化成「按大小」；本章 §1.1 的「只合不拆」在这里体现为：没有 `split` 接口，所以压缩后的路径不必担心被拆回去 |
| 5 | [redis/redis](https://github.com/redis/redis) | 77127 | §3.2 Rabin-Karp 滚动哈希与 Trie：把「比较」换成「计算」和「走树」 | 读 `src/rax.c`：Redis 的 radix tree 就是压缩 Trie，看它如何做前缀匹配与内存压缩——比教科书 Trie 省一个数量级；本章 §3.1「一个模式对不上时，多模式与前缀检索该换什么结构」的答案是：单模式用 KMP/BM、多模式用 AC 自动机、前缀查询用 Trie、而 Redis 的 rax 把「前缀」与「有序遍历」两件事压进同一棵树 |
| 6 | [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | 225745 | §2.2 next 数组就是公共前后缀长度表，以及它的两种下标口径（对照实现） | 读 `data_structures/disjoint_set/` 与 `strings/` 下的 KMP：短小可直接跑，用来对照自己写的版本；这里的价值在于「同一算法用 Python 写一遍」会把教材里靠指针操作隐藏的边界暴露出来——比如 next 数组的构建里 `j` 回退到 -1 时该做什么，Python 版一般用 `j = -1` 显式判断，比 C 版的位移技巧更容易读懂 |

## 本章 B 站视频路线
| # | 系列 / UP 主 | 视频 | 对应本章 | 看什么 |
|---|---|---|---|---|
| 1 | 王道 · 数据结构（考研） | [BV1b7411N798](https://www.bilibili.com/video/BV1b7411N798/) | 全章 | KMP 与并查集大题 |
| 2 | 王道 · 计算机组成原理 | [BV1BE411D7ii](https://www.bilibili.com/video/BV1BE411D7ii/) | 全章 | 体系关联 |
| 3 | 王道 · 操作系统（考研） | [BV1YE411D7nH](https://www.bilibili.com/video/BV1YE411D7nH/) | 全章 | 进程集合类比 |
| 4 | 王道 · 计算机网络（考研） | [BV19E411D78Q](https://www.bilibili.com/video/BV19E411D78Q/) | 全章 | 路由集合类比 |

## 本章配套论文与书
| # | 文献 / 章节 |
|---|---|
| 1 | 《算法导论（第 4 版）》Cormen 等 |
| 2 | 《数据结构（严蔚敏）》严蔚敏 |
| 3 | 《柔性字符串匹配》Crochemore 等 |
