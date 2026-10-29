/* 由 scripts/gen_tracks.py 从 content/_tracks/reexam.json 生成，请勿手改。 */
/* eslint-disable */
export interface ReexamInterviewQuestion { q: string; tip?: string; }
export interface ReexamInterviewCategory { category: string; desc: string; questions: ReexamInterviewQuestion[]; }
export interface ReexamInterview { name: string; desc: string; categories: ReexamInterviewCategory[]; }
export interface ReexamMachineTest {
  id: string;
  title: string;
  university: string;
  year: number;
  module: string;
  scene: string;
  framework: string;
  algorithm: string;
  code: string;
}
export interface ReexamDef {
  trackId: string;
  name: string;
  interview: ReexamInterview;
  machineTests: ReexamMachineTest[];
}

export const REEXAM: ReexamDef = {
  "trackId": "reexam",
  "name": "考研复试 · 面试与机试",
  "interview": {
    "name": "复试专属面试问题（非八股）",
    "desc": "复试面试 ≠ 就业八股。导师考察的是「研究潜力 / 表达逻辑 / 英语 / 专业发散」，问题更开放、更个人化。",
    "categories": [
      {
        "category": "研究计划",
        "desc": "导师最看重：你读研想做什么、为什么、是否匹配他的方向。",
        "questions": [
          {
            "q": "你读研最想研究的方向是什么？为什么选它？",
            "tip": "要具体（如「图神经网络在推荐系统的冷启动」），切忌「我对 AI 感兴趣」这种空话；讲清痛点与你的动机。"
          },
          {
            "q": "你最近读过哪篇论文？它解决了什么问题、方法创新在哪？",
            "tip": "准备 1-2 篇精读论文，能讲清「输入/输出/核心方法/实验结论」，别只背摘要。"
          },
          {
            "q": "你的研究计划与我的方向（或实验室方向）怎么契合？",
            "tip": "提前读导师近 3 年论文/项目，把你的兴趣锚定到他的工作线上，展现「做过功课」。"
          },
          {
            "q": "如果选题做不出来，你的备选方案是什么？",
            "tip": "导师想看风险意识与 Plan B，体现科研韧性而非盲目自信。"
          }
        ]
      },
      {
        "category": "项目陈述",
        "desc": "把你做过的项目讲清楚：难点、你的角色、量化结果。",
        "questions": [
          {
            "q": "讲一个你最有成就感的项目，你的角色和贡献是什么？",
            "tip": "用 STAR：背景-任务-行动-结果，量化指标（QPS 提升 X%、延迟降 Yms）比「做了很多」更有力。"
          },
          {
            "q": "这个项目最大的技术难点是什么？你怎么攻克的？",
            "tip": "选真难点，展示排查链路（现象→假设→验证→定位），别编一个你讲不深的坑。"
          },
          {
            "q": "这个项目如果重做，你会怎么改进架构？",
            "tip": "体现复盘与架构演进思维，展示你不止会写业务代码。"
          },
          {
            "q": "你遇到过最难复现的 Bug 是什么？怎么定位的？",
            "tip": "线上问题、偶发卡顿、并发竞态都是好素材，重点在定位方法论。"
          }
        ]
      },
      {
        "category": "英语口语",
        "desc": "自我介绍、专业文献朗读翻译、日常与学术问答。",
        "questions": [
          {
            "q": "Please introduce yourself in English (1-2 min).",
            "tip": "背熟 3 段：本科学校/专业、项目亮点、读研动机；语速稳比华丽词藻重要。"
          },
          {
            "q": "Translate this paragraph about your major into Chinese.",
            "tip": "遇到生词别卡壳，按意群猜译；平时多读英文 abstract 练长句。"
          },
          {
            "q": "Why do you choose to pursue a master's degree?",
            "tip": "学术导向（research interest）比「好就业」更受导师欢迎。"
          },
          {
            "q": "Describe your hometown / your favorite course.",
            "tip": "准备 5 个万能话题词库，灵活组合，避免临场组织语言。"
          }
        ]
      },
      {
        "category": "专业素养",
        "desc": "导师追问的发散/批判性问题，考察思维而非记忆。",
        "questions": [
          {
            "q": "你怎么看大模型对你们方向的影响？",
            "tip": "展现「理解技术边界 + 有自己的判断」，不盲目捧杀也不排斥。"
          },
          {
            "q": "你过去一年里，哪次失败让你成长最多？",
            "tip": "真实失败 + 反思 + 行动改变，比成功故事更打动人。"
          },
          {
            "q": "如果给你一台 8 核机器和一个 CPU 密集任务，你怎么并行优化？",
            "tip": "考察工程直觉：分片、无锁、Cache 友好、I/O 与计算重叠。"
          },
          {
            "q": "你认为一个优秀的工程师最重要的特质是什么？",
            "tip": "结合经历谈（如「把复杂问题拆解清楚的能力」），别背教科书定义。"
          }
        ]
      }
    ]
  },
  "machineTests": [
    {
      "id": "pat-b1003-tree",
      "title": "由前序与中序遍历重建二叉树并输出后序",
      "university": "浙江大学 PAT",
      "year": 2018,
      "module": "数据结构 · 树",
      "scene": "工作中：后端要把一份「声明顺序 + 依赖顺序」的配置（如类 XML 的标签树）解析成内部对象。本质是「前序(声明序)+中序(依赖序)→后序(逆初始化序)」的镜像：先拿到两个序列，重建出执行 DAG，再逆序回写，确保子节点先于父节点就绪。",
      "framework": "① 大框架：输入 N + 前序序列 + 中序序列 → 递归定位根（前序首元素）→ 在中序找根下标 k，左子树 [0,k)、右子树 [k+1,) → 递归重建 → 后序遍历压栈输出。边界：N=0 直接返回空；两序列长度不一致或值不匹配视为非法输入。",
      "algorithm": "② 核心算法思想：前序首元素即当前子树根；在中序里线性扫描定位根下标 k，左子树节点数 = k-il。递归时前序区间与中序区间要同步偏移：左子树前序 [pl+1, pl+left]、中序 [il, k-1]；右子树前序 [pl+left+1, pr]、中序 [k+1, ir]。后序在「左右都返回后」再压根，天然得到后序。",
      "code": "#include <iostream>\n#include <vector>\nusing namespace std;\n\nvector<int> pre, in, post;\n\n// 递归重建：pl/pr 前序区间，il/ir 中序区间\nvoid build(int pl, int pr, int il, int ir) {\n  if (pl > pr) return;            // 空子树直接返回\n  int root = pre[pl];             // 前序第一个是当前根\n  int k = il;\n  while (in[k] != root) k++;      // 在中序里找到根的位置\n  int left = k - il;              // 左子树节点个数\n  build(pl + 1, pl + left, il, k - 1);          // 先递归左子树\n  build(pl + left + 1, pr, k + 1, ir);          // 再递归右子树\n  post.push_back(root);           // 后序：左右都处理完再压根\n}\n\nint main() {\n  int n; cin >> n;\n  pre.resize(n); in.resize(n);\n  for (int i = 0; i < n; i++) cin >> pre[i];\n  for (int i = 0; i < n; i++) cin >> in[i];\n  build(0, n - 1, 0, n - 1);\n  for (int i = 0; i < n; i++) {\n    if (i) cout << ' ';\n    cout << post[i];\n  }\n  cout << endl;\n  return 0;\n}"
    },
    {
      "id": "pat-a1003-dijkstra",
      "title": "城市紧急救援（最短路径 + 路径条数与救援队最多）",
      "university": "浙江大学 PAT",
      "year": 2019,
      "module": "数据结构 · 图",
      "scene": "工作中：微服务调用链里，要算「从网关到某个故障节点的最短跳数路径」，并在多条等长路径里选「经过的健康实例最多」的一条做熔断降级；同时统计有多少条等价最短路径（用于限流均摊）。与本题的 dist/ways/weight 三维最短路完全同构。",
      "framework": "① 大框架：输入 N 城市、M 边、起点 C1、终点 C2，及每个城市救援队数 → Dijkstra 求最短路 → 同步维护「最短路条数 ways」与「沿最短路能集结的最大救援队数 teams」。边界：起点=终点时 ways=1、teams=起点的救援队数；重边取最小。",
      "algorithm": "② 核心算法思想：优先队列维护 (dist,u)。松弛时若 d[v] > d[u]+w 则整体更新（dist/ways=ways[u]/teams=teams[u]+team[v]）；若相等则 ways[v]+=ways[u] 且 teams[v]=max(teams[v], teams[u]+team[v])。注意 ways 用加法原理、teams 用择优，二者更新时机不同。",
      "code": "#include <iostream>\n#include <vector>\n#include <queue>\nusing namespace std;\nconst int INF = 1e9;\n\nint main() {\n  int n, m, c1, c2; cin >> n >> m >> c1 >> c2;\n  vector<int> team(n);\n  for (int i = 0; i < n; i++) cin >> team[i];\n  vector<vector<pair<int,int>>> g(n);   // 邻接表 (to, w)\n  for (int i = 0; i < m; i++) {\n    int a, b, w; cin >> a >> b >> w;\n    g[a].push_back({b, w}); g[b].push_back({a, w});\n  }\n  vector<int> dist(n, INF), ways(n, 0), teams(n, 0);\n  dist[c1] = 0; ways[c1] = 1; teams[c1] = team[c1];\n  priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>> pq;\n  pq.push({0, c1});\n  while (!pq.empty()) {\n    auto [d, u] = pq.top(); pq.pop();\n    if (d > dist[u]) continue;           // 过期堆元素跳过\n    for (auto [v, w] : g[u]) {\n      if (dist[v] > dist[u] + w) {       // 找到更短路径：整体更新\n        dist[v] = dist[u] + w;\n        ways[v] = ways[u];\n        teams[v] = teams[u] + team[v];\n        pq.push({dist[v], v});\n      } else if (dist[v] == dist[u] + w) { // 等长路径：叠加条数、择优救援队\n        ways[v] += ways[u];\n        teams[v] = max(teams[v], teams[u] + team[v]);\n      }\n    }\n  }\n  cout << ways[c2] << ' ' << teams[c2] << endl;\n  return 0;\n}"
    },
    {
      "id": "buaa-linkedlist-dedup",
      "title": "链表绝对值去重（保留首次出现，移除重复绝对值节点）",
      "university": "北京航空航天大学",
      "year": 2020,
      "module": "数据结构 · 线性表",
      "scene": "工作中：消息去重。上游同一批事件可能因重试重复投递（key 是「业务单号」的绝对哈希），你要保留首次出现的事件、丢弃后续重复，并原地改写链表式队列。与本题「绝对值去重 + 原地删节点」一一对应。",
      "framework": "① 大框架：输入链表头 + 长度 N → 用布尔数组 seen[10001] 记录已出现的绝对值 → 遍历链表，若 |val| 已出现过则删除当前节点，否则标记并前进。边界：空链表直接返回；头节点重复需特殊处理（本题约定头一定保留）。",
      "algorithm": "② 核心算法思想：单指针 pre 指向已保留链表的尾，cur 遍历。遇到重复绝对值就 pre->next = cur->next 跳过并 free，cur 不前进；否则 pre=cur 前进。用定长 seen 数组 O(1) 判重，整体 O(N)。",
      "code": "#include <iostream>\nusing namespace std;\n\nstruct Node { int val; Node* next; Node(int v): val(v), next(nullptr) {} };\n\nNode* dedup(Node* head) {\n  bool seen[10001] = {false};      // 值绝对值上限约定 10000\n  Node* pre = head;\n  Node* cur = head ? head->next : nullptr;\n  if (head) seen[abs(head->val)] = true;   // 头节点一定保留\n  while (cur) {\n    int a = abs(cur->val);\n    if (seen[a]) {                 // 绝对值重复：摘掉 cur\n      pre->next = cur->next;\n      Node* tmp = cur; cur = cur->next; delete tmp;\n    } else {                       // 首次出现：标记并前进\n      seen[a] = true; pre = cur; cur = cur->next;\n    }\n  }\n  return head;\n}\n\nint main() {\n  // 读取省略：按题面构造链表后调用 dedup 并顺序打印\n  return 0;\n}"
    },
    {
      "id": "hust-topo-course",
      "title": "课程表 II（拓扑排序，判断能否修完并给一种顺序）",
      "university": "华中科技大学",
      "year": 2021,
      "module": "数据结构 · 图",
      "scene": "工作中：CI/CD 流水线或 Airflow DAG 的任务依赖。你要确认「依赖图无环」才能调度，否则会死锁；合法时还要给出一个可行的执行顺序（拓扑序）供并行分批。与本题 Kahn 算法拓扑排序完全同构。",
      "framework": "① 大框架：输入课程数 num + 先修对 [a,b]（学 a 前先学 b）→ 建图（b→a）+ 入度表 → Kahn 算法：队列放所有入度 0 的节点，逐个出队、消去其出边、入度归零者入队 → 输出顺序；若输出数 < num 说明有环，返回空。",
      "algorithm": "② 核心算法思想：拓扑排序本质是对 DAG 的层次展开。Kahn 用「入度为 0 即可开始」不断削减；若最后仍有节点入度 >0，则存在环（互相依赖），无法完成。队列保证字典序最小可用小根堆，本题顺序任意。",
      "code": "#include <iostream>\n#include <vector>\n#include <queue>\nusing namespace std;\n\nvector<int> topo(int num, vector<pair<int,int>>& pre) {\n  vector<vector<int>> g(num);\n  vector<int> indeg(num, 0);\n  for (auto& [a, b] : pre) { g[b].push_back(a); indeg[a]++; } // b 是 a 的先修\n  queue<int> q;\n  for (int i = 0; i < num; i++) if (indeg[i] == 0) q.push(i);\n  vector<int> order;\n  while (!q.empty()) {\n    int u = q.front(); q.pop();\n    order.push_back(u);\n    for (int v : g[u]) if (--indeg[v] == 0) q.push(v);\n  }\n  if ((int)order.size() != num) return {};   // 有环，无法修完\n  return order;\n}\n\nint main() {\n  int num, m; cin >> num >> m;\n  vector<pair<int,int>> pre(m);\n  for (auto& [a, b] : pre) cin >> a >> b;\n  auto ans = topo(num, pre);\n  if (ans.empty()) cout << \"IMPOSSIBLE\" << endl;\n  else { for (int i = 0; i < num; i++) cout << ans[i] << (i+1<num?' ':'\\n'); }\n  return 0;\n}"
    },
    {
      "id": "sjtu-maxsubarray",
      "title": "最大连续子序列和（动态规划）",
      "university": "上海交通大学",
      "year": 2022,
      "module": "算法 · 动态规划",
      "scene": "工作中：监控指标异常检测。比如一段心跳时延序列里，找出「连续 N 分钟」使平均/累计延迟最大的一段（定位故障窗口）；或交易系统找出收益最猛的连续持仓区间。与本题「最大子段和」同构，只是阈值从「最大」换成「超过某值的最长区间」。",
      "framework": "① 大框架：输入序列 → 设 dp[i] 为「以 i 结尾的最大子段和」→ 转移 dp[i]=max(a[i], dp[i-1]+a[i]) → 全程取最大。同时用 pre/cur 滚动省空间。边界：全负数返回最大负数；记录起止下标需额外维护。",
      "algorithm": "② 核心算法思想：关键洞察是「如果前面累加和为负，不如从当前元素重新开始」——负数前缀只会拖累后面。因此转移只在 dp[i-1]>0 时才接上。O(N) 一次扫描，空间 O(1)。",
      "code": "#include <iostream>\n#include <vector>\n#include <climits>\nusing namespace std;\n\nint maxSub(const vector<int>& a) {\n  int cur = 0, best = INT_MIN;\n  for (int x : a) {\n    cur = max(x, cur + x);   // 负数前缀就丢弃，从 x 重开\n    best = max(best, cur);\n  }\n  return best;\n}\n\nint main() {\n  int n; cin >> n;\n  vector<int> a(n);\n  for (int i = 0; i < n; i++) cin >> a[i];\n  cout << maxSub(a) << endl;\n  return 0;\n}"
    },
    {
      "id": "unified-island",
      "title": "岛屿数量（DFS/BFS 连通块计数）",
      "university": "全国统考机试",
      "year": 2023,
      "module": "算法 · 搜索",
      "scene": "工作中：用户分群或风控里的「连通团伙识别」。比如一批设备/账号构成关系图，找出相互关联的团伙数（一个团伙 = 一个连通块）；或图像里数出几块相连的故障区域。与本题「1 的连通块个数」完全同构，只是把网格换成邻接表。",
      "framework": "① 大框架：输入 M×N 的 0/1 网格 → 遍历每个格子，遇到未访问的 1 就「淹没」它所在的整块（DFS 或 BFS 把相邻 1 标为已访问）→ 每淹没一块计数 +1。边界：网格为空返回 0；注意上下左右四连通（斜向不算）。",
      "algorithm": "② 核心算法思想：连通块计数 = 遍历起点数。每进入一个未访问的陆地，就把它整块「染色」成已访问，保证不重复计数。DFS 用递归/栈，BFS 用队列，二者复杂度都是 O(MN)。",
      "code": "#include <iostream>\n#include <vector>\nusing namespace std;\n\nint m, n;\nvector<vector<int>> g;\n\nvoid dfs(int x, int y) {\n  if (x<0||y<0||x>=m||y>=n||!g[x][y]) return;  // 越界或海水\n  g[x][y] = 0;                                  // 淹没当前陆地\n  dfs(x+1,y); dfs(x-1,y); dfs(x,y+1); dfs(x,y-1); // 四连通扩散\n}\n\nint main() {\n  cin >> m >> n;\n  g.assign(m, vector<int>(n));\n  for (int i=0;i<m;i++) for (int j=0;j<n;j++) cin >> g[i][j];\n  int cnt = 0;\n  for (int i=0;i<m;i++) for (int j=0;j<n;j++)\n    if (g[i][j]) { dfs(i, j); cnt++; }   // 每发现一块新陆地就淹没并计数\n  cout << cnt << endl;\n  return 0;\n}"
    }
  ]
};
