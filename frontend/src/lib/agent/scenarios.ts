/**
 * agent/scenarios.ts —— 两个场景：S1 学情诊断、S2 实验陪跑
 * ============================================================================
 * 为什么只有两个（A 期）：
 *   S3 部署 / S4 模拟面试需要「线上环境信息」和「多轮追问」，工具面比这两个场景宽得多，
 *   放进 A 期只会让 planner 的 prompt 变长、成功率变低。先把「读进度 → 跑代码 → 出报告」
 *   这条最小闭环做扎实，后面两个场景是加工具，不是改架构。
 *
 * 每个场景有两套动作序列：
 *   1. **fallback（规则序列）**：没有 LLM、或 LLM 连续返回非法格式时用。
 *      它必须能独立产出一份「数字全对、只是没有洞察」的报告——
 *      这是「离线可用」与「降级不崩」两条要求的落点。
 *   2. **task（给 planner 的任务书）**：自然语言，讲清目标与停止条件。
 *
 * fallback 的参数支持 `{{变量}}` 占位，由 loop.ts 在每步观察后回填，
 * 这样规则序列也能依赖前一步的结果（例如「诊断最弱的那一章」）。
 */

import type { AgentScenario } from './types';

/* ============================================================================
 * 一、实验模板：没有专属 lab 时的通用脚本
 * ========================================================================== */

/**
 * 为什么要有模板：
 *   23 章目前都还没有 labs.json（S2 素材缺口），但「跑一段真代码并引用真实输出」
 *   是 agent 与聊天机器人的分界。没有专属实验时，用章节族的通用实验顶上，
 *   报告里如实标注 `template`，不假装是本章专属实验。
 *
 * 约束：**必须能在 Pyodide 里跑**（numpy/sklearn 有，torch 没有），
 * 且必须 `print` 出结论——没有 stdout 的输出无法被报告引用。
 */
export interface LabTemplate {
  /** 这份模板在证明什么（会写进报告的一句话） */
  claim: string;
  code: string;
}

const ML_GRADIENT_LAB: LabTemplate = {
  claim: '学习率过大时损失震荡不收敛，过小时收敛慢；这条曲线是调参的物理依据',
  code: `import numpy as np

# 一维二次损失 f(w) = (w-3)^2 上的梯度下降，对比三个学习率
def run(lr, steps=30):
    w, hist = 0.0, []
    for _ in range(steps):
        g = 2 * (w - 3)          # df/dw
        w -= lr * g
        hist.append((w - 3) ** 2)
    return w, hist

print(f"{'lr':>6} {'最终 w':>10} {'最终损失':>12} {'是否收敛':>8}")
for lr in (0.01, 0.1, 1.05):
    w, hist = run(lr)
    converged = "是" if hist[-1] < 1e-6 else "否"
    print(f"{lr:>6} {w:>10.6f} {hist[-1]:>12.3e} {converged:>8}")

# 收敛速度的量级：二次函数上误差按 (1-lr*H) 等比缩小，H=2
for lr in (0.01, 0.1):
    ratio = (hist[-1] / hist[-2]) if len(hist) > 1 else float('nan')
    print(f"lr={lr}: 相邻两步损失比 ≈ {ratio:.4f}（理论 {(1 - lr * 2) ** 2:.4f}）")
`,
};

const ML_OVERFIT_LAB: LabTemplate = {
  claim: '训练误差随模型复杂度单调下降，验证误差先降后升——这就是过拟合的可观测形态',
  code: `import numpy as np

rng = np.random.default_rng(0)

# 真函数 f(x)=sin(2πx)，20 个带噪样本
def f(x):
    return np.sin(2 * np.pi * x)

x_tr = np.sort(rng.uniform(0, 1, 20))
y_tr = f(x_tr) + rng.normal(0, 0.2, 20)
x_va = np.sort(rng.uniform(0, 1, 200))
y_va = f(x_va) + rng.normal(0, 0.2, 200)

print(f"{'次数':>4} {'训练 MSE':>10} {'验证 MSE':>10}")
for deg in (1, 3, 5, 9, 15):
    coef = np.polyfit(x_tr, y_tr, deg)
    tr = np.mean((np.polyval(coef, x_tr) - y_tr) ** 2)
    va = np.mean((np.polyval(coef, x_va) - y_va) ** 2)
    print(f"{deg:>4} {tr:>10.4f} {va:>10.4f}")

print("结论：训练 MSE 一路降到 ~0，验证 MSE 在 3~5 次最低后回升 → 高方差")
`,
};

