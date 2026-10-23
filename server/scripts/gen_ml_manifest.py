"""生成 content/ml/_manifest.json —— 机器学习课程体系（章节划分对齐 B 站吴恩达课程）。

为什么按吴恩达的课程划分
--------------------------------------------------------------------
用户在 B 站跟的是吴恩达《机器学习》专项课程（2022 版，三门课 / 共 10 周）：

    课程一  Supervised Machine Learning: Regression and Classification
            W1 导论、监督/无监督、代价函数、梯度下降
            W2 多元线性回归、向量化、特征缩放、特征工程、多项式回归
            W3 逻辑回归、决策边界、过拟合与正则化
    课程二  Advanced Learning Algorithms
            W1 神经网络推理       W2 神经网络训练（激活/softmax/Adam/诊断）
            W3 应用机器学习建议   W4 决策树与集成
    课程三  Unsupervised Learning, Recommenders, Reinforcement Learning
            W1 K-means 与异常检测  W2 推荐系统  W3 强化学习

本学科的章节顺序与这三门课一一对应，便于「看一集 → 读一章 → 做一章题」。
两处刻意的差异（写在每章 summary 里）：

1. **神经网络只讲到「能解释、能实现一个最小 MLP」**：完整推导、CNN/RNN/Transformer、
   LLM 全部归 `ai` 学科。这是「机器学习 ≠ 深度学习」的分界，不是遗漏。
2. **吴恩达 2022 版砍掉的 SVM/核方法、PCA、工程化（特征存储/漂移）** 不在 8 章主线里，
   单独列为 `extensions`，避免假装覆盖。

star 数据来源：GitHub REST API，抓取于 2026-10-21。
用法：python server/scripts/gen_ml_manifest.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "content" / "ml" / "_manifest.json"
FETCHED_AT = "2026-10-21"

BILI_COURSE = "https://www.bilibili.com/video/BV164411b7dx/"
BILI_COLLECTION = "https://space.bilibili.com/589397373/lists/1844068"

# 真实仓库（full_name, stars, note），全部由 GitHub API 实测
GH = {
    "ml-ch01": [
        ("GokuMohandas/Made-With-ML", 49786, "生产级 ML 全流程：数据校验→训练→部署→监控，用来对照「课程里的玩具流程」与真实工程"),
        ("scikit-learn/scikit-learn", 67840, "工业标准 ML 库：每个算法的参考实现与 API 取舍"),
        ("datawhalechina/pumpkin-book", 26132, "西瓜书公式推导详解，补课程里跳过推导的部分"),
        ("apachecn/AiLearning", 42601, "《机器学习实战》中文笔记：经典算法的可运行实现"),
    ],
    "ml-ch02": [
        ("scikit-learn/scikit-learn", 67840, "linear_model 模块：闭式解、正则化与求解器选择的参考实现"),
        ("fengdu78/lihang-code", 19606, "《统计学习方法》全章代码：感知机、逻辑回归、最大熵"),
        ("rasbt/python-machine-learning-book", 12659, "算法手写 + sklearn 对照，适合核对公式与实现"),
        ("amueller/introduction_to_ml_with_python", 8220, "scikit-learn 作者写的入门书代码：讲清 API 背后的取舍"),
    ],
    "ml-ch03": [
        ("tensorflow/tensorflow", 201154, "吴恩达课程用 TensorFlow 演示；看 Keras 层的实现与自动微分"),
        ("microsoft/ML-For-Beginners", 91642, "微软 12 周 ML 课程，含神经网络与分类的配套 Notebook"),
        ("GokuMohandas/Made-With-ML", 49786, "把「训练一个网络」放进完整工程链路里看"),
    ],
    "ml-ch04": [
        ("scikit-learn/scikit-learn", 67840, "model_selection 与 metrics：交叉验证、学习曲线、指标口径"),
        ("GokuMohandas/Made-With-ML", 49786, "误差分析与上线前检查的工程范例"),
        ("optuna/optuna", 14945, "贝叶斯超参搜索：比手工网格更接近「应用建议」的自动化版本"),
        ("shap/shap", 25823, "特征重要性的可解释替代，避免只看树模型 importance"),
    ],
    "ml-ch05": [
        ("dmlc/xgboost", 28895, "课程 W4 直接讲到 XGBoost；这里看二阶泰勒与分裂增益的权威实现"),
        ("shap/shap", 25823, "TreeSHAP：树模型解释的工业标配"),
        ("lightgbm-org/LightGBM", 18897, "直方图分箱 + leaf-wise + GOSS/EFB，大规模数据的工程解法"),
        ("catboost/catboost", 9155, "有序目标统计解决类别特征泄漏"),
    ],
    "ml-ch06": [
        ("scikit-learn/scikit-learn", 67840, "cluster / covariance 模块：K-means、DBSCAN、GMM、异常检测"),
        ("jakevdp/PythonDataScienceHandbook", 50114, "《Python 数据科学手册》：聚类与密度估计的可视化讲解"),
        ("amueller/introduction_to_ml_with_python", 8220, "无监督方法的实际使用边界与常见误用"),
    ],
    "ml-ch07": [
        ("recommenders-team/recommenders", 21959, "微软推荐系统最佳实践：召回-排序-评测的完整链路"),
        ("RUCAIBox/RecBole", 4589, "统一推荐算法框架：100+ 模型的公平对比基线"),
        ("eugeneyan/applied-ml", 30664, "工业界推荐/搜索落地案例与经验教训"),
    ],
    "ml-ch08": [
        ("dennybritz/reinforcement-learning", 22153, "经典 RL 算法的 Notebook 实现：Q-learning、策略迭代、价值迭代"),
        ("ray-project/ray", 44096, "RLlib：从单机 Q-learning 到分布式 RL 的工程路径"),
        ("Farama-Foundation/Gymnasium", 12704, "课程 W3 的 Lunar Lander 就是 Gym 环境；看 env 接口与环境设计"),
    ],
}

CHAPTERS = [
    {
        "id": "ml-ch01",
        "order": 1,
        "group": "C1",
        "course": "课程一 · 监督学习：回归与分类",
        "week": "第 1 周",
        "title": "机器学习导论：范式、代价函数与梯度下降",
        "summary": (
            "对应吴恩达课程一第 1 周：什么是机器学习、监督学习与无监督学习的区别、"
            "回归与分类的任务形态、代价函数（平方误差）为什么长这样、梯度下降与学习率的直觉、"
            "凸函数为什么保证「局部最优即全局最优」。"
            "**本项目的加深**：把课程里「梯度下降就是往下走」补成可证明的收敛率（O(1/k)、"
            "强凸下的 (1−μ/L)^k）、条件数 κ 与特征标准化的关系、以及偏差-方差分解的完整推导——"
            "后者在课程里要到课程二第 3 周才出现，这里先建立理论框架，第 4 章再做诊断实操。"
        ),
        "prerequisites": [],
        "books": [
            "《机器学习》周志华 第1-2章（假设空间、归纳偏好、评估）",
            "《统计学习方法》李航 第1章（统计学习三要素）",
            "《The Elements of Statistical Learning》第2、7章（偏差-方差、模型复杂度）",
        ],
    },
    {
        "id": "ml-ch02",
        "order": 2,
        "group": "C1",
        "course": "课程一 · 监督学习：回归与分类",
        "week": "第 2-3 周",
        "title": "线性回归与逻辑回归：从最小二乘到正则化",
        "summary": (
            "对应课程一第 2-3 周：多特征线性回归、向量化为什么快、特征缩放与学习率、"
            "特征工程与多项式回归、逻辑回归与 sigmoid、决策边界、交叉熵代价函数、"
            "过拟合与正则化（λ 的作用）。"
            "**本项目的加深**：最小二乘的几何投影解释与正规方程的条件数问题、"
            "岭回归的谱滤波视角、Lasso 的稀疏几何与坐标下降、逻辑回归的牛顿法/IRLS、"
            "以及 softmax 多分类与 GLM 的统一框架——这些是课程里「知道怎么用」但没讲「为什么」的部分。"
        ),
        "prerequisites": ["ml-ch01"],
        "books": [
            "《统计学习方法》李航 第6章（逻辑回归与最大熵）",
            "《The Elements of Statistical Learning》第3章（最小二乘与岭回归）",
            "《机器学习》周志华 第3章（线性模型）",
        ],
    },
    {
        "id": "ml-ch03",
        "order": 3,
        "group": "C2",
        "course": "课程二 · 高级学习算法",
        "week": "第 1-2 周",
        "title": "神经网络：推理、训练与多分类（衔接 ai 学科）",
        "summary": (
            "对应课程二第 1-2 周：神经元与层、前向传播、用 TensorFlow/Keras 搭建网络、"
            "激活函数（ReLU/sigmoid/linear）的选择、多分类 softmax、Adam 优化器、"
            "反向传播的直觉、训练集/验证集诊断与正则化。"
            "**边界声明**：本章只讲到「能解释一层网络在算什么、能用 NumPy 手写一个最小 MLP」。"
            "完整推导（计算图、VJP、梯度消失机制、优化器演进）、CNN/RNN/Transformer 与 LLM "
            "全部在 `ai` 学科，不在这里重复——这是「机器学习 ≠ 深度学习」的分界。"
            "**本项目的加深**：把课程的「反向传播直觉」落实为一次手写链式法则 + 数值梯度校验。"
        ),
        "prerequisites": ["ml-ch02"],
        "books": [
            "《机器学习》周志华 第5章（神经网络）",
            "《深度学习》Goodfellow 第6章（反向传播）——仅第 6 章，其余归 ai 学科",
            "吴恩达课程二 W1-W2 的配套笔记",
        ],
    },
    {
        "id": "ml-ch04",
        "order": 4,
        "group": "C2",
        "course": "课程二 · 高级学习算法",
        "week": "第 3 周",
        "title": "应用机器学习：评估、偏差方差与误差分析",
        "summary": (
            "对应课程二第 3 周（吴恩达称之为「最有实用价值的一周」）："
            "训练/验证/测试集的划分、模型评估与选择、偏差与方差的诊断、学习曲线、"
            "误差分析、类别不平衡下的精确率/召回率、迁移学习、完整 ML 项目的工作流。"
            "**本项目的加深**：交叉验证的几种切分（分层/分组/时间序列）与嵌套 CV、"
            "五类数据泄漏的识别、指标的选择口径（ROC vs PR、AUC 的概率解释）与概率校准——"
            "这些是把「课程方法论」落到真实数据集上必须补的部分。"
        ),
        "prerequisites": ["ml-ch01", "ml-ch02"],
        "books": [
            "《机器学习》周志华 第2章（评估方法、性能度量、比较检验）",
            "《The Elements of Statistical Learning》第7章（模型评估与选择）",
            "《Designing Machine Learning Systems》Chip Huyen 第8章（误差分析与上线）",
        ],
    },
    {
        "id": "ml-ch05",
        "order": 5,
        "group": "C2",
        "course": "课程二 · 高级学习算法",
        "week": "第 4 周",
        "title": "决策树与集成学习：从信息增益到 XGBoost",
        "summary": (
            "对应课程二第 4 周：决策树的熵与信息增益、独热编码、连续特征的切分、回归树、"
            "随机森林、XGBoost 的使用与直觉。"
            "**本项目的加深**：信息增益/增益率/基尼的差异与偏好、预剪枝与后剪枝、"
            "Bagging 方差缩减的推导、GBDT 的加法模型与负梯度拟合、XGBoost 的二阶泰勒与分裂增益公式、"
            "LightGBM 的直方图/leaf-wise/GOSS——课程里「会用 XGBoost」到「知道它为什么赢」之间的那段推导。"
        ),
        "prerequisites": ["ml-ch02"],
        "books": [
            "《机器学习》周志华 第4章（决策树）、第8章（集成学习）",
            "《The Elements of Statistical Learning》第9-10章（树、Boosting）",
            "XGBoost 论文：Chen & Guestrin, 2016",
        ],
    },
    {
        "id": "ml-ch06",
        "order": 6,
        "group": "C3",
        "course": "课程三 · 无监督、推荐与强化学习",
        "week": "第 1 周",
        "title": "无监督学习：K-means、异常检测与 GMM",
        "summary": (
            "对应课程三第 1 周：K-means 的步骤与目标函数、簇数选择、"
            "异常检测（高斯密度估计、阈值 ε 的选择）、以及 GMM 与 EM 的直觉。"
            "**本项目的加深**：Lloyd 迭代的单调性、K-means++ 初始化、轮廓系数、"
            "DBSCAN 的密度视角、EM 的下界构造与单调收敛证明、GMM 与 K-means 的硬/软分配关系——"
            "课程里「看起来像 K-means 的软版本」在数学上到底差在哪。"
        ),
        "prerequisites": ["ml-ch02"],
        "books": [
            "《机器学习》周志华 第9章（聚类）",
            "《统计学习方法》李航 第9章（EM 算法）",
            "《Pattern Recognition and Machine Learning》第9章（混合模型与 EM）",
        ],
    },
    {
        "id": "ml-ch07",
        "order": 7,
        "group": "C3",
        "course": "课程三 · 无监督、推荐与强化学习",
        "week": "第 2 周",
        "title": "推荐系统：协同过滤与矩阵分解",
        "summary": (
            "对应课程三第 2 周：协同过滤、用户/物品特征、矩阵分解、均值归一化、"
            " finding related items、用 TensorFlow 实现推荐模型。"
            "**本项目的加深**：user/item-based 相似度的取舍、矩阵分解的 SGD/ALS 推导、"
            "BPR 排序损失、隐式反馈与负采样、冷启动的混合策略，以及推荐系统的评测口径"
            "（Recall@K/NDCG）与线上 A/B 的关系——课程里没展开的「离线指标怎么对应线上收益」。"
        ),
        "prerequisites": ["ml-ch02", "ml-ch06"],
        "books": [
            "《推荐系统实践》项亮（协同过滤与评测）",
            "《深度学习推荐系统》王喆（召回-排序-工程链路）",
            "吴恩达课程三 W2 的配套笔记",
        ],
    },
    {
        "id": "ml-ch08",
        "order": 8,
        "group": "C3",
        "course": "课程三 · 无监督、推荐与强化学习",
        "week": "第 3 周",
        "title": "强化学习：马尔可夫决策过程与 Q-learning",
        "summary": (
            "对应课程三第 3 周：什么是强化学习、马尔可夫决策过程（状态/动作/奖励/折扣因子）、"
            "回报与策略、Q-learning 与 Bellman 方程、ε-greedy 探索、连续状态空间、Lunar Lander 实战。"
            "**本项目的加深**：Bellman 最优性算子的压缩映射与收敛性、"
            "on-policy 与 off-policy 的分野、函数逼近（DQN 的最小实现）与「为什么 RL 难复现」，"
            "以及与监督学习的根本差异（数据分布依赖策略，i.i.d. 假设失效）。"
        ),
        "prerequisites": ["ml-ch02"],
        "books": [
            "《Reinforcement Learning: An Introduction》Sutton & Barto 第3、6章",
            "吴恩达课程三 W3 的配套笔记",
            "David Silver 的 RL 课程讲义（UCL）",
        ],
    },
]

# 吴恩达 2022 版未覆盖、但对工程/自命题考试重要的专题：单列，不伪装成已完成章节
EXTENSIONS = [
    {"key": "svm", "title": "支持向量机与核方法",
     "why": "经典课程有、2022 版删除；自命题 AI 专业课仍常考间隔与对偶推导",
     "entry": "间隔最大化 → 拉格朗日对偶 → KKT 稀疏性 → 核技巧"},
    {"key": "pca", "title": "PCA 与降维",
     "why": "课程三只讲 K-means；PCA 是数据预处理与可视化的常备工具",
     "entry": "最大方差 = 最小重构 → SVD 实现 → 方差解释率"},
    {"key": "feature-engineering", "title": "特征工程与 MLOps",
     "why": "课程给了方法论，但真实项目的泄漏、特征存储、漂移监控需要单独展开",
     "entry": "泄漏五类 → 目标编码 OOF → 特征存储 → PSI 漂移"},
]

MANIFEST = {
    "schema_version": 1,
    "subject": "ml",
    "title": "CppMind · 机器学习课程体系（对齐吴恩达 B 站课程）",
    "note": (
        "章节划分对齐 B 站吴恩达《机器学习》专项课程（2022 版三门课、共 10 周）："
        "课程一 监督学习（回归与分类）→ 课程二 高级学习算法（神经网络/应用建议/决策树）→ "
        "课程三 无监督、推荐与强化学习。每章标注对应周次，可「看一集 → 读一章 → 做一章题」。"
        "**与 ai 学科的分界**：本学科只讲到「能解释并能手写一个最小 MLP」，"
        "反向传播的完整推导、CNN/RNN/Transformer、LLM、RAG、Agent 全部归 `ai` 学科；"
        "课程二里的神经网络部分因此只保留直觉与最小实现，不重复深度学习内容。"
        "吴恩达 2022 版删掉的 SVM、PCA、工程化专题单列在 `extensions`，不冒充章节。"
        "每章须齐备 7 类内容（见 _template 规范），resources 仅存元数据与链接，符合合规红线。"
    ),
    "source_course": {
        "name": "吴恩达《机器学习》专项课程（2022）",
        "bilibili": BILI_COURSE,
        "bilibili_note": "B 站中英字幕版（经典全课程）；2022 版三门课合集见 up 主列表",
        "bilibili_collection": BILI_COLLECTION,
        "structure": [
            {"course": "课程一", "title": "Supervised Machine Learning: Regression and Classification",
             "weeks": ["W1 导论/代价函数/梯度下降", "W2 多元线性回归/向量化/特征工程", "W3 逻辑回归/正则化"],
             "chapters": ["ml-ch01", "ml-ch02"]},
            {"course": "课程二", "title": "Advanced Learning Algorithms",
             "weeks": ["W1 神经网络推理", "W2 神经网络训练", "W3 应用机器学习建议", "W4 决策树与集成"],
             "chapters": ["ml-ch03", "ml-ch04", "ml-ch05"]},
            {"course": "课程三", "title": "Unsupervised Learning, Recommenders, Reinforcement Learning",
             "weeks": ["W1 K-means/异常检测", "W2 推荐系统", "W3 强化学习"],
             "chapters": ["ml-ch06", "ml-ch07", "ml-ch08"]},
        ],
    },
    "groups": {
        "C1": "课程一 · 监督学习：回归与分类",
        "C2": "课程二 · 高级学习算法",
        "C3": "课程三 · 无监督、推荐与强化学习",
    },
    "chapters": [],
    "extensions": EXTENSIONS,
    "github_resources": [],
    "resources_fetched_at": FETCHED_AT,
}


def build_resources(chapter_id: str) -> dict:
    gh = GH.get(chapter_id, [])
    return {
        "github": [r[0] for r in gh],
        "github_stars": [r[1] for r in gh],
        "github_notes": [r[2] for r in gh],
        "github_fetched_at": FETCHED_AT,
        "bilibili": BILI_COURSE,
        "books": [],
        "leetcode": [],
        "nowcoder": [],
    }


def main() -> int:
    chapters = []
    for ch in CHAPTERS:
        item = dict(ch)
        item["status"] = "complete"
        item["resources"] = build_resources(ch["id"])
        chapters.append(item)
    MANIFEST["chapters"] = chapters

    seen: dict[str, dict] = {}
    for ch in CHAPTERS:
        for repo, stars, note in GH[ch["id"]]:
            if repo not in seen or stars > seen[repo]["stars"]:
                seen[repo] = {"repo": repo, "stars": stars,
                              "url": f"https://github.com/{repo}", "note": note}
    MANIFEST["github_resources"] = sorted(seen.values(), key=lambda x: -x["stars"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"写入 {OUT.relative_to(ROOT)}：{len(chapters)} 章 / "
          f"{len(MANIFEST['github_resources'])} 个 GitHub 仓库 / "
          f"{len(EXTENSIONS)} 个拓展专题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
