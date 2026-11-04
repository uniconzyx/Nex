# -*- coding: utf-8 -*-
"""批次二 · 来源颗粒度补齐：ml 8 章（ml-ch01 ~ ml-ch08）

与 inject_sources_agent.py 完全同一套路（表格改写、CRLF 写盘、` · ` 拆分），
只是换了目标学科与章节。共用逻辑见那个文件的说明，这里只写差异与内容。

ml-ch09 不在本批
----------------
ml-ch09 的 notes 已经是合格写法（`svm.cpp` 的 `Solver::Solve`、
`sklearn/svm/` 封装层、`SVC` 默认 OvO 等），不改——改了反而破坏。

为什么是这 8 章
---------------
判定口径：notes 里没有反引号包住的入口文件/目录，或没有 §小节号。
这类描述读者无法落到具体位置，等于「学科级复制」的软形式
（audit_sources 的 route_key 去重查不出，因为它只比整组是否完全相同）。

三要素（与 agent 批一致）
------------------------
  §小节号 + `入口文件/目录` + 证明本章哪条结论

每条写成 "<对应本章> · <读什么>"，脚本按 ` · ` 切开：
前半进 goals.md 表格的「对应本章」列，后半进「读什么」列。
**分隔符必须是前后各一个半角空格**——写成 `）· §` 会让 split 静默失败，
整条被塞进「读什么」而「对应本章」退回「全章」（agent 批踩过，返工两次）。
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
ML_DIR = os.path.join(ROOT, "content", "ml")
MANIFEST = os.path.join(ML_DIR, "_manifest.json")

# GitHub 资源表行：| n | [owner/repo](url) | 12,345 | 对应本章 | 读什么 |
RE_GH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|\s*(.*?)\s*\|\s*$"
)

NOTES = {
    # ── ch01 机器学习基础与范式 ──────────────────────────────────────
    "ml-ch01": [
        "§2.从分解到工程：三个可控项 · §5.样本复杂度与学习曲线："
        "`mlops/` 下从数据校验到监控的每一环都有可跑的 notebook，"
        "读它的数据切片与验证策略，对照本章「可控项只有三个」",
        "§1.形式化：一个学习问题由五件东西组成 · §1.四种学习范式："
        "`sklearn/api_reference.py` 的 `estimator_type` 字段把 classifier / regressor / "
        "clusterer 写成了显式属性——「监督信号从哪来」在 API 层是可读的",
        "§2.分解的完整推导 · §4.正则化的两种解释："
        "`pumpkin-book` 的附录把西瓜书的偏差-方差分解逐行展开，"
        "第 2 章对应的推导正好补本章「这一步必须会写」",
        "§3.SGD 用方差换速度 · §6.把学习看成压缩："
        "`src/` 里各算法的纯 NumPy 实现（没有 sklearn 封装）适合核对公式，"
        "对照本章「归纳偏置决定你能不能学」",
    ],
    # ── ch02 线性模型与正则化 ───────────────────────────────────────
    "ml-ch02": [
        "§1.岭回归闭式解与谱滤波 · §2.Lasso 的 L1 稀疏几何："
        "`sklearn/linear_model/_ridge.py` 里 `_solve_svd` 与 `_solve_cholesky` 是两条路径，"
        "读它为什么默认走 SVD，就懂本章「条件数被平方放大」",
        "§3.交叉熵 = 极大似然（为什么不用 MSE） · §2.软阈值："
        "`lihang-code` 第 6 章逻辑回归与第 7 章 SVM 的代码连起来看，"
        "「为什么平方损失在这里不对」在梯度表达式上就看得出来",
        "§1.正规方程与数值稳定性 · §4.弹性网在相关特征上救 Lasso："
        "`code/` 每章都是手写实现 + sklearn 对照，"
        "把自己的手推结果和它的输出逐项核，公式错在哪一眼可见",
        "§5.L1/L2 的贝叶斯先验（拉普拉斯 vs 高斯） · §2.Lasso 稀疏几何："
        "`notebooks/` 里 L1/L2 的几何示意图是画出来的，"
        "对照本章「先验不同所以稀疏性不同」，比纯公式直观",
    ],
    # ── ch03 神经网络基础 ───────────────────────────────────────────
    "ml-ch03": [
        "§2.一层：矩阵形式与维度约定 · §3.为什么必须有非线性："
        "`keras/src/layers/core/dense.py` 里 `call()` 就是 `x @ kernel + bias` 一行，"
        "读它确认本章「维度约定」到底是怎么落地的",
        "§1.一个神经元：加权和 + 偏置 + 激活 · §4.激活函数怎么选："
        "`lessons/` 里的分类与神经网络 Notebook 都能直接跑，"
        "换激活函数重训一次，看本章「多层线性仍是线性」的实验证据",
        "§6.训练循环的常见 bug · §2.数值梯度校验："
        "`mlops/` 把训练放进完整工程链路（含数据校验与测试），"
        "它的测试用例正好是本章「手写网络要用数值梯度兜底」的实践版",
    ],
    # ── ch04 评估与指标 ─────────────────────────────────────────────
    "ml-ch04": [
        "§2.交叉验证把划分的运气摊平 · §3.切分策略必须匹配依赖结构："
        "`sklearn/model_selection/_split.py` 里 `TimeSeriesSplit` 与 `GroupKFold` 是两条独立分支，"
        "读它为什么不能对时序用 KFold，就懂本章「切分要匹配依赖」",
        "§2.学习曲线让诊断可复现 · §2 天花板：什么时候不该再调："
        "`mlops/` 的评估与监控章节给了「上线前检查清单」，"
        "对照本章「训练/验证误差四象限」逐条核",
        "§4.阈值是业务参数（代价矩阵） · §1.六个指标与各自盲区："
        "`study/` 里有贝叶斯超参搜索的 notebook，"
        "它把「搜索目标」显式写成 metric——本章「选错指标等于调错方向」的实证",
        "§5.概率校准（分数可排序不代表概率可信） · §1.混淆矩阵家族："
        "`shap` 的 `plots/` 把「模型凭什么这么判」画出来，"
        "补本章「不能只看 importance 一个数」那一条",
    ],
    # ── ch05 树模型与集成 ───────────────────────────────────────────
    "ml-ch05": [
        "§2.XGBoost 二阶泰勒与分裂增益 · §1.加法模型与负梯度："
        "`src/tree/split_evaluator.h` 里 `CalcSplitGain` 就是本章那条分裂增益公式的实现，"
        "对照着读能看出正则项是怎么扣的",
        "§1.连续特征切分点（相邻取值中点） · §3 树模型解释："
        "`shap/explainers/_tree.py` 的 TreeSHAP 是精确解而非采样近似，"
        "读它就知道本章「树重要性会偏向高基数特征」为什么不适用于 SHAP 值",
        "§3.LightGBM 三板斧（直方图/leaf-wise/GOSS） · §2.方差缩减："
        "`src/io/` 与 `src/treelearner/` 分别是直方图分箱与 leaf-wise 生长，"
        "两处一读，本章「为什么 LightGBM 比 XGBoost 快」有了依据",
        "§1 类别特征处理 · §2.特征抽样与去相关："
        "`catboost/` 的 ordered target statistics 解决的是目标泄漏，"
        "正好对照本章「普通 target encoding 会把标签漏进特征」",
    ],
    # ── ch06 聚类与密度估计 ─────────────────────────────────────────
    "ml-ch06": [
        "§2.Lloyd 迭代两步各自最优 · §4.k-means++ 的概率保证："
        "`sklearn/cluster/_kmeans.py` 里 `_k_init` 就是 k-means++ 的实现，"
        "读它「按 D² 加权抽样」几行，本章「把运气变成概率保证」就落地了",
        "§1.目标函数畸变 J · §6.失效边界（球状/等方差/同密度）："
        "`notebooks/` 里聚类章节全是可视化，"
        "拿不同形状的合成数据跑一遍，本章失效条件当场可见",
        "§3.多元高斯的协方差结构 · §2.ε 怎么选用 F1 口径："
        "`notebooks/` 的 GMM 与密度估计部分画了等高线，"
        "对照本章「谁定义了异常」——协方差选 full 还是 diag 决定了判据",
    ],
    # ── ch07 推荐系统 ───────────────────────────────────────────────
    "ml-ch07": [
        "§1.召回-排序链路 · §2.离线指标的口径（先把分母说清楚）："
        "`examples/` 下每个 notebook 都从数据处理跑到评测，"
        "读它的评测单元就知道本章「分母不同指标不可比」指什么",
        "§3.SGD 一次一个观测 · §4.ALS 固定一侧有闭式解："
        "`recbole/model/` 里 MF 与 BPR 是分开的两个类，"
        "两者的 loss 与采样方式并排看，本章「优化排序 vs 优化评分」的差别一目了然",
        "§6.流行度偏差与去偏 · §3.离线评估与线上 A/B 的差距："
        "`README` 的 case study 收录了推荐系统线上踩坑，"
        "对照本章「离线涨了线上掉」的三种常见原因",
    ],
    # ── ch08 强化学习 ───────────────────────────────────────────────
    "ml-ch08": [
        "§3 动态规划三件套 · §2.Bellman 最优方程："
        "`DP/` 下策略评估、策略迭代、价值迭代是三个独立 notebook，"
        "并排跑一次，本章「一个 max 让问题质变」在代码上看得见",
        "§4 装上神经网络：致命三要素 · §5 为什么 RL 难复现："
        "`rllib/algorithms/` 里每个算法都配了 tuned example，"
        "「换个环境超参全废」正是本章「难复现是方法问题」的证据",
        "§3.Q-learning 与 SARSA 差一个 max · §3.ε-greedy："
        "`gymnasium/envs/` 的 `step()` 返回五元组（含 truncated），"
        "读它区分 terminated 与 truncated，就懂本章「回合结束不等于失败」为什么会影响 TD 目标",
    ],
# ── ch09 支持向量机与核方法 ──────────────────────────────────────
    "ml-ch09": [
        "§1.最大间隔 · §2.拉格朗日对偶："
        "`svm.cpp` 的 `Solver::Solve` 与 `select_working_set` 就是本章 ex07/ex08 的工程版，"
        "读它「每次只动两个乘子」的选取规则，本章「对偶把约束变成内积」有了实现依据",
        "§3.为什么对偶值得单独学 · §3 原始形式的适用面："
        "`linear.cpp` 直接在原始形式做坐标下降，"
        "对照本章「n 大且不核化时别走对偶」，就知道两条路的分岔点在哪",
        "§3.求解与工程：SMO、多分类与大规模 · §3 概率校准："
        "`sklearn/svm/` 的封装层确认 `SVC` 默认 OvO、`LinearSVC` 默认 OvR、"
        "`probability=True` 内部走 5 折 Platt——本章「置信度要额外校准」的原型",
        "§3.SMO 的单步更新 · §2.核的选择："
        "`lihang-code` 第 7 章是教学版 SMO，可与本章推导逐行对照，"
        "看它的启发式选点比自己的实现快在哪",
    ],
}


def split_note(note: str) -> tuple[str, str]:
    """把 "<对应本章> · <读什么>" 拆成两栏；无分隔符则整条进「读什么」。"""
    if " · " not in note:
        return "全章", note
    head, tail = note.split(" · ", 1)
    return head.strip(), tail.strip()


def rewrite_goals_table(ch_dir: str, cid: str) -> tuple[bool, str]:
    """只改「## 本章 GitHub」小节内的 `| n |` 表格行。

    B 站小节的表格同样 5 列、同样以 `| 1 |` 开头（区别是第 2 列是链接而非仓库名），
    全文件扫会把视频说明覆盖掉，所以必须先框定小节范围。
    """
    path = os.path.join(ch_dir, "goals.md")
    if not os.path.exists(path):
        return False, "goals.md 不存在"

    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    notes = NOTES.get(cid) or []
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## 本章 GitHub"))
    except StopIteration:
        # ml-ch09 缺失该小节标题：表格直接接在上一节后面。
        # 标题是 goals.md 的章节骨架（也是 audit 定位资源段的锚），必须补上，
        # 否则读者在页面里看到的是一张没有标题的裸表。
        anchor = next(
            (i for i, ln in enumerate(lines)
             if ln.startswith("## ") and "B 站" in ln),
            None,
        )
        first_row = next(
            (i for i, ln in enumerate(lines) if RE_GH_ROW.match(ln)), None
        )
        if first_row is None or anchor is None:
            return False, "找不到「## 本章 GitHub」小节且无法定位表格"
        lines.insert(first_row, "## 本章 GitHub 学习路线（按阅读顺序）")
        lines.insert(first_row + 1, "")
        start = first_row

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    row_idx = 0
    for i in range(start, end):
        m = RE_GH_ROW.match(lines[i])
        if not m:
            continue
        num, name, url, star, _c, _r = m.groups()
        if row_idx >= len(notes):
            row_idx += 1
            continue
        corner, read = split_note(notes[row_idx])
        lines[i] = f"| {num} | [{name}]({url}) | {star} | {corner} | {read} |"
        row_idx += 1

    if row_idx == 0:
        return False, "GitHub 表格没匹配到任何行"

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return True, f"表格 {row_idx} 行"


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as f:
        data = json.load(f)

    by_id = {c.get("id"): c for c in (data.get("chapters") or [])}

    n = 0
    for cid, notes in NOTES.items():
        c = by_id.get(cid)
        if not c:
            print(f"!! 找不到章节 {cid}")
            continue
        res = c.setdefault("resources", {})
        repos = res.get("github") or []
        if len(repos) != len(notes):
            print(f"!! {cid} 仓库 {len(repos)} 个、notes {len(notes)} 条，不匹配，跳过")
            continue
        res["github_notes"] = notes
        n += 1
        ok, msg = rewrite_goals_table(os.path.join(ML_DIR, cid), cid)
        print(f"  {cid:<10} {len(notes)} 条 · {'✓' if ok else '✗'} {msg:<12} · {notes[0][:26]}…")

    # 换行格式**按学科探测**：agent/ml/cpp 是 CRLF，其余 11 个学科是 LF。
    # 写死任一种都会让另一种学科整份假 diff，这里统一读一次原文件判断。
    with open(MANIFEST, "rb") as fb:
        nl = "\r\n" if b"\r\n" in fb.read() else "\n"
    with open(MANIFEST, "w", encoding="utf-8", newline=nl) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n写入 {os.path.normpath(MANIFEST)}，共更新 {n} 章")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
