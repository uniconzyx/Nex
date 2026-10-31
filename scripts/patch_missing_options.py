"""为「只有题干、没有选项」的选择题补写选项（人工编写，非自动生成）。

为什么单独一个脚本
--------------------------------------------------------------------
`fix_choice_options.py` 处理的是「选项写在正文里、只是格式不标准」的题，可以
自动解析。但还有 28 道题**从来就没写过选项** —— 作者只写了题干和正确答案，
是历史遗留的内容缺口。这类只能按题意人工编写干扰项，不能靠正则。

覆盖清单（29 条，按学科）：
  ai        1  (LRU 元数据题)
  cpp       5  (cpp-ch20 q1/q2/q4/q5/q6)
  data      5  (广播 shape、403 处置、requests 超时、缺失值机制、模型缩放)
  middleware 6 (acks=all、重试乱序、幂等落库、削峰、事务消息、消费者/分区)
  python    11 (open mode、__exit__、decode replace、flush/fsync、re.match、
               后行断言、GIL、ThreadPool 背压、dtype、副本 vs 视图、loc/iloc)
  tooling   1  (CMD/ENTRYPOINT —— 原文两问合一、答案 5 个字母对 4 个选项，
               这里拆成 q3 + q3b 两道单选)

每条补丁都保持「正确答案字母与原有 answer.correct 一致」，只在个别原始数据
本身矛盾的题（tooling q3）上重写答案。

用法
--------------------------------------------------------------------
    python scripts/patch_missing_options.py            # dry-run
    python scripts/patch_missing_options.py --apply    # 写入
    python scripts/patch_missing_options.py --apply --restore   # 还原
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
BACKUP = CONTENT / "_backup_missing_options"


def o(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"key": k, "text": t} for k, t in pairs]


PATCHES: list[dict] = [
    # ---------------- ai ----------------
    {
        "file": "ai/ai-ch03/exercises.json",
        "title": "LeetCode 146",
        "options": o([
            ("A", "哈希表 + 双向链表即可让 `get` / `put` 均摊 O(1)；推理侧的 KV Cache 分页淘汰与它同构"),
            ("B", "用动态数组保存元素就能做到 O(1)，因为数组支持随机访问"),
            ("C", "只需要哈希表，不必维护任何顺序信息"),
            ("D", "必须用红黑树实现，因为要按 key 排序"),
        ]),
        "correct": ["A"],
    },
    # ---------------- cpp-ch20 ----------------
    {
        "file": "cpp/cpp-ch20/exercises.json",
        "title": "对 std::vector 调用 reserve(n) 之后",
        "options": o([
            ("A", "`capacity()` 恒为 100，`p` 始终有效"),
            ("B", "`size()` 不超过 100 时 `p` 有效；一旦扩容，旧内存被释放，`p` 悬空"),
            ("C", "`reserve` 之后 `p` 永远有效，因为 vector 不再搬移内存"),
            ("D", "`reserve(n)` 会把 `size()` 也设为 n，因此 `p` 指向已构造的元素"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "cpp/cpp-ch20/exercises.json",
        "title": "两个对象互相持有对方的 std::shared_ptr",
        "options": o([
            ("A", "引用计数仍能归零，两个对象都正常析构"),
            ("B", "引用计数无法归零，两个对象都不析构，内存泄漏"),
            ("C", "编译期报错，因为 shared_ptr 不允许互相持有"),
            ("D", "只有先构造的那个对象泄漏，另一个正常析构"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "cpp/cpp-ch20/exercises.json",
        "title": "关于返回局部对象",
        "options": o([
            ("A", "`return std::move(obj);`"),
            ("B", "`return obj;`"),
            ("C", "`return std::ref(obj);`"),
            ("D", "`return new Obj(obj);`"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "cpp/cpp-ch20/exercises.json",
        "title": "基类析构函数非 virtual 时",
        "options": o([
            ("A", "编译失败，因为基类析构函数不是 virtual"),
            ("B", "未定义行为：只调用 Base 的析构，Derived 的析构与 `p` 的释放都不执行，内存泄漏"),
            ("C", "运行期抛出 std::bad_cast"),
            ("D", "编译器会自动补一个虚析构，行为与加了 virtual 相同"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "cpp/cpp-ch20/exercises.json",
        "title": "在 for 循环里对 vector 持续 push_back",
        "options": o([
            ("A", "无风险，vector 保证元素地址在生命周期内稳定"),
            ("B", "扩容时元素整体搬移、旧内存释放，`p` 悬空，解引用是未定义行为"),
            ("C", "只会发生一次数据复制，`p` 仍指向有效副本"),
            ("D", "`p` 会被自动更新为新地址"),
        ]),
        "correct": ["B"],
    },
    # ---------------- data ----------------
    {
        "file": "data/data-ch02/exercises.json",
        "title": "广播后的 shape 推导",
        "content_md": "给定 `A.shape == (2, 1, 3)`、`B.shape == (4, 3)`，执行 `C = A + B`，`C.shape` 是多少？",
        "options": o([
            ("A", "`(2, 1, 3)`"),
            ("B", "`(2, 4, 1)`"),
            ("C", "`(2, 4, 3)`"),
            ("D", "抛出 ValueError，两者形状不兼容"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "data/data-ch05/exercises.json",
        "title": "采集时遇到 403",
        "options": o([
            ("A", "立即重试同一请求，直到返回 200"),
            ("B", "更换 User-Agent 伪装成浏览器后再抓"),
            ("C", "记录该 URL 与状态码后跳过，必要时通过站点公开接口或授权渠道获取"),
            ("D", "提高并发数抢占配额，把请求压过去"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "data/data-ch05/exercises.json",
        "title": "关于 requests 的超时设置",
        "options": o([
            ("A", "requests 默认有 30 秒超时，通常不需要显式设置"),
            ("B", "`timeout=5` 表示整个请求（含重定向与下载）最多 5 秒"),
            ("C", "不设 timeout 会一直挂住；传单个数字时连接与读取都用该值，读取超时衡量的是两次数据到达之间的间隔"),
            ("D", "`timeout` 只对 GET 生效，POST 不受影响"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "data/data-ch06/exercises.json",
        "title": "关于缺失值机制",
        "options": o([
            ("A", "只要缺失比例不高，无论哪种机制，删除缺失行都不会引入偏差"),
            ("B", "MCAR 下删除缺失行只损失样本量、不引入偏差；MAR 指缺失与**已观测**变量有关；MNAR 无法用数据自证"),
            ("C", "MAR 指缺失与缺失值本身有关，可以直接用均值填充"),
            ("D", "填充策略与缺失机制无关，选均值填充总是安全的"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "data/data-ch06/exercises.json",
        "title": "下列哪个模型不必须做特征缩放",
        "options": o([
            ("A", "KNN"),
            ("B", "RBF 核 SVM"),
            ("C", "决策树"),
            ("D", "PCA"),
        ]),
        "correct": ["C"],
    },
    # ---------------- middleware ----------------
    {
        "file": "middleware/mw-ch07/exercises.json",
        "title": "acks=all 与 min.insync.replicas",
        "options": o([
            ("A", "`acks=all` 要求所有副本（含尚未同步的 follower）都写入成功才返回"),
            ("B", "`acks=all` 的强度等于 min(ISR 实际大小, min.insync.replicas)；当 min.insync.replicas=1 时它会退化为 `acks=1`"),
            ("C", "`acks=all` 与 min.insync.replicas 无关，只要设了 all 就不会丢消息"),
            ("D", "`acks=all` 只能用于单副本 topic，多副本时必须用 `acks=1`"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "middleware/mw-ch07/exercises.json",
        "title": "什么情况下生产者重试会导致分区内乱序",
        "options": o([
            ("A", "只要 `retries>0` 就一定乱序，与其它参数无关"),
            ("B", "`max.in.flight.requests.per.connection>1` 且未开启幂等时，重试可能乱序；开启幂等后 Kafka 用 (PID, partition, seq) 保证有序，允许 in.flight ≤ 5"),
            ("C", "乱序只发生在消费者端，与生产者重试无关"),
            ("D", "开启幂等后必须把 in.flight 设为 1 才能保证有序"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "middleware/mw-ch07/exercises.json",
        "title": "幂等落库的正确写法",
        "options": o([
            ("A", "先 `SELECT` 判断 `order_no` 是否存在，不存在再 `INSERT`"),
            ("B", "`INSERT ... ON CONFLICT (order_no) DO NOTHING`，把原子性下沉到存储引擎"),
            ("C", "用 `REPLACE INTO`，冲突时直接覆盖"),
            ("D", "在应用层加一把 `synchronized` 锁，然后普通 `INSERT`"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "middleware/mw-ch08/exercises.json",
        "title": "削峰填谷能解决什么",
        "options": o([
            ("A", "削峰填谷平滑的是到达时间分布，并不减少总工作量"),
            ("B", "当生产速率长期大于消费速率时，积压会单调增长、永不清空"),
            ("C", "队列把「瞬时高并发」转成「平稳低并发」交给消费端处理"),
            ("D", "只要加了消息队列，消费端就永远不会被压垮"),
        ]),
        "correct": ["D"],
    },
    {
        "file": "middleware/mw-ch08/exercises.json",
        "title": "原生事务消息的归属",
        "options": o([
            ("A", "Kafka"),
            ("B", "RabbitMQ"),
            ("C", "RocketMQ"),
            ("D", "ActiveMQ"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "middleware/mw-ch08/exercises.json",
        "title": "消费者数超过分区数之后",
        "options": o([
            ("A", "触发 rebalance，6 个分区被 7 个消费者均分，吞吐提升"),
            ("B", "多出的消费者分不到分区、处于空闲，吞吐不再增长——分区数就是并行度上限"),
            ("C", "直接报错，消费者组拒绝新成员加入"),
            ("D", "集群自动扩容分区数，以匹配消费者数量"),
        ]),
        "correct": ["B"],
    },
    # ---------------- python ----------------
    {
        "file": "python/py-ch05/exercises.json",
        "title": "open 的 mode 参数语义",
        "options": o([
            ("A", "`encoding` 只在文本模式下合法，二进制模式传入会抛 `ValueError`"),
            ("B", "`'a'` 模式在文件不存在时会创建新文件"),
            ("C", "`'a'` 模式会把写指针定位到文件开头，从而覆盖原有内容"),
            ("D", "`'r+'` 要求文件必须已存在，否则抛 `FileNotFoundError`"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "python/py-ch05/exercises.json",
        "title": "__exit__ 的返回值语义",
        "options": o([
            ("A", "异常会被重新抛出，返回 True 只是记录日志"),
            ("B", "异常被视为已处理，不再向外传播"),
            ("C", "只对 `KeyboardInterrupt` 生效，其它异常照常抛出"),
            ("D", "返回 True 是非法的，解释器会抛 `TypeError`"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "python/py-ch05/exercises.json",
        "title": "解码错误的不可逆性",
        "options": o([
            ("A", "可以完整恢复为原来的 `b'caf\\xe9 ok'`"),
            ("B", "得到 `b'caf\\xef\\xbf\\xbd ok'`：`\\xe9` 已被 U+FFFD 替换，原字节永久丢失"),
            ("C", "第一步 `decode` 就会抛 `UnicodeDecodeError`，因为指定了 `errors='replace'` 也不生效"),
            ("D", "得到 UTF-8 编码的 `b'café ok'`，与原始字节一致"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "python/py-ch05/exercises.json",
        "title": "flush 与 fsync 的边界",
        "options": o([
            ("A", "`flush()` 已经把数据写到磁盘，进程崩溃或断电都不会丢"),
            ("B", "`flush()` 只把数据交给 OS 页缓存（进程崩溃可保、断电不可保）；`fsync()` 才触发落盘，两者都做才算断电安全"),
            ("C", "`fsync()` 只同步元数据，文件内容仍可能丢失"),
            ("D", "`flush()` 与 `fsync()` 是同一件事的两个名字"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "python/py-ch06/exercises.json",
        "title": "re.match 与 re.fullmatch 的行为差异",
        "options": o([
            ("A", "`re.match` 返回 `None`，`re.fullmatch` 也返回 `None`"),
            ("B", "`re.match` 返回 `'123'`，`re.fullmatch` 返回 `None`"),
            ("C", "`re.match` 返回 `None`，`re.fullmatch` 返回 `'123'`"),
            ("D", "两者都返回 `'123'`"),
        ]),
        "correct": ["A"],
    },
    {
        "file": "python/py-ch06/exercises.json",
        "title": "后行断言的长度约束",
        "options": o([
            ("A", "`(?<=a+)b`"),
            ("B", "`(?<=\\d*)x`"),
            ("C", "`(?<=abc)d`"),
            ("D", "`(?<=a|bc)e`"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "python/py-ch07/exercises.json",
        "title": "GIL 存在时，多线程在什么场景仍有收益",
        "options": o([
            ("A", "纯 Python 实现的 CPU 密集循环"),
            ("B", "纯 Python 实现的大整数矩阵乘法"),
            ("C", "I/O 密集任务（网络请求、文件读写）——线程等待 I/O 时会释放 GIL"),
            ("D", "用多线程替代多进程做 CPU 并行计算"),
        ]),
        "correct": ["C"],
    },
    {
        "file": "python/py-ch07/exercises.json",
        "title": "ThreadPoolExecutor 的任务队列与背压",
        "options": o([
            ("A", "直接抛 `RuntimeError`，拒绝多余任务"),
            ("B", "任务被放进无界队列缓存，内存持续增长，提交方不被阻塞（没有背压）"),
            ("C", "自动把 `max_workers` 扩容到 1000"),
            ("D", "队列满后丢弃最旧的任务"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "python/py-ch08/exercises.json",
        "title": "np.array([1, 2, 3.5])",
        "options": o([
            ("A", "`int64`"),
            ("B", "`float64`"),
            ("C", "`object`"),
            ("D", "`float32`"),
        ]),
        "correct": ["B"],
    },
    {
        "file": "python/py-ch08/exercises.json",
        "title": "哪些索引方式返回的是副本",
        "options": o([
            ("A", "`a[1:3]`（基本切片）"),
            ("B", "`a.reshape(2, 2)`"),
            ("C", "`a.T`（转置）"),
            ("D", "`a[[0, 2]]`（花式索引）"),
        ]),
        "correct": ["D"],
    },
    {
        "file": "python/py-ch08/exercises.json",
        "title": "loc 与 iloc 的切片端点差异",
        "options": o([
            ("A", "都是 3 个"),
            ("B", "都是 4 个"),
            ("C", "`loc` 3 个，`iloc` 4 个"),
            ("D", "`loc` 2 个，`iloc` 3 个"),
        ]),
        "correct": ["A"],
    },
]

# tooling q3：原文把「CMD 覆盖规则」和「shell 形式副作用」两问写成一道，
# 答案列了 B/C/D/E/H 五个字母而选项只有 A-D。拆成两道单选，内容不丢。
TOOLING_SPLIT = {
    "file": "tooling/tool-ch05/exercises.json",
    "id": "q3",
    "first": {
        "content_md": "镜像里写了 `ENTRYPOINT [\"python\"]`、`CMD [\"app.py\"]`，执行 `docker run img -u` 时最终运行的命令是什么？",
        "options": o([
            ("A", "`python app.py -u`"),
            ("B", "`python -u`"),
            ("C", "`-u`"),
            ("D", "`python app.py`（`docker run` 尾部参数被忽略）"),
        ]),
        "correct": ["B"],
    },
    "second": {
        "id": "q3b",
        "title": "shell 形式的 ENTRYPOINT 会带来什么",
        "content_md": "把上一题改成 shell 形式 `ENTRYPOINT python app.py` 后，下列哪种说法**正确**？",
        "options": o([
            ("A", "等价于 `exec` 形式，`CMD` 仍会作为参数追加"),
            ("B", "等价于 `/bin/sh -c \"python app.py\"`，`CMD` 被完全忽略；且 PID 1 是 `/bin/sh`，SIGTERM 不会转发给应用"),
            ("C", "镜像构建会直接失败，因为 ENTRYPOINT 不支持 shell 形式"),
            ("D", "`CMD` 会覆盖 ENTRYPOINT，最终只执行 `CMD` 里的命令"),
        ]),
        "correct": ["B"],
        "explanation": "shell 形式会再套一层 `/bin/sh -c`：① `CMD` 不再作为参数被追加，而是完全失效；② PID 1 变成 sh，`docker stop` 发的 SIGTERM 不会传给 python，只能等 10 秒超时后 SIGKILL，优雅退出逻辑全部失效。工程上应始终用 exec 形式：`ENTRYPOINT [\"/app/server\"]` + `CMD [\"--port\",\"8080\"]`。",
        "tags": ["Docker", "Dockerfile", "ENTRYPOINT", "信号处理"],
        "source_ref": "《Docker 技术入门与实战》Dockerfile 指令章节；tool-ch05 examples/ex10",
        "category": "基础题",
        "platform": "book",
        "difficulty": "mid",
        "type": "choice",
        "source": "book",
    },
}


def _norm_title(t: str) -> str:
    return "".join(str(t or "").split())


def find_item(items: list[dict], title: str) -> dict | None:
    key = _norm_title(title)
    for it in items:
        if _norm_title(it.get("title", "")).startswith(key):
            return it
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not BACKUP.exists():
            print("无备份")
            return 1
        snaps = sorted(p for p in BACKUP.iterdir() if p.is_dir())
        if not snaps:
            print("备份目录为空")
            return 1
        snap = snaps[-1]
        n = 0
        for src in snap.rglob("exercises.json"):
            dst = CONTENT / src.relative_to(snap)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
        print(f"已从 {snap.name} 还原 {n} 个文件")
        return 0

    snap_dir = BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
    touched: dict[pathlib.Path, dict] = {}
    applied, skipped, missing = 0, 0, []

    for p in PATCHES:
        fp = CONTENT / p["file"]
        if not fp.exists():
            missing.append((p["file"], p["title"], "文件不存在"))
            continue
        data = touched.get(fp)
        if data is None:
            data = json.loads(fp.read_text(encoding="utf-8"))
            touched[fp] = data
        it = find_item(data.get("items") or [], p["title"])
        if it is None:
            missing.append((p["file"], p["title"], "未匹配到题目"))
            continue
        have = [x for x in (it.get("options") or []) if isinstance(x, dict)]
        if len(have) >= 2:
            skipped += 1
            if args.verbose:
                print(f"  [skip] {p['file']} {p['title']}: 已有 {len(have)} 个选项")
            continue
        it["options"] = p["options"]
        if "content_md" in p:
            it["content_md"] = p["content_md"]
        ans = it.get("answer")
        if not isinstance(ans, dict):
            ans = {}
            it["answer"] = ans
        for k in ("choice", "value", "index"):
            ans.pop(k, None)
        ans["correct"] = p["correct"]
        applied += 1
        if args.verbose:
            print(f"  [ok] {p['file']} {p['title'][:24]} -> {p['correct']}")

    # ---- tooling q3 拆分 ----
    sp = TOOLING_SPLIT
    fp = CONTENT / sp["file"]
    if fp.exists():
        data = touched.get(fp) or json.loads(fp.read_text(encoding="utf-8"))
        touched[fp] = data
        items = data.get("items") or []
        idx = next((i for i, x in enumerate(items) if x.get("id") == sp["id"]), None)
        if idx is None:
            missing.append((sp["file"], sp["id"], "未找到 q3"))
        else:
            q3 = items[idx]
            q3["content_md"] = sp["first"]["content_md"]
            q3["options"] = sp["first"]["options"]
            ans = q3.setdefault("answer", {})
            ans["correct"] = sp["first"]["correct"]
            if not any(x.get("id") == "q3b" for x in items):
                second = dict(sp["second"])
                new_item = {
                    "id": second.pop("id"),
                    "type": "choice",
                    "category": second.get("category", "基础题"),
                    "platform": second.get("platform", "book"),
                    "difficulty": second.get("difficulty", "mid"),
                    "title": second["title"],
                    "content_md": second["content_md"],
                    "options": second["options"],
                    "answer": {"correct": second["correct"], "explain": second["explanation"]},
                    "explanation": "shell 形式 ENTRYPOINT 的双重副作用：CMD 失效 + 信号不转发。",
                    "tags": second["tags"],
                    "source": "book",
                    "source_ref": second["source_ref"],
                }
                items.insert(idx + 1, new_item)
                applied += 2
                if args.verbose:
                    print("  [split] tool-ch05 q3 -> q3 + q3b")

    if args.apply:
        for fp, data in touched.items():
            snap_dir.mkdir(parents=True, exist_ok=True)
            bak = snap_dir / fp.relative_to(CONTENT)
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bak)
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n==== 统计 ====")
    print(f"  应用      {applied}")
    print(f"  已跳过    {skipped}（已有选项）")
    print(f"  未匹配    {len(missing)}")
    for f, t, why in missing:
        print(f"    ! {f} {t} — {why}")
    print(f"  涉及文件  {len(touched)}")
    if args.apply:
        print(f"\n已写入。备份：{snap_dir}")
        print("还原：python scripts/patch_missing_options.py --restore")
    else:
        print("\n(dry-run，未写入。加 --apply 生效)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
