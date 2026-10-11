# data-ch06 · 数据分析与数学建模实战

## 一、这一章要把前面所有零件装成一台机器

`data-ch01`~`data-ch05` 教的是零件：数组运算、广播、Series/DataFrame、分组聚合、采集与清洗。
本章是**装配线**：一份脏数据 → 质量诊断 → 特征工程 → 探索分析 → 建模 → 评估 → 结论。

真正的分水岭不在"会不会调 API"，而在**能不能对自己的结论负责**：
- 你的缺失值处理是否引入了偏差？
- 你的特征里有没有"未来信息"（数据泄漏）？
- 你的指标在类别不平衡时还有意义吗？
- 你的结论做了**灵敏度分析**吗？换个假设还成立吗？

## 二、学完之后你应该能做到

1. 拿到任何一份表，先跑**质量体检**（缺失、重复、异常、类型、取值域），并给出可执行的处置。
2. 区分缺失机制（MCAR / MAR / MNAR），并据此选择删除、单值填充、统计填充还是模型填充。
3. 用 Z-score / IQR / 分位数三种方法做异常检测，说明各自在什么分布假设下成立。
4. 正确使用标准化、归一化、Robust 缩放，并说清哪些模型**必须**缩放。
5. 识别并杜绝**数据泄漏**（目标编码泄漏、时间穿越、预处理在划分前做）。
6. 按"要表达什么关系"选择图表，而不是按"我会画哪种图"。
7. 手工算出 MAE / RMSE / R² / 精确率 / 召回率 / F1 / AUC，并解释它们在什么场景会误导。
8. 按数学建模的规范流程写出一份有**假设、符号、求解、灵敏度分析**的完整答案。

## 三、本章结构

| # | 概念文件 | 核心内容 |
|---|---|---|
| 1 | `01-cleaning-and-quality-checks.md` | 质量体检清单、缺失机制与填充策略、异常检测、去重与一致性 |
| 2 | `02-feature-engineering.md` | 缩放、类别编码、分箱、派生特征、**数据泄漏**与防范 |
| 3 | `03-eda-and-visualization.md` | EDA 提问法、图表选型矩阵、四类关系（分布/关系/时间/构成） |
| 4 | `04-modeling-metrics-and-math-modeling.md` | 建模流程、回归/分类评价指标、交叉验证、**数学建模论文结构** |

## 四、动手实践（建议顺序）

1. `ex01`~`ex04`：质量体检 → 缺失填充对比 → 异常检测三法 → 缩放对比。
2. `ex05`~`ex08`：类别编码与泄漏 → 相关性三法 → 回归指标 → 分类指标与不平衡。
3. `ex09`~`ex12`：缩放对距离模型的影响 → 划分与泄漏实证 → 灵敏度分析 → 端到端案例。

> 本机**没有 sklearn / scipy / statsmodels**，所以全部示例用 `numpy` + `pandas` **从零实现**。
> 这不是退让：手写一遍指标与模型，你对"公式"和"库调用"的关系才真正清楚——
> 而且能亲手验证「库的输出 = 公式的结果」。

## 五、自检清单

- [ ] 能说出 MCAR / MAR / MNAR 的区别，以及"删除"在哪种机制下会引入偏差
- [ ] 能用 IQR 规则算出上下界，并解释 1.5 这个系数的含义
- [ ] 能说出标准化与归一化的公式差异，以及为什么 SVM/KNN/PCA 必须缩放而决策树不必
- [ ] 能举出三种数据泄漏的具体例子，并说出防范手段
- [ ] 能解释为什么类别不平衡时 accuracy 会"骗人"，该看什么指标
- [ ] 能解释 AUC 的概率含义（随机取一对正负样本，正样本得分更高的概率）
- [ ] 能在数学建模题里写出假设、符号说明、模型建立、求解、灵敏度分析五段


## 本章 GitHub 资源（大纲实时抓取，star 最高）

| 仓库 | star | 用途 |
|---|---|---|
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | 67487 | 经典机器学习库官方仓库：算法实现与最佳实践 |
| [jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 50114 | 《Python 数据科学手册》全书 Jupyter Notebook（NumPy/Pandas/Matplotlib） |
| [pandas-dev/pandas](https://github.com/pandas-dev/pandas) | 49928 | Pandas 官方仓库：API 与内部机制权威来源 |
| [microsoft/Data-Science-For-Beginners](https://github.com/microsoft/Data-Science-For-Beginners) | 37525 | 微软官方 10 周数据科学课程 |

> 资源由 `server/scripts/sync_github_resources.py` 从 GitHub API 实时抓取并固化到 `_manifest.json`，star 数以文件内 `github_fetched_at`(2026-09-21) 为准。

## 本章 B 站视频教程（与 GitHub 代码资源互补）

> 视频来源均来自 B 站（bilibili.com）。与上方 GitHub 仓库互为补充：**GitHub 看工业级源码实现，B 站看原理讲解与「从零手搓」演示**。

| UP 主 / 系列 | 链接 | 对应本章内容 |
|---|---|---|
| 黑马程序员 · Python 数据分析教程 | [视频](https://www.bilibili.com/video/BV1hx411d7jb/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 莫烦 Python · Numpy & Pandas 数据处理 | [视频](https://www.bilibili.com/video/av16378934/) | 本学科配套视频，建议结合本章示例与习题观看 |
| Datawhale · 巨硬的 NumPy（视频） | [视频](https://www.bilibili.com/video/BV1Ym4y1U7at/) | 本学科配套视频，建议结合本章示例与习题观看 |
| 北京理工大学 · Python 数据分析与展示 | [视频](https://www.bilibili.com/video/av10101509/) | 本学科配套视频，建议结合本章示例与习题观看 |