const AI_SOFTMAX_LAB: LabTemplate = {
  claim: 'softmax 的数值稳定性来自「先减最大值」，不减时 exp 会溢出成 inf',
  code: `import numpy as np

logits = np.array([1000.0, 1001.0, 1002.0])

def softmax_naive(z):
    e = np.exp(z)
    return e / e.sum()

def softmax_stable(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()

print("naive :", softmax_naive(logits))
print("stable:", softmax_stable(logits))
print("两者概率和:", softmax_naive(logits).sum(), softmax_stable(logits).sum())
print("差值（stable - naive）:", softmax_stable(logits) - softmax_naive(logits))
print("结论：softmax 对整体平移不变，减最大值不改变结果，只避免溢出")
`,
};

const AI_ATTENTION_LAB: LabTemplate = {
  claim: '注意力权重按 √d_k 缩放后才不会在维度变大时退化为 one-hot（softmax 饱和）',
  code: `import numpy as np

rng = np.random.default_rng(1)

def attn_entropy(d, n=4, scale=True):
    q = rng.normal(size=(n, d))
    k = rng.normal(size=(n, d))
    s = q @ k.T
    if scale:
        s = s / np.sqrt(d)
    s = s - s.max(axis=1, keepdims=True)
    p = np.exp(s)
    p = p / p.sum(axis=1, keepdims=True)
    ent = -(p * np.log(p + 1e-12)).sum(axis=1).mean()
    return p, ent

print(f"{'d_k':>5} {'缩放':>4} {'平均熵':>8} {'最大权重(均值)':>14}")
for d in (8, 64, 512):
    for scale in (True, False):
        p, ent = attn_entropy(d, scale=scale)
        print(f"{d:>5} {str(scale):>4} {ent:>8.4f} {p.max(axis=1).mean():>14.4f}")

print("结论：不缩放时熵随 d_k 下降、最大权重趋近 1 → 注意力退化为硬选择")
`,
};

const GENERIC_NUMPY_LAB: LabTemplate = {
  claim: '先确认环境与数值精度，再做任何计算——这是所有实验的第一步',
  code: `import sys
import numpy as np

print("python:", sys.version.split()[0])
print("numpy :", np.__version__)
a = np.arange(12).reshape(3, 4)
print("shape:", a.shape, "dtype:", a.dtype, "strides:", a.strides)
print("按列求和的 shape:", a.sum(axis=0).shape, "值:", a.sum(axis=0).tolist())
print("结论：形状与轴的方向是 numpy 里最容易错的地方，动手前先打印出来")
`,
};

/**
 * 章节族 → 默认实验。键是章节 id 前缀，取值顺序即优先级。
 * 找不到时用 GENERIC_NUMPY_LAB（永远可跑）。
 */
const LAB_BY_PREFIX: [string, LabTemplate][] = [
  ['ml-ch01', ML_GRADIENT_LAB],
  ['ml-ch03', ML_OVERFIT_LAB],
  ['ml-ch04', ML_OVERFIT_LAB],
  ['ml-ch05', ML_OVERFIT_LAB],
  ['ai-ch01', AI_SOFTMAX_LAB],
  ['ai-ch03', AI_ATTENTION_LAB],
  ['ai-ch02', AI_ATTENTION_LAB],
];

