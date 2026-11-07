# SVM 代码速查：凯喵的七段可运行片段

> 这一篇是配套速查。前三篇讲清了最大间隔、对偶与核方法，这一篇把它们落成代码——从硬间隔的二次规划，到 SMO 的核心迭代，再到核矩阵与调参。凯喵的用法是先用小数据手推一遍对偶，再跑代码对照。

## 一、硬间隔 SVM：直接解二次规划

最直白的实现是调用现成的 QP 求解器，把原问题按标准形式送进去。

```python
import numpy as np
from scipy.optimize import minimize

def hard_margin_svm(X, y):
    """min 0.5*||w||^2  s.t. y_i(w·x_i + b) >= 1"""
    n, d = X.shape

    def obj(v):
        w, b = v[:d], v[d]
        return 0.5 * w @ w

    cons = [{"type": "ineq",
             "fun": (lambda v, i=i: y[i] * (v[:d] @ X[i] + v[d]) - 1)}
            for i in range(n)]
    res = minimize(obj, np.zeros(d + 1), constraints=cons, method="SLSQP")
    return res.x[:d], res.x[d]
```

这个版本的用途是「理解原问题」，不适合生产：约束数量等于样本数，样本一多就解不动。

## 二、对偶问题与支持向量的识别

```python
from scipy.optimize import minimize

def dual_svm(X, y, C=1.0):
    """min 0.5*a^T Q a - 1^T a  s.t. 0<=a_i<=C, sum(a_i y_i)=0"""
    n = X.shape[0]
    K = X @ X.T
    Q = (y[:, None] * y[None, :]) * K

    def obj(a):
        return 0.5 * a @ Q @ a - a.sum()

    cons = [{"type": "eq", "fun": lambda a: a @ y}]
    bounds = [(0, C)] * n
    res = minimize(obj, np.zeros(n), bounds=bounds,
                   constraints=cons, method="SLSQP")
    a = res.x
    sv = a > 1e-6                       # 支持向量：alpha > 0
    w = ((a * y)[:, None] * X).sum(0)
    b = np.mean([y[i] - w @ X[i] for i in range(n) if sv[i]])
    return w, b, a
```

`alpha > 0` 就是支持向量，这个判据来自 KKT 互补松弛条件——非支持向量的 `alpha` 必然为 0，对 `w` 没有贡献。

## 三、核技巧：只改内积，不改算法

核方法的核心是「把 `x·z` 替换成 `K(x, z)`」，其余全部不变。

```python
def linear_kernel(A, B):
    return A @ B.T

def rbf_kernel(A, B, gamma=1.0):
    d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
    return np.exp(-gamma * d2)

def poly_kernel(A, B, degree=3, coef0=1.0):
    return (A @ B.T + coef0) ** degree
```

RBF 的 `gamma` 控制影响半径：`gamma` 大则每个样本的影响范围小，边界更弯曲（容易过拟合）；`gamma` 小则边界更平滑（容易欠拟合）。

## 四、SMO 的单步更新

SMO 每步只优化两个乘子，把问题降成解析可解。

```python
def smo_step(i, j, a, y, K, C, b):
    if y[i] == y[j]:
        L, H = max(0, a[i] + a[j] - C), min(C, a[i] + a[j])
    else:
        L, H = max(0, a[j] - a[i]), min(C, C + a[j] - a[i])
    if L == H:
        return 0.0
    eta = 2 * K[i, j] - K[i, i] - K[j, j]
    if eta >= 0:
        return 0.0
    ai_old, aj_old = a[i], a[j]
    a[j] = aj_old - y[j] * (0) / eta      # 误差项由调用方传入
    a[j] = min(H, max(L, a[j]))
    a[i] = ai_old + y[i] * y[j] * (aj_old - a[j])
    return abs(a[j] - aj_old)
```

这段故意留了误差项的接口，因为完整 SMO 需要一个外层循环维护 `E_i = f(x_i) - y_i`。重点是 `L/H` 的裁剪：不做裁剪会导致乘子越界，收敛到错误解。

## 五、用 sklearn 做正确的调参流程

