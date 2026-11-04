# -*- coding: utf-8 -*-
"""python 学科来源锚点重写（批次 P1，9 章 28 条）。

依据：逐章 grep concept/*.md 的真实 `##` 标题，按「文件序号.文件内小节序号」重编 §。
每条格式：`§x.y 小节标题 · 读什么`（分隔符为前后各一空格的中间点，供 split_note 拆两栏）。

为什么要重写
------------
原 notes 的 § 编号是「主题一/主题二」想象出来的，与 concept 真实小节完全错位：
  py-ch01 原写 `§1.2 讲「流程控制与分支」` —— 真实 1.2 是「可变与不可变」，流程控制在第 2 个文件
  py-ch03 原写 `§4.2 讲「集合去重」`   —— 本章只有 3 个概念文件，§4.2 根本不存在
`scripts/audit_source_anchor.py` 可复验这类错位（Q1 编号越界 / Q3 标题漂移）。
"""
import json
import os
import re

MANIFEST = "content/python/_manifest.json"
CH_DIR = "content/python"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)


def split_note(note: str) -> tuple[str, str]:
    """把 "<对应本章> · <读什么>" 拆成两栏；无分隔符则整条进「读什么」。"""
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行（B 站表格同形，必须框定范围）。"""
    path = os.path.join(CH_DIR, cid, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"
    with open(path, encoding="utf-8") as f:
        s = f.read()
    lines = s.split("\n")

    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        return False, "找不到「## 本章 GitHub」小节"

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = [i for i in range(start, end) if RE_GH_ROW.match(lines[i])]
    if not row_idx:
        return False, "小节内无表格行"
    if len(row_idx) != len(notes):
        return False, f"表格 {len(row_idx)} 行、notes {len(notes)} 条，不匹配"

    for i, note in zip(row_idx, notes):
        m = RE_GH_ROW.match(lines[i])
        head, tail = split_note(note)
        lines[i] = (
            f"| {m.group(1)} | [{m.group(2)}]({m.group(3)}) | {m.group(4)} "
            f"| {head} | {tail} |"
        )

    out = "\n".join(lines)
    if out == s:
        return True, "已是同源"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    return True, f"表格 {len(row_idx)} 行已同步"


NOTES: dict[str, list[str]] = {
    # ---------------- py-ch01 语法与数据类型 ----------------
    "py-ch01": [
        "§2.2 `for` 的本质：迭代器协议 · 读 `maths/` 与 `conversions/` 下的单文件脚本："
        "它们几乎都用 `for x in 序列` 直取元素、从不靠下标推进，正好对照「for 拿到的是迭代器吐出的值」"
        "——想验证这一点，把这些脚本里的一层循环改成手动 `next()` 看输出是否一致",

        "§1.2 可变与不可变：唯一需要背的分类 · 看 `Day01-15/` 的基础语法篇："
        "它对「可变/不可变」的表述决定了后面默认参数与浅拷贝的坑，"
        "重点盯它对 `list` 与 `tuple` 的对比——本章「别名、缓存与浅拷贝」那节的示例就是这条的展开",

        "§3.4 `dict`：哈希表，且保证插入顺序 · 看入门课的数据准备一节："
        "特征用列表、样本用字典，这种「列表套字典」是读 CSV/JSON 时最常见的内存形态；"
        "本章 §3.1 复杂度速查里的 O(1) 平均查找，就是靠这里每条样本的键哈希换来的",
    ],
    # ---------------- py-ch02 函数与作用域 ----------------
    "py-ch02": [
        "§4.1 理论根基：函数是携带环境的对象 · 读 `dynamic_programming/` 里的记忆化实现："
        "用字典缓存 + 嵌套函数把递归复杂度从指数压到多项式，是闭包最实用的场景；"
        "关键是看外层那个 `memo` 字典如何被内层函数「带着走」——这就是 §4.2 的 cell",

        "§2.2 实现机制：参数如何传递与解包 · 看 `Day01-15/` 的函数篇："
        "`*args`/`**kwargs` 与「关键字参数必须写在位置参数之后」的规则，它给了能直接跑的反例；"
        "对照 §5.1 可变默认参数陷阱，能看出「解包」和「默认值」是两套独立机制",

        "§3.1 理论根基：函数作为值 · 看入门课的特征工程脚本："
        "把「清洗函数」作为参数传给 `apply`，这是「函数即值」在数据处理里的日常用法；"
        "读的时候数一下：这个函数被创建了几次、被调用了几次——这正是 §2.1「函数被延迟创建」的意思",
    ],
    # ---------------- py-ch03 内置数据结构 ----------------
    "py-ch03": [
        "§2.2 哈希冲突与「最坏 O(n)」 · 读 `hashes/` 目录的 `hash_table.py`："
        "它用「桶数组 + 链地址」实现，能直接看到「冲突怎么处理、扩容怎么触发」——"
        "比背复杂度直观；读完再回本章 §2.1，就明白为什么 3.7 之前 dict 不保证顺序",

        "§3.3 深浅拷贝：拷贝的是「引用」还是「对象图」 · 看 `Day01-15/` 的容器篇："
        "`copy.copy` 只复制外层、`deepcopy` 递归复制，嵌套列表的例子能把「改内层影响原对象」"
        "演示清楚；配合 §3.4 的 `[[0]] * 3` 陷阱一起读，两个坑一次看清",

        "§2.4 `set`：同一套哈希机制，只存 key · 看入门课的数据清洗一节："
        "用 `set` 找重复样本、用 `Counter` 统计类别分布，是数据准备阶段的高频动作；"
        "注意 `set` 与 `dict` 在 §2.3 可哈希契约上的共同约束——存进去的东西必须 `__hash__` 与 `__eq__` 一致",
    ],
    # ---------------- py-ch04 标准库 ----------------
    "py-ch04": [
        "§2.2 `sys.path` 与导入解析顺序 · 读仓库根目录的脚本组织方式："
        "所有算法按目录归类、用 `if __name__ == \"__main__\"` 提供自测入口，"
        "这是「模块 vs 脚本」的现成范例；读完再回 §1.1，就明白为什么它不写 `sys.path.append` 也能互相导入",

        "§3.1 三种时间表示，别混着用 · 看 `Day16-20/` 的日期处理篇："
        "`datetime` 默认是「无时区」的 naive、`timezone` 要显式加，混用会导致跨时区差 8 小时；"
        "这正是 §3.2「naive 会被当成本地时间」那个坑的现场，再读 §3.3 的 `zoneinfo` 收尾",

        "§4.1 类型映射表：什么能过、什么会炸 · 看入门课的数据集加载："
        "把配置与标签放在 JSON 里、用 `json.load` 读，比硬编码在脚本里更好维护；"
        "读的时候顺手找一处「把 `datetime` 或 `set` 塞进 `json.dumps`」的写法——"
        "那就是 §4.3 `default` 参数存在的理由",
    ],
    # ---------------- py-ch05 文件与 IO ----------------
    "py-ch05": [
        "§2.1 `with` 究竟做了什么 · 读仓库里读文件的工具函数："
        "显式 `with open(...)` 而不是手动 `close`，异常路径下也能保证句柄释放；"
        "读完再回 §2.2，就明白「句柄为什么一定被关掉」取决于 `__exit__` 是否吞掉异常",

        "§1.2 `encoding` 必须显式写 · 看 `Day16-20/` 的文件篇："
        "`open(..., encoding=\"utf-8\")` 必须显式写，Windows 默认 GBK 会让中文读写互崩；"
        "配合 §1.4 的 BOM 与 §1.5 的 `errors` 策略，就是一整套「文本 IO 排障顺序」",

        "§3.6 大文件处理的内存红线 · 看入门课处理数据集的方式："
        "逐行迭代而不是 `readlines()` 全量入内存，这是「数据比内存大」时的基本写法；"
        "它的前提是 §3.2 的缓冲策略——读的时候对照 `buffering` 参数，算一下 10GB 文件逐行读的真实内存占用",
    ],
    # ---------------- py-ch06 正则 ----------------
    "py-ch06": [
        "§4.4 什么时候不该用正则 · 读 `strings/` 目录下的校验脚本："
        "邮箱/手机号的正则各一版，能对照出「什么时候该用正则、什么时候该写解析」；"
        "读完再回 §1.2 `findall` 的分组陷阱——这正是「正则看着对、结果不对」的常见来源",

        "§2.3 反向引用：`\\1` 与 `\\g<1>` · 看 `Day21-30/` 的文本处理篇："
        "`re.sub` 配反向引用做「调换两段」的改写，比字符串切分稳；"
        "先读 §2.1 三类括号弄清「哪个括号是分组、哪个是被捕获」，再回来看替换模板里的 `\\g<name>`",

        "§3.2 回溯爆炸：为什么会指数级 · 看入门课的文本清洗："
        "对长文本用简单字符类而不是嵌套量词 `(a+)+`，后者在异常输入上会指数级回溯；"
        "对照 §3.1 三种量词语义与 §3.3 三种解法（原子组 / 占有量词模拟 / 换算法），"
        "就是本章「灾难性回溯」的完整处置链",
    ],
    # ---------------- py-ch07 并发 ----------------
    "py-ch07": [
        "§1.3 二维决策：IO 密集 vs CPU 密集 · 读仓库里的并行示例："
        "CPU 密集用多进程、IO 密集用多线程，这个目录的脚本大多是「纯计算」，"
        "正好说明「为什么它们不能靠 threading 提速」；读的时候对照 §1.1 GIL 是什么，"
        "就知道提速失败不是写法问题而是锁的问题",

        "§4.1 协程是「可暂停的函数」 · 看 `Day31-35/` 的并发篇："
        "`async def` + `await` 把「等待」让出去，写法与线程池完全不同，别混着用；"
        "重点读 §4.4「最大的坑：阻塞事件循环」——一个同步 `time.sleep` 就能让整条协程链停摆",

        "§3.2 线程池：别再手写 `Thread` · 看入门课的批量处理脚本："
        "用线程池做 IO 密集的图片下载，注意「线程数不是越多越好」——上下文切换会吃掉收益；"
        "配合 §3.3 Future 与异常传播，看它的 `submit` 结果是怎么收集失败的，"
        "这决定了「下载失败会不会被静默吞掉」",
    ],
    # ---------------- py-ch08 numpy/pandas ----------------
    "py-ch08": [
        "§1.2 向量化与循环的对照 · 读 `sorts/` 的实现："
        "纯 Python 循环排序在十万级数据上比 `numpy.sort` 慢两个数量级，"
        "这是「为什么数值计算要用 ndarray」的最直观对照；读时把 §1.1 的 dtype 与步长概念带上，"
        "就明白差距来自「解释器循环 vs C 循环 + 连续内存」",

        "§4.1 `Series` / `DataFrame` 与索引对齐 · 看 `Day41-55/` 的数据分析篇："
        "`loc` 按标签、`iloc` 按位置，混用是「取出来的数据不对」的头号原因；"
        "先把 §2.1 视图与副本的语义弄清，再读这段，就不会把「切片拿到的是视图」当成 bug",

        "§3.1 广播规则 · 看入门课的回归案例："
        "`X` 是 `(样本数, 特征数)`、`y` 是 `(样本数,)`，形状对不上是 `fit` 报错的第一排查点；"
        "这正是 §3.2 axis 语义与聚合的直接应用——`(n,1) - (n,)` 为什么会广播成 `(n,n)`，"
        "在这里能一眼看出代价",
    ],
    # ---------------- py-ch09 面向对象 ----------------
    "py-ch09": [
        "§1.1 可变类属性是共享的 · §2.1 `super()` 不是「父类」 · 读 `Objects/typeobject.c` 的 "
        "`tp_getattro` 与 MRO 计算：属性查找走的是「实例字典 → 类 MRO」这条链，"
        "所以类属性被所有实例共享、`super()` 找的是 MRO 里的下一个类而不是父类",

        "§2.1 `super()` 不是「父类」 · Flask 用 `Scaffold` + `__init_subclass__` 收集视图，"
        "`App` 的继承与 `super()` 调用链正是 §2.1 讲的那套机制；"
        "读 `pallets/flask` 的 `app.py` 看 `__init_subclass__` 何时触发，"
        "就明白为什么插件能「声明即注册」",

        "§3.2 `@property` 与三种方法修饰符 · 读 `attrs` 如何用描述符把类属性变成带校验的字段："
        "`attrs` 的 `_make_init` 给每个字段生成 `__set__`，等同于本章说的「数据描述符优先于实例字典」；"
        "配合 §3.3 魔术方法查找为什么绕过实例字典，两条机制就对上了",

        "§2.2 什么时候真的该用多继承 · 读 GoF 设计模式合集："
        "`Strategy` / `Adapter` 在这里都是「组合 + 委托」而非继承，"
        "正好是本章「继承 vs 组合」取舍的反例样本；"
        "读的时候问一句：换成多继承会引入哪个 MRO 冲突——答不上来就说明该用组合",
    ],
}


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    data = json.load(open(MANIFEST, encoding="utf-8"))

    done = 0
    changed = False
    for ch in data.get("chapters", []):
        cid = ch.get("id")
        if cid not in NOTES:
            continue
        new = NOTES[cid]
        res = ch.setdefault("resources", {})
        old = res.get("github_notes", [])
        if len(old) != len(new):
            print(f"!! {cid} 原 {len(old)} 条、新 {len(new)} 条，不匹配，跳过")
            continue
        if old != new:
            res["github_notes"] = new
            changed = True
        done += 1
        ok, msg = rewrite_goals_table(cid, new)
        print(f"{'OK ' if ok else '!! '}{cid}: notes {len(new)} 条｜{msg}")

    # 换行按学科探测：python 是 LF，写死 CRLF 会产生整份假 diff
    if changed:
        with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"manifest 已写盘（{done} 章）")
    else:
        print(f"manifest 已是目标状态（{done} 章），未写盘")


if __name__ == "__main__":
    main()
