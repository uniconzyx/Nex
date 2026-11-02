# §5 fund-ch04 实战手记：凯喵带你把图论用「错」

> 前四节把存储、DFS/BFS、最短路、并查集讲透了。这一节凯喵把算法面试里图题最容易 WA / TLE / 栈溢出的 12 个现场搬出来——建图方式、边界条件、递归爆栈，全是细节。

### 现场一：邻接表用 ArrayList 还是数组，先想清空

凯喵写 BFS 用 `List<Integer>[] g = new ArrayList[n]`，结果上一组测试用例的残留边混进下一组，答案错乱。图结构每题要**重新建**，不能复用旧容器。竞赛里常用 `List<List<Integer>>` 每轮 new，或 `head[]` + `edge[]` 静态邻接表。

```java
int n = 5;
List<Integer>[] g = new ArrayList[n];
for (int i = 0; i < n; i++) g[i] = new ArrayList<>();  // ✅ 每题重建
// ❌ 复用上次 new 出来的 g，残留边污染本次结果
g[0].add(1); g[1].add(2);
```

### 现场二：BFS 最短路要在「入队时」设距离

凯喵第一次写 BFS 求最短路，把 `dist[v] = dist[u] + 1` 写在**出队**时，结果起点 dist 设成 -1，相邻点算成 0，整张图距离全错。正确：在**入队**那一刻就定下距离，保证首次到达即最短；起点 dist 初始化为 0。

```java
int[] dist = new int[n];
Arrays.fill(dist, -1);
Queue<Integer> q = new ArrayDeque<>();
dist[0] = 0; q.offer(0);
while (!q.isEmpty()) {
    int u = q.poll();
    for (int v : g[u]) {
        if (dist[v] == -1) {
            dist[v] = dist[u] + 1;   // ✅ 入队时定距离
            q.offer(v);
        }
    }
}
```

### 现场三：DFS 递归爆栈，十万点要改显式栈

凯喵在 V=10^5 的链状图上用递归 DFS，直接 `StackOverflowError`。JVM 默认栈深约几千，长链递归必爆。解法：① 非递归用显式栈；② 或调大 `-Xss`；③ 拓扑/连通这类改用 BFS 或并查集。面试时先问数据规模再决定写法。

```java
// ❌ 链状图递归爆栈
void dfs(int u) { for (int v : g[u]) dfs(v); }

// ✅ 显式栈版本
Deque<Integer> st = new ArrayDeque<>();
st.push(0);
while (!st.isEmpty()) {
    int u = st.pop();
    for (int v : g[u]) if (!vis[v]) { vis[v] = true; st.push(v); }
}
```

### 现场四：有向图判环别用 bool visited

凯喵用 `boolean[] vis` 判有向图环，结果一个 DAG 被误判成有环。原因：bool 分不清「当前递归栈上的祖先」和「已完成的兄弟分支」。必须用**三色标记**：白=未访问、灰=递归栈中、黑=已完成；遇到灰色邻居才是真环。

```java
int[] color = new int[n]; // 0白 1灰 2黑
boolean dfs(int u) {
    color[u] = 1;
    for (int v : g[u]) {
        if (color[v] == 1) return true;      // ✅ 灰=祖先=有环
        if (color[v] == 0 && dfs(v)) return true;
    }
    color[u] = 2;
    return false;
}
```

### 现场五：Kruskal 收边前必须判环

凯喵写 Kruskal 直接 `for edge: mst.add(edge)`，得了一棵带环的「树」。正确：先按权重排序，用并查集 `find(u) != find(v)` 才收下并把两边并起来，否则就不是最小生成树（甚至不是树）。

```java
edges.sort(Comparator.comparingInt(e -> e.w));
int taken = 0, cost = 0;
for (Edge e : edges) {
    int ru = find(e.u), rv = find(e.v);
    if (ru != rv) {              // ✅ 判环：不在同一集合才收
        union(ru, rv);
        cost += e.w;
        if (++taken == n - 1) break;
    }
}
```

### 现场六：Dijkstra 不能处理负权，别硬上

凯喵拿到一道带负权边的题，惯性套 Dijkstra 得到错误最短路。Dijkstra 的贪心正确性依赖「一旦确定了某点最短距离就不再被更新」，负权会破坏这个前提。负权用 Bellman-Ford（还能判负环）；全源用 Floyd；稀疏正权用堆优化 Dijkstra。

```java
// ❌ 有负权还用 Dijkstra -> 错
// ✅ 负权改用 Bellman-Ford
for (int i = 0; i < n - 1; i++)
    for (Edge e : edges)
        dist[e.v] = Math.min(dist[e.v], dist[e.u] + e.w);
// 第 n 趟还能松弛 -> 存在负环
```

### 现场七：邻接矩阵在 V=10^5 时直接 MLE

凯喵想「省事」用 `int[][] g = new int[V][V]` 存图，V=10^5 需要 10^10 个 int，光矩阵就 40GB，OOM。稀疏图（E 接近 V）一律邻接表或 CSR；矩阵只在 V ≤ 1000 且稠密（如 Floyd）时才用。

```java
// ❌ 10^5 顶点 -> 40GB，MLE
// int[][] g = new int[100000][100000];
// ✅ 稀疏图用邻接表
List<List<Integer>> g = new ArrayList<>();
```

### 现场八：拓扑排序遇到环要能识别