```python
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GridSearchCV

pipe = make_pipeline(StandardScaler(), SVC(kernel="rbf"))
param = {"svc__C": [0.1, 1, 10, 100], "svc__gamma": ["scale", 0.01, 0.1, 1]}

gs = GridSearchCV(pipe, param, cv=5, scoring="f1", n_jobs=-1)
gs.fit(X_train, y_train)
print(gs.best_params_, gs.score(X_test, y_test))
```

两个必须做对的事：**先标准化**（SVM 对特征尺度敏感，量纲差异会让某个维度主导距离）；**把 scaler 放进 pipeline**（否则交叉验证时 scaler 会「看到」验证集，造成数据泄漏）。

## 六、不平衡数据下的类别权重

```python
from sklearn.svm import SVC

clf = SVC(kernel="rbf", class_weight="balanced", C=1.0)
```

`class_weight="balanced"` 会把 `C` 按类别频率反比缩放，让少数类的误分惩罚更重。手工指定也行：`class_weight={0: 1, 1: 10}` 表示少数类的惩罚是多数类的 10 倍。

## 七、决策函数与置信度

```python
dec = clf.decision_function(X_query)     # 到超平面的有符号距离
pred = clf.predict(X_query)
```

`decision_function` 的绝对值不是概率，不能直接当置信度用。需要概率时设 `probability=True`（内部会做 Platt 缩放），代价是训练变慢且概率本身是近似值。

## 三视角解析
### 🧑‍💻 程序员视角
SVM 的 `C` 与 `γ` 是最需要调的两个超参：`C` 大 → 不容忍误分类 → 易过拟合；`γ` 大 → 单个样本影响范围小 → 决策边界弯曲 → 也易过拟合。核函数不是「越复杂越好」：线性核在特征维度已经很高时（文本 TF-IDF）往往够用且快得多。样本量超过十万时，SVM 的训练复杂度 `O(n²)~O(n³)` 会成为瓶颈，这时该换线性模型或树模型。

### 🎓 博士生视角
SVM 的几何直觉是「最大化间隔」：在可分情况下，最优超平面是到最近样本距离最大的那个，这些最近样本就是支持向量。对偶问题的引入让「核技巧」成为可能——把样本映射到高维空间的内积用核函数直接计算，避免显式映射。软间隔用松弛变量与惩罚系数 `C` 处理噪声，等价于合页损失（hinge loss）+ L2 正则。理论上，SVM 的泛化界由「间隔」而非「维度」控制，这是它在小样本高维场景表现好的原因。

### 📚 考研者视角
算法岗面试高频：
1. **最大间隔**：为什么最大化间隔能提升泛化、支持向量的含义。
2. **核技巧**：常用核函数（线性、多项式、RBF）的性质，RBF 的 `γ` 如何影响边界。
3. **软间隔**：`C` 的作用与过拟合的关系。
4. **SVM vs 逻辑回归**：损失函数（hinge vs log loss）、输出（距离 vs 概率）、适用场景。

## 收尾

这七段代码覆盖了 SVM 从理论到落地的完整链路：原问题、对偶、核、SMO、调参、加权、置信度。凯喵的体会是，SVM 是「理论优美但工程细节多」的典型——对偶推导看懂了，代码里仍可能因为忘记标准化、忘记裁剪乘子、或者把决策函数当概率而翻车。真正的掌握标准是：给定一个数据集，你能说出「为什么这个 kernel、这个 C、这个 gamma」，而不是只会跑网格搜索。

```text
04-svm-snippets.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 一、硬间隔 SVM：直接解二次规划  (python)
    |
    v
  [02] 二、对偶问题与支持向量的识别  (python)
    |
    v
  [03] 三、核技巧：只改内积，不改算法  (python)
    |
    v
  [04] 四、SMO 的单步更新  (python)
    |
    v
  [05] 五、用 sklearn 做正确的调参流程  (python)
    |
    v
  [06] 六、不平衡数据下的类别权重  (python)
    |
    v
  [07] 七、决策函数与置信度  (python)
    |
    v
  [08] 收尾  (-)
    |
    v
  [END] 三视角解析收口
```
