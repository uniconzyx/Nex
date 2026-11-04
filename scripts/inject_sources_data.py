# -*- coding: utf-8 -*-
"""data 学科来源笔记（6 章 24 条）。

病因与 fundamentals 早期章节相同：全部 6 章共用同一套模板
「§x.y 讲「某话题」时读某路径」，编号是虚构的、话题与本章无关
（如 data-ch05 是「数据采集」，却写「§4.1 讲采集数据的质量校验时读 sklearn 的 check_array」）。
本批按 concept 真实 `##` 标题逐节重写。
"""
import json
import os
import re

MANIFEST = "content/data/_manifest.json"
CH_DIR = "content/data"

RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

NOTES: dict[str, list[str]] = {
    # ---------------- data-ch01 NumPy 基础 ----------------
    # 仓库序：scikit-learn / PythonDataScienceHandbook / pandas / Data-Science-For-Beginners
    "data-ch01": [
        "§3.2 2. 三个数量级的差距从哪来 · 读 `sklearn/utils/extmath.py`："
        "里面 `safe_sparse_dot` 最终都落到 `numpy.dot`（底层 BLAS），"
        "这就是「向量化快在哪」的工业侧证据——"
        "它快不是因为 Python 写得短，而是因为整段计算被交给了一个按连续内存布局优化的 C/Fortran 内核；"
        "对照本章 §3.1「ufunc 是什么」看，ufunc 是逐元素版的同一件事",

        "§1.4 4. strides：NumPy 最精妙的设计 · 读 "
        "`notebooks/02.02-The-Basics-Of-NumPy-Arrays.ipynb`："
        "它用 `flags`、`strides`、`nbytes` 三个属性把「一块内存 + 元信息」直接打出来，"
        "比画图更直观；"
        "看完再回头看本章 §2.1「视图（view）vs 拷贝（copy）」——"
        "`a[::2]` 之所以是视图，就是因为只改了 strides、没动数据",

        "§1.5 5. C order vs F order · 读 `pandas/core/internals/managers.py`："
        "pandas 按 dtype 把同类型列聚成 Block，"
        "就是为了「连续访问 + 向量化」，与 ndarray 的 C 顺序是同一个动机；"
        "这解释了本章 §1.3「ndarray 的内存模型」为什么强调「连续」——"
        "一旦混入 object dtype，Block 就被拆散，后面的向量化全部退化",

        "§4.4 4. 用布尔索引做数据清洗（数据科学日常） · 读 "
        "`Data-Science-For-Beginners` 的 `2-Working-With-Data/`："
        "先把数据读成 ndarray / DataFrame 再谈建模，形状与 dtype 没对齐时后面全是错——"
        "这正是本节「数据清洗」的入口；"
        "而本章 §4.3「布尔索引的组合与陷阱」里的 `&`/`|` 必须加括号，"
        "在这个阶段最容易被 `and`/`or` 写错成报错",
    ],

    # ---------------- data-ch02 NumPy 进阶 ----------------
    "data-ch02": [
        "§3.1 一、向量化 vs 显式循环：为什么快、何时不快 · 读 "
        "`sklearn/utils/extmath.py` 里的分块处理："
        "大数据集要先分块、否则一次性构造的距离矩阵会直接 OOM——"
        "这正是本章 §1.2「广播的内存零拷贝本质与「内存爆炸」陷阱」的工业答案："
        "广播本身零拷贝，但「广播后的运算符」会把结果物化，"
        "所以 `(n,1) - (1,m)` 的中间结果是 `n×m` 而不是 `n+m`",

        "§1.1 一、广播的三条规则与形状推导 · 读 "
        "`notebooks/02.05-Computation-on-arrays-broadcasting.ipynb`："
        "它用 `(3,1)` 与 `(1,4)` 相加得到 `(3,4)` 的例子，"
        "把「缺的维补 1、1 可以拉伸」讲成一张图；"
        "配合本章 §1.2 看，就能分清「规则允许」与「内存真的被复制」是两件事——"
        "前者是语义，后者是 strides=0 的实现",

        "§3.2 二、`np.einsum` 与 stride tricks：零拷贝的张量收缩 · 读 "
        "`pandas/core/reshape/merge.py` 与 `pandas/core/groupby/groupby.py`："
        "pandas 的聚合底层把「按轴求和」翻译成 `einsum`/`dot`，"
        "走的是同一套 BLAS 路径，所以「einsum 写法性能接近 matmul」不是巧合；"
        "这也回答了本章 §3.1「何时不快」——"
        "一旦表达式涉及 fancy indexing（不连续访存），BLAS 的快路径就用不上了",

        "§2.1 一、旧式 `np.random` 全局 API 与新式 `Generator` · 读 "
        "`Data-Science-For-Beginners` 课程里的建模脚本："
        "所有 `train_test_split` 都带 `random_state`，"
        "否则「同一份代码两次结果不同」无法排查；"
        "本章 §2.2「可复现性、随机流与并行」的要点也在这里——"
        "旧式全局 API 共享一个隐式全局状态，多线程下会互相干扰，"
        "`Generator` 把状态装在实例里就是要解决这件事",
    ],

    # ---------------- data-ch03 Pandas 基础 ----------------
    "data-ch03": [
        "§4.2 2. 检测与处理缺失 · 读 `sklearn/impute/_base.py`："
        "`SimpleImputer` 的 `strategy` 与 pandas 的 `fillna` 是两套语义"
        "（前者在管道内、后者在数据上），混用时要注意「训练/推理口径一致」；"
        "本章 §4.1「缺失值的三种标记」正是这条差异的根源："
        "`np.nan` / `None` / `pd.NaT` 三者被判空的方式不同，"
        "`SimpleImputer` 只认 `np.nan` 与 `NaN` 语义",

        "§3.2 2. `iloc` 与 `loc` 的完整能力 · 读 "
        "`notebooks/03.02-Data-Indexing-and-Selection.ipynb`："
        "`loc` 闭区间、`iloc` 左闭右开——两种切片的边界规则不同，"
        "混用就是「取出来的行数不对」；"
        "本节 §3.3「链式赋值与 `SettingWithCopyWarning`」也在这里埋下伏笔："
        "`df[df.a > 0]['b'] = 1` 取到的是副本，赋值等于没做",

        "§1.1 1. 两个核心数据结构 · 读 `pandas/core/frame.py` 与 "
        "`pandas/core/internals/managers.py`："
        "DataFrame 不是「行列表」，而是「按 dtype 分块的二维结构」，"
        "这解释了「混类型列会让操作变慢」；"
        "本章 §1.2「自动对齐：Pandas 的灵魂」在这个结构上才说得通——"
        "对齐发生在每个 Series/Block 的索引上，而不是整行",

        "§2.3 3. 分块读：文件比内存大怎么办 · 读 "
        "`pandas/io/parsers/readers.py` 里 `read_csv` 的 `chunksize` 参数实现："
        "它返回的是一个迭代器，每次只解析一块，"
        "而不是「先全读进来再切」；"
        "这正是本节「文件比内存大」的答案，"
        "也解释了本章 §2.1「`read_csv` 的关键参数」里 `dtype` 为什么必须显式给——"
        "分块读时若靠推断，每一块的 dtype 可能都不同",
    ],

    # ---------------- data-ch04 Pandas 进阶 ----------------
    "data-ch04": [
        "§3.4 4. rolling / expanding / ewm：三种窗口 · 读 "
        "`pandas/core/resample.py` 与 `sklearn/model_selection/_split.py`："
        "时序窗口统计必须只用「过去的数据」，"
        "而 sklearn 的 `TimeSeriesSplit` 用分割而非窗口来强制这个边界；"
        "两者的分工在于：`rolling` 保证「单行特征不偷看未来」，"
        "`TimeSeriesSplit` 保证「训练集不偷看测试集」，"
        "本章 §2.3「多对多：行数膨胀」提醒的另一类泄漏则在合并阶段发生",

        "§2.2 2. 四种连接语义与 SQL 对照 · 读 "
        "`notebooks/03.07-Merge-and-Join.ipynb`："
        "inner/left/right/outer 的行数变化配了对照表，"
        "`indicator=True` 用来查「哪边没匹配上」；"
        "本节 §2.3「多对多：行数膨胀（本章最重要的一节）」正是这张表的极端情形——"
        "键不唯一时，行数是两边的笛卡尔积，而不是 max",

        "§1.1 1. 心智模型：split → apply → combine · 读 "
        "`pandas/core/groupby/groupby.py`："
        "先按键做哈希分组、再对每组应用聚合；"
        "`as_index=False` 与 `reset_index()` 的差别就出在「分组键是否进索引」，"
        "这正是本章 §1.4「命名聚合（Named Aggregation）」要绕开的坑——"
        "命名聚合直接产出扁平列名，省掉一次 `reset_index`",

        "§1.2 2. 四种聚合器：返回形状决定用途 · 读 "
        "`Data-Science-For-Beginners` 课程里的分组分析："
        "`count`/`nunique` 混用会把「订单数」算成「商品数」，"
        "指标定义要先写清再写代码；"
        "本章 §4.1「pivot_table：带默认聚合的 groupby」也一样——"
        "它默认用 `mean`，所以「销售额汇总」必须显式写 `aggfunc='sum'`，"
        "否则得到的是「平均每行金额」",
    ],

    # ---------------- data-ch05 数据采集 ----------------
    "data-ch05": [
        "§3.1 一、解析三件套：lxml / BeautifulSoup / 正则 · 读 "
        "`sklearn/utils/validation.py` 的 `check_array`："
        "形状、dtype、NaN 的检查顺序，"
        "可以直接照搬成「采集结果落库前」的自检清单；"
        "本节讲的是「怎么把 HTML 变成结构化数据」，"
        "而自检清单回答的是「变出来的东西能不能用」——"
        "这两步顺序颠倒，脏数据会一路流到建模阶段",

        "§2.3 三、会话复用与流式下载 · 读 "
        "`notebooks/03.07-Merge-and-Join.ipynb`："
        "层级索引能把「多来源数据」压进一个 DataFrame，"
        "比手工拼列更不容易错位；"
        "本节「会话复用」解决的是请求侧的成本，"
        "而层级索引解决的是落表侧的错位——"
        "采集多个页面时，`pd.concat(..., keys=[...])` 天然带上来源层级",

        "§3.4 四、从表格到 DataFrame：一次性说清 · 读 "
        "`pandas/io/json/_normalize.py`：`json_normalize` 把嵌套 JSON 拍平成表，"
        "是「采集 → 结构化」最常用的一步；"
        "本节要讲的「表格到 DataFrame」与它是对偶的两条路："
        "一个从 HTML `<table>` 解析出来、一个从嵌套 JSON 拍平，"
        "最终都要对齐到「一行一条记录」的口径",

        "§4.3 三、合规红线：这一节和技术同等重要 · 读 "
        "`Data-Science-For-Beginners` 的 `1-Introduction/` 里的数据伦理一课："
        "只采公开且允许抓取的数据、遵守 robots.txt 与频率限制——"
        "这条在本节有明确约束；"
        "本节 §4.4「把合规检查做成代码」的意思是："
        "把「是否允许抓」写成 `robots.txt` 解析 + 域名白名单，"
        "而不是写在 README 里靠自觉",
    ],

    # ---------------- data-ch06 数据分析与数学建模实战 ----------------
    "data-ch06": [
        "§4.1 一、建模流程：八步不可跳 · 读 `sklearn/pipeline.py`："
        "`Pipeline` 把「预处理 + 模型」串成一步，`fit` 只在训练集上调用——"
        "这是防泄漏的结构性保证，不是纪律问题；"
        "本章 §2.3「数据泄漏：三个真实场景」的前两个（缩放/编码在全量数据上 fit、"
        "用未来数据算特征）都能被 Pipeline 挡住，"
        "第三个（目标泄漏）挡不住，只能靠业务理解",

        "§3.3 三、相关系数三法：Pearson / Spearman / 互信息 · 读 "
        "`notebooks/05.02-Introducing-Scikit-Learn.ipynb`："
        "它先用散点图看关系再选模型，比盲试模型更快排除方向性错误；"
        "本节的价值就在于给出「看图之后用什么数说话」——"
        "Pearson 只看线性、Spearman 看单调、互信息能抓非单调关系，"
        "三者不一致时通常说明关系非线性",

        "§4.2 二、回归评价指标：五个数各自的脾气 · 读 "
        "`pandas/core/reshape/pivot.py` 与 `sklearn/metrics/_regression.py`："
        "前者把「模型 × 指标」摊成矩阵（写实验报告最省事的结构），"
        "后者给出 MAE/MSE/RMSE/MAPE/R² 的确切定义；"
        "本节要讲的「脾气」在源码里就是式子的差别："
        "MSE 平方放大离群点、MAPE 在真值为 0 时爆炸、R² 可以为负",

        "§4.4 四、数学建模：把开放题答成规范报告 · 读 "
        "`Data-Science-For-Beginners` 的 `4-Data-Science-Lifecycle/`："
        "先定义「成功标准」再选指标，"
        "否则模型分数再高也可能答错了问题；"
        "这正是本节「把开放题答成规范报告」的第一道工序——"
        "报告的结构（问题 → 假设 → 数据 → 方法 → 验证 → 结论）"
        "必须对应到一组可被判读的指标",
    ],
}


def split_note(note: str) -> tuple[str, str]:
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(cid: str, notes: list[str]) -> tuple[bool, str]:
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


def main() -> None:
    with open(MANIFEST, "rb") as fb:
        raw = fb.read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8"))
    changed = 0
    for ch in data.get("chapters", []):
        cid = ch.get("id") or ch.get("chapter_id")
        notes = NOTES.get(cid)
        if not notes:
            continue
        res = ch.get("resources") or {}
        cur = res.get("github_notes") or []
        if len(cur) != len(notes):
            print(f"!! {cid}: 原 {len(cur)} 条 / 新 {len(notes)} 条，不匹配，跳过")
            continue
        res["github_notes"] = notes
        ch["resources"] = res
        ok, msg = rewrite_goals_table(cid, notes)
        print(f"{'ok' if ok else '!!'} {cid}: manifest 已改，goals {msg}")
        changed += 1

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if nl == "\r\n":
        out = out.replace("\n", "\r\n")
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(f"\n完成 {changed} 章")


if __name__ == "__main__":
    main()