凯喵写 Kahn 拓扑排序，图里其实有环，结果队列空了但只排了部分点，输出残缺。正确：Kahn 结束后若入队点数 < V，说明有环（排不完）；DFS 后序逆序法遇到回边也直接判环。排课 / 编译依赖场景必须处理环。

```java
int[] indeg = new int[n];
for (int u = 0; u < n; u++) for (int v : g[u]) indeg[v]++;
Queue<Integer> q = new ArrayDeque<>();
for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
int cnt = 0;
while (!q.isEmpty()) {
    int u = q.poll(); cnt++;
    for (int v : g[u]) if (--indeg[v] == 0) q.offer(v);
}
boolean hasCycle = cnt < n;   // ✅ 排不满就是有环
```

### 现场九：并查集不路径压缩，退化成 O(n)

凯喵的并查集只 `parent[p] = find(q)` 没压缩，10^5 次查询 TLE。标准写法：find 时把路径上节点直接挂到根（路径压缩）+ 按秩/按大小合并，单次接近 O(1)，总复杂度 O(α(n))。

```java
int find(int x) {
    if (parent[x] != x) parent[x] = find(parent[x]); // ✅ 路径压缩
    return parent[x];
}
void union(int a, int b) {
    a = find(a); b = find(b);
    if (a == b) return;
    if (rank[a] < rank[b]) parent[a] = b;           // ✅ 按秩合并
    else { parent[b] = a; if (rank[a] == rank[b]) rank[a]++; }
}
```

### 现场十：双向 BFS 没判「两边相遇」就停

凯喵写双向 BFS 求最短，只在「正向队空」就停，漏掉两边相遇的情况，距离算错。正确：从两端交替扩展，当某步扩展到的节点**已在另一端 visited** 时，两边距离相加即答案；要维护两套 dist 和两套 visited。

```java
// 正向 q1 / 反向 q2，各一套 dist1/dist2
if (dist2.containsKey(v)) return dist1.get(u) + dist2.get(v) + 1; // ✅ 相遇
```

### 现场十一：无向图存边要存两条，有向只存一条

凯喵在「无向」图上只 `g[u].add(v)` 没加反向边，BFS 只能单向走，连通性全错。无向边是双向的，建图务必 `g[u].add(v); g[v].add(u)`；有向图才只存一条。建完图先确认边数符合预期。

```java
// 无向图
g[u].add(v); g[v].add(u);   // ✅ 存两条
// 有向图
g[u].add(v);                // 只存一条
```

### 现场十二：重边和自环别忘了特判

凯喵的题里出现重边（u→v 多条）和自环（u→u），最短路径被自环或重复边干扰。Dijkstra 允许重边自动取最小，但 Bellman-Ford 循环次数要够；自环在无向图里可能影响度数/拓扑判环，建图后先去重或特判。

```java
// 自环对最短路无意义，建图时可跳过
if (u == v) continue;
// 重边：邻接表允许保留，松弛时自然取最小；或先排序去重
```

> 凯喵总结：图论的坑 90% 在「建图」和「边界」——容器没重建、距离入队才设、递归爆栈、bool 判环、负权套 Dijkstra、矩阵爆内存。把这 12 个现场刻进手感，面试图题少 WA 一半。

## 三视角解析
### 🧑‍💻 程序员视角
凯喵写 BFS 求最短路，把 `dist[v] = dist[u] + 1` 写在出队时，结果同一个点被反复覆盖成更大的值——正确做法是**入队时**就定死距离，出队只负责扩展。DFS 递归在十万结点的链式图上直接爆栈，只能改显式栈；但显式栈要注意「入栈顺序与访问顺序相反」，想要左子树先访问就得先压右子树。Dijkstra 遇到负权边会给出错误答案，不是「精度问题」而是算法前提被破坏——松弛的有效性依赖「已确定的最短路不会再被更短的路径推翻」，负权让这个不变量失效，此时只能用 Bellman-Ford。

### 🎓 博士生视角
图的表示决定了算法的复杂度常数：邻接矩阵 O(V²) 空间、O(1) 判边；邻接表 O(V+E) 空间、O(deg) 判边。稠密图用矩阵、稀疏图用表，这不是风格问题而是渐进复杂度问题。最短路算法的分层很清晰：无权图 BFS 是 O(V+E)；非负权 Dijkstra 用二叉堆 O((V+E)logV)、用斐波那契堆 O(E+VlogV)；含负权用 Bellman-Ford O(VE)，其队列优化版 SPFA 平均快但最坏仍 O(VE)；全源最短路 Floyd 是 O(V³) 的动态规划，状态转移 `d[i][j] = min(d[i][j], d[i][k]+d[k][j])` 的 k 必须在外层，这是正确性的关键。

### 📚 考研者视角
408 图论考「存储 + 遍历 + 两类经典算法」：
1. **存储结构**：邻接矩阵与邻接表的空间、适合场景；十字链表（有向图）、邻接多重表（无向图）的结构图要能画。
2. **遍历**：给邻接表写出 DFS/BFS 序列，注意「按编号从小到大」的约定，序列不唯一但题目会给规则。
3. **最小生成树**：Prim 从点出发 O(V²)、Kruskal 从边出发 O(ElogE)，要能说清「稠密图用 Prim、稀疏图用 Kruskal」。
4. **最短路径**：Dijkstra 的手算过程（每次选最小未确定点，松弛其邻边）、Floyd 的三重循环顺序、拓扑排序的入度法。
5. **关键路径**：求最早/最迟开始时间与时间余量，余量为 0 的活动是关键活动。