export function labFor(chapterId?: string): { template: LabTemplate; exact: boolean } {
  if (chapterId) {
    for (const [prefix, tpl] of LAB_BY_PREFIX) {
      if (chapterId === prefix || chapterId.startsWith(prefix)) return { template: tpl, exact: true };
    }
  }
  return { template: GENERIC_NUMPY_LAB, exact: false };
}

/* ============================================================================
 * 二、场景定义
 * ========================================================================== */

const DIAGNOSE: AgentScenario = {
  id: 'diagnose',
  name: '学情诊断',
  tagline: '读你的真实进度与错题，定位最薄弱的 3 处，给出本周能做完的下一步',
  task: [
    '你的任务是做一次**基于真实数据的学情诊断**，不是给通用学习建议。',
    '',
    '必须做到：',
    '1. 先用 get_progress 拿到本学科的逐章掌握度、错题数、未开始章；',
    '2. 对最薄弱的 2~3 章，用 read_chapter 读它的 pitfalls（易错点）和 interviews（面试题），',
    '   再用 list_chapter_exercises 取几道题，判断「薄弱」到底是概念没懂还是题没做；',
    '3. 如果错题集中在某一章，用 list_wrong_exercises 限定该章，把错题的题型列出来；',
    '4. 结论必须落到「先做哪一章、做哪一关、补哪一篇 concept」这种可执行的粒度。',
    '',
    '禁止：不要编造百分比、错题数、章节名——所有数字只能来自工具返回。',
    '停止条件：拿到足够定位薄弱点的证据后，输出 final。',
  ].join('\n'),
  fallback: [
    { thought: '先看整体进度，确定薄弱面', tool: 'get_progress', args: {} },
    { thought: '列出章节清单，确认可选范围', tool: 'list_chapters', args: {} },
    { thought: '统计错题分布', tool: 'list_wrong_exercises', args: { limit: 10 } },
    { thought: '读最弱章最容易错的地方', tool: 'read_chapter', args: { chapter_id: '{{weak0}}', focus: 'pitfalls' } },
    {
      thought: '看最弱章的题目，判断是概念问题还是练得少',
      tool: 'list_chapter_exercises',
      args: { chapter_id: '{{weak0}}', limit: 5 },
    },
  ],
};

const EXPERIMENT: AgentScenario = {
  id: 'experiment',
  name: '实验陪跑',
  tagline: '锁定一章，写一段真跑的 Python，用真实输出回答你的问题',
  task: [
    '你的任务是**陪用户做一个能跑出结果的实验**，结论必须由真实 stdout 支撑。',
    '',
    '必须做到：',
    '1. 先用 read_chapter 读锁定章节的 concepts，确认要验证的是哪条论断；',
    '2. 用 run_python 写一段最小可运行脚本去验证它，脚本必须 print 出对比数据；',
    '3. 如果报错或输出为空，**读 Traceback 改代码重跑**，不要用文字解释代替运行；',
    '4. 报告里每一句带数字的结论，都必须能在 run_python 的 stdout 里找到。',
    '',
    '环境限制：沙箱有 numpy / scipy / sklearn / matplotlib，**没有 torch**。',
    '涉及深度学习的内容，改用 numpy 复现关键计算（前向、注意力、softmax、梯度），不要 import torch。',
    '停止条件：实验跑通且拿到可引用的输出后，输出 final。',
  ].join('\n'),
  fallback: [
    { thought: '先确认这一章要验证什么', tool: 'read_chapter', args: { chapter_id: '{{chapter}}', focus: 'concepts' } },
    { thought: '跑一段最小实验，拿到真实输出', tool: 'run_python', args: { code: '{{lab_code}}' } },
  ],
};

export const SCENARIOS: AgentScenario[] = [DIAGNOSE, EXPERIMENT];

export function getScenario(id: string): AgentScenario | undefined {
  return SCENARIOS.find((s) => s.id === id);
}

/** 默认学科：ML/DL 都挂在 `ai` 包下，但用户心里「机器学习」是独立的一门 */
export const DEFAULT_SUBJECT = 'ml';
