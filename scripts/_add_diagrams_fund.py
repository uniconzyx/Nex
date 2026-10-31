# -*- coding: utf-8 -*-
"""为 fundamentals（数据结构/计组/计网/操作系统）各章 concept 插入 ASCII 图表。
渲染器只支持代码块内等宽文本，故用 ```text 围栏。

每章在第一个 concept 文件的「## 三视角解析」之前插入一张最能概括本章结构的图。
用法：python scripts/_add_diagrams_fund.py
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

# (chapter, diagram_text)
DIAG = {
    "fund-ch01": r"""```text
数组:    [ 0 ][ 1 ][ 2 ][ 3 ][ 4 ]   连续内存，随机访问 O(1)，插入/删除 O(n)
链表:    ●─▶●─▶●─▶●─▶∅            节点分散存 data+next，访问 O(n)，头插/头删 O(1)
双链表:  ◀─●─▶◀─●─▶◀─●─▶          每个节点多一个 prev，删除已知节点 O(1)
```""",

    "fund-ch02": r"""```text
栈(Stack, LIFO):   push▶[ A ][ B ][ C ]◀pop     后进先出，用数组/链表尾作栈顶
队列(Queue, FIFO): enq▶[ A ][ B ][ C ]◀deq     先进先出，需头指针+尾指针
循环队列:  尾到头绕回，用 (rear+1)%cap==front 判满
串匹配:  KMP 靠失配函数 next[] 跳过已匹配前缀，避免主串指针回退
```""",

    "fund-ch03": r"""```text
          [ 1 ]
         /     \
      [ 2 ]   [ 3 ]
     /   \       \
  [ 4 ] [ 5 ]   [ 6 ]
先序(根左右): 1 2 4 5 3 6
中序(左根右): 4 2 5 1 3 6
后序(左右根): 4 5 2 6 3 1
层序(BFS)   : 1 2 3 4 5 6     二叉搜索树靠「中序有序」支撑查找 O(log n)
```""",

    "fund-ch04": r"""```text
邻接表(稀疏图省空间):   0 → [1, 2]   1 → [2]   2 → []
邻接矩阵(稠密图查边快): 2D 布尔表，查边 O(1)，空间 O(V²)
遍历:  BFS 用队列(按层)   DFS 用栈或递归(一条路走到底)
最短路径: Dijkstra(非负权) / Floyd(全源)   最小生成树: Prim / Kruskal
```""",

    "fund-ch05": r"""```text
key ──hash()──▶ 槽位 h
冲突解决:
  链地址法:  槽 h ─▶ [node]─▶[node]─▶∅      (Java HashMap 做法)
  开放寻址:  h, h+1, h+2 ... 线性探测       (探测序列填满整个表)
负载因子 α = 元素数 / 槽数；α↑ → 冲突↑ → 查找从 O(1) 退化到 O(n)
```""",

    "fund-ch06": r"""```text
        最好      平均      最坏     稳定   核心思想
插入排序  O(n)     O(n²)    O(n²)    稳    边扫描边把元素插到已排序区
快速排序  O(nlogn) O(nlogn) O(n²)   不稳  分治+基准，最左/右作枢轴
归并排序  O(nlogn) O(nlogn) O(nlogn) 稳   分治+合并，额外 O(n) 空间
堆排序    O(nlogn) O(nlogn) O(nlogn) 不稳  建堆后反复取堆顶
计数/桶/基: 非比较排序，可突破 O(nlogn) 下界
```""",

    "fund-ch07": r"""```text
原码:   [符号][数值]          0 和 -0 两种表示，加减要判符号，麻烦
补码:   负数 = 取反 + 1       统一用加法器做减法，只有一种 0，溢出可检
浮点 IEEE754(32位): [1位S][8位阶E][23位尾M]  值 = (-1)^S × 1.M × 2^(E-127)
  阶码全0/全1 用作 0 / 非规 / ±∞ / NaN
```""",

    "fund-ch08": r"""```text
存储层次(越往外越慢越大):
  CPU寄存器 ─ L1 ─ L2 ─ L3 ─ 内存 ─ SSD ─ HDD
CPU 五级流水: 取指 → 译码 → 执行 → 访存 → 写回  (理想吞吐≈单级延迟)
Cache 映射: 直接映射 / 组相联 / 全相联   命中率取决于时间+空间局部性
```""",

    "fund-ch09": r"""```text
进程 = 资源容器(地址空间/文件句柄)   线程 = 进程内的执行流
PCB ──拥有──▶ 若干 TCB
状态机:  就绪 ─▶(调度) 运行 ─▶(时间片到) 就绪
                    │
                    └─▶(等IO) 阻塞 ─▶(IO完成) 就绪
调度: FCFS / 时间片轮转 / 优先级 / 多级反馈队列
```""",

    "fund-ch10": r"""```text
虚拟地址 ─MMU─▶ 页表 ─▶ 物理页帧       分页让进程以为独占内存
页面置换: FIFO / LRU / Clock   缺页率高 → 频繁换入换出(颠簸)
文件: inode ─▶ 数据块链表            IO 缓冲/缓存减少 syscall 与磁盘次数
```""",

    "fund-ch11": r"""```text
应用层  HTTP / DNS / FTP
传输层  TCP(可靠,三次握手)  UDP(不可靠,低延迟)
网络层  IP(路由,无连接)     ICMP
链路层  帧 / MAC / ARP / 交换机
TCP 三次握手建连:  SYN → SYN+ACK → ACK
TCP 四次挥手断连:  FIN → ACK → FIN → ACK
```""",

    "fund-ch12": r"""```text
浏览器 ─DNS解析─▶ IP ─TCP握手─▶ TLS ─HTTP请求─▶ 服务器 ─响应─▶ 渲染
排错自底向上:
  ping       (网络层连通)
  traceroute (路径哪跳丢包)
  curl -v    (应用层请求/响应头)
  RTT / 丢包率 / 重传 定位瓶颈
```""",
}

ANCHOR = "## 三视角解析"

# 每章图内唯一签名串，用于幂等判定（已插入则跳过，避免重复）
SIG = {
    "fund-ch01": "双链表",
    "fund-ch02": "循环队列",
    "fund-ch03": "先序(根左右)",
    "fund-ch04": "邻接表(稀疏图",
    "fund-ch05": "负载因子",
    "fund-ch06": "计数/桶/基",
    "fund-ch07": "IEEE754",
    "fund-ch08": "存储层次(越往外",
    "fund-ch09": "多级反馈队列",
    "fund-ch10": "虚拟地址 ─MMU",
    "fund-ch11": "应用层  HTTP",
    "fund-ch12": "排错自底向上",
}


def main() -> int:
    for ch, block in DIAG.items():
        d = CONTENT / "fundamentals" / ch / "concept"
        files = sorted(d.glob("*.md"))
        if not files:
            print(f"[skip] {ch} 无 concept")
            continue
        f = files[0]
        text = f.read_text(encoding="utf-8")
        # 幂等：已含本张图则跳过
        if SIG.get(ch, "") in text:
            print(f"[skip] {ch} 已含图")
            continue
        if ANCHOR in text:
            idx = text.index(ANCHOR)
            new = text[:idx] + block + "\n\n" + text[idx:]
        else:
            # 无锚点章（用 ## 1. 编号或 ## 三视角小结）：插在 H1 标题之后
            lines = text.splitlines(keepends=True)
            ins = None
            for i, ln in enumerate(lines):
                if ln.startswith("# "):
                    ins = i + 1
                    break
            if ins is None:
                print(f"[skip] {ch} 找不到标题行")
                continue
            # 跳过标题后的空行，插到首个非空内容之前
            j = ins
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            lines.insert(j, block + "\n\n")
            new = "".join(lines)
        f.write_text(new, encoding="utf-8")
        print(f"[ok] {ch} -> {f.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
