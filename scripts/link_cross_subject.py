# -*- coding: utf-8 -*-
"""补全跨学科前置边，并做全图环检测。

问题（2026-10-28 核查）：141 章 **跨学科前置边为 0 条**。后果不是抽象的——
  · `spring-ch01`（IoC 容器与依赖注入）的 prerequisites 是 `[]`，
    意味着「不需要任何 Java 基础就能学 Spring」；
  · `java-ch09`（Maven 与 Spring Boot 入门）学完，接不上 `spring-ch01`，
    两条科各自成岛，用户从 Java 学到 Spring 会撞墙；
  · `fs-ch08`（部署 / CI-CD / Docker）不要求 `tool-ch05`（Docker 基础），
    fs 自己讲了一遍 Docker、tool 又讲一遍，且谁都不承认对方；
  · `fs-ch05`（数据库与 REST API 设计）不要求 `db-ch01`（SQL 基础）。

本脚本只改 prerequisites，不动正文。规则一条：**每条新边都必须能说出「不学前者，
后者哪个知识点会读不懂」**，写不出来的不加（见 EDGES 里的 why 字段）。

安全措施：
  · 加边前先拓扑排序验环；成环则整批拒绝写入（宁可少一条边，不要一张有环的图）；
  · 已存在的边不重复加；
  · 写回前按原 manifest 的字段顺序与缩进序列化，避免整文件 diff。

用法：
    python scripts/link_cross_subject.py            # dry-run，打印将加的边
    python scripts/link_cross_subject.py --apply
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUBS = ("fundamentals", "cpp", "java", "spring", "python", "fullstack",
        "database", "middleware", "data", "bigdata", "tooling", "ai", "agent", "ml")

# (章, 前置章, 理由) —— 理由必须具体到「不学前者的哪个知识点，后者哪节读不懂」
EDGES: list[tuple[str, str, str]] = [
    # ── Java → Spring：这门课的前提是 Java，不是空的
    ("spring-ch01", "java-ch03",
     "IoC 注入的对象、@Component 的类、接口与实现的分工都依赖「继承/多态/接口」；"
     "不学 java-ch03，讲「按接口注入实现」时读者不知道接口在这里扮演什么角色"),
    ("spring-ch01", "java-ch04",
     "Spring 容器本身就是个 Map<String, Bean>，Bean 的存取、单例缓存都对照集合框架理解"),
    ("spring-ch02", "java-ch08",
     "Bean 生命周期里的「类加载 / 反射创建实例 / 无法回收」只有懂 JVM 内存与类加载才讲得透"),
    ("spring-ch03", "java-ch07",
     "AOP 代理与事务线程隔离要靠 ThreadLocal，那正是 java-ch07 的线程模型与锁"),
    ("spring-ch06", "db-ch01",
     "MyBatis 全部工作是把 SQL 与对象互转；SQL 本身没学过（SELECT/JOIN）就只是在抄 XML"),

    # ── Spring → 全栈：Java+Vue 那条线的入口
    ("fs-ch04", "java-ch01",
     "fs-ch04 的自选后端分支会演示 Spring Boot，至少要能读 Java 语法与 main 方法"),
    ("fs-ch06", "spring-ch05",
     "JWT 鉴权要落在「过滤器 / 拦截器 / Controller 参数」上，不懂 Web 层就只能调库"),

    # ── 全栈 → 数据库 / 工具链：现在谁都不承认对方
    ("fs-ch05", "db-ch01",
     "REST 资源建模直接对应表与 SQL；db-ch01 学完才知道 API 契约背后该建什么表"),
    ("fs-ch05", "db-ch02",
     "联表查询决定了 API 是返回嵌套对象还是两次请求，这正是 db-ch02 的 JOIN 与子查询"),
    ("fs-ch08", "tool-ch05",
     "fs-ch08 讲的是「部署一个镜像」，Dockerfile / 分层 / 卷都在 tool-ch05，不学前置等于跳讲"),
    ("fs-ch08", "tool-ch06",
     "CI-CD 起来的多服务要用 compose 编排，依赖顺序与健康检查是 tool-ch06 的内容"),

    # ── 全栈 → 中间件：登录态与热点缓存
    ("fs-ch06", "mw-ch04",
     "refresh token 存哪、怎么防重放、多实例下 token 状态怎么同步——绕不开缓存与分布式锁"),

    # ── 大数据 / 数据分析 → 工具链与数据库
    ("bd-ch06", "db-ch01",
     "离线数仓的 DWD/DWS 分层最终落到 HQL；没有 SQL 基础时「分组聚合」只是背语法"),
    ("bd-ch01", "tool-ch01",
     "启动 Hadoop 先要会 Linux 目录、权限与进程查看，否则连日志在哪都找不到"),
    ("data-ch05", "tool-ch02",
     "采集脚本要挂在 cron 上、要能后台跑、要会看退出码——都是 tool-ch02 的进程与 Shell"),
    ("data-ch08" if False else "data-ch06", "tool-ch02",
     "建模实战要跑批处理脚本与定时任务，进程/管道/退出码是前置"),

    # ── 中间件 / 数据 → 计算机基础（学原理必须先有 408 底座）
    ("mw-ch01", "fund-ch01",
     "SDS 为什么不用 char*、listpack 为什么省内存，都要先懂线性结构与内存布局"),
    ("db-ch03", "fund-ch03",
     "B+ 树索引这一章通篇是树；没学过 fund-ch03 的 B 树/M 阶，只能死记「三层存两千万行」"),
    ("db-ch03", "fund-ch10",
     "buffer pool 与页缓存、事务的 WAL 与文件系统 fsync 是同一件事的两面"),

    # ── AI 科内部跨线（agent / ai / ml 三线合并成一科，但内部也有先后）
    ("ai-ch09", "ai-ch01",
     "扩散模型的反向过程仍然是「张量 + 梯度」；没学过前向反向传播，噪声预测网络看不懂"),
    ("ai-ch10", "ai-ch03",
     "训练工程（并行策略 / 混合精度 / 显存账）的对象就是 Transformer，先懂结构再谈怎么摊"),

    # ── Python → 数据分析
    ("data-ch01", "py-ch03",
     "ndarray 与 list 的差异贯穿整门课；没学过 py-ch03 的容器与深浅拷贝，讲 view/copy 会混淆"),
    ("data-ch03", "data-ch01",
     "DataFrame 的列就是 ndarray，索引对齐与广播规则直接继承 NumPy"),
]


def load_manifest(sub: str) -> dict:
    return json.loads((ROOT / f"content/{sub}/_manifest.json").read_text(encoding="utf-8"))


def save_manifest(sub: str, data: dict) -> None:
    (ROOT / f"content/{sub}/_manifest.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_graph() -> dict[str, dict]:
    graph: dict[str, dict] = {}
    for s in SUBS:
        m = load_manifest(s)
        for c in m["chapters"]:
            graph[c["id"]] = {"subject": s, "prereq": list(c.get("prerequisites") or [])}
    t = (ROOT / "frontend/src/data/clangUnits.ts").read_text(encoding="utf-8")
    arr = json.loads(re.search(r"export const CLANG_CHAPTERS: BundleChapter\[\] = (\[.*?\]);", t, re.S).group(1))
    for c in arr:
        graph[c["id"]] = {"subject": "clang", "prereq": list(c.get("prerequisites") or [])}
    return graph


def has_cycle(graph: dict[str, dict]) -> list[str] | None:
    """返回一个环（章 id 列表）；无环返回 None。"""
    color: dict[str, int] = {k: 0 for k in graph}
    stack: list[str] = []

    def dfs(n: str) -> list[str] | None:
        color[n] = 1
        stack.append(n)
        for p in graph[n]["prereq"]:
            if p not in graph:
                continue
            if color[p] == 1:
                return stack[stack.index(p):] + [p]
            if color[p] == 0:
                r = dfs(p)
                if r:
                    return r
        stack.pop()
        color[n] = 2
        return None

    for k in graph:
        if color[k] == 0:
            r = dfs(k)
            if r:
                return r
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    graph = collect_graph()
    unknown = [(a, b) for a, b, _ in EDGES if a not in graph or b not in graph]
    if unknown:
        print("✗ 存在未知章 id：", unknown)
        return 1

    added, already = [], []
    for child, parent, why in EDGES:
        if parent in graph[child]["prereq"]:
            already.append((child, parent))
            continue
        graph[child]["prereq"].append(parent)
        added.append((child, parent, why))

    cycle = has_cycle(graph)
    if cycle:
        print("✗ 加边后成环，拒绝写入：", " → ".join(cycle))
        return 1

    cross = sum(1 for k, v in graph.items()
                if any(p.split("-")[0] != k.split("-")[0] for p in v["prereq"]))
    print(f"将新增 {len(added)} 条跨科前置边（已存在 {len(already)} 条）")
    for child, parent, why in added:
        print(f"  {child:14s} ← {parent:14s}")
        print(f"      理由：{why}")
    print(f"\n加边后：跨科前置章数 {cross} / {len(graph)} · 全图无环 ✓")

    if not args.apply:
        print("\n（dry-run，未写盘；加 --apply 生效）")
        return 0

    # 按学科分组写回（只改 prerequisites 字段，其余原样）
    by_subject: dict[str, dict[str, list[str]]] = {}
    for child, parent, _ in added:
        by_subject.setdefault(graph[child]["subject"], {})[child] = graph[child]["prereq"]

    for sub, wants in by_subject.items():
        m = load_manifest(sub)
        for c in m["chapters"]:
            if c["id"] in wants:
                c["prerequisites"] = wants[c["id"]]
        save_manifest(sub, m)
        print(f"  写入 content/{sub}/_manifest.json ({len(wants)} 章)")

    # 复核
    g2 = collect_graph()
    c2 = has_cycle(g2)
    print("\n复核：", "无环 ✓" if c2 is None else f"有环 ✗ {c2}")
    return 0 if c2 is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
