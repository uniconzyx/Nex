/**
 * agent/report.ts —— 「数字可溯源」的守门 + .ipynb 导出
 * ============================================================================
 * 这个文件是整个 agent 承诺的兑现处。承诺是：
 *
 *   **报告里的每个数字，都能在某个工具的真实返回里找到。**
 *
 * 兑现方式不是「相信模型」，而是事后用 auditReport() 反向核对：
 *   1. evidence 必须指向一个真实存在的步骤（"get_progress#3"），指向不存在 = error；
 *   2. body 里出现的数字，必须能在该步骤的 brief / data / raw 里找到，找不到 = warn。
 *
 * 为什么分成 error / warn 两级：
 *   - evidence 指错（error）说明报告的因果链断了，这份报告不可信；
 *   - 数字找不到（warn）有可能是「3 步」「2 章」这类叙述性数量词，不一定是编的，
 *     所以不阻断，但要显式列出来——让用户自己判断，而不是替用户隐瞒。
 *
 * 导出 .ipynb 而不是 .md 的原因（主人定的）：
 *   markdown 里贴的输出是「文本」，ipynb 里贴的输出是「output 对象」，
 *   后者能保留 stdout / image/png / 执行计数，回放时不会与代码脱节。
 */

import type { AgentReport, AgentRun, AgentStep } from './types';

/* ============================================================================
 * 一、审计
 * ========================================================================== */

export interface AuditIssue {
  level: 'error' | 'warn';
  section: string;
  message: string;
  /** 出问题的原文片段，便于定位 */
  detail?: string;
}

/** 从 "get_progress#3" 解析出工具名与步骤号 */
function parseEvidence(ev?: string): { tool: string; idx: number } | null {
  if (!ev) return null;
  const m = /^([a-z_]+)#(\d+)$/.exec(ev.trim());
  if (!m) return null;
  return { tool: m[1], idx: Number(m[2]) };
}

/**
 * 抽出「值得核对的数字」。
 * 先剔噪：代码标识符（ml-ch01）、反引号内的代码、URL、年份区间都能合法出现而不来自工具。
 */
export function extractNumbers(text: string): string[] {
  const stripped = text
    .replace(/https?:\/\/\S+/g, ' ')
    .replace(/`[^`]*`/g, ' ')
    .replace(/\b[a-z]+-ch\d+\b/gi, ' ')
    .replace(/\b(?:ex|ch|step|lr)\d*[-\w]*/gi, ' ');
  const out = new Set<string>();
  for (const m of stripped.matchAll(/\d+(?:\.\d+)?/g)) {
    const n = m[0].replace(/^0+(?=\d)/, '');
    // 单个 0~9 的数字多为「三关」「2 步」这类叙述，噪声太大，不核
    if (n.length === 1) continue;
    out.add(n);
  }
  return [...out];
}

/** 把 observation 的三种回填形态压成一个可搜索的大字符串 */
function haystack(step: AgentStep): string {
  const o = step.observation;
  if (!o) return '';
  const parts = [o.brief, o.raw ?? ''];
  if (o.data !== undefined) {
    try {
      parts.push(JSON.stringify(o.data));
    } catch {
      /* 循环引用不可能出现在工具返回里，兜底忽略 */
    }
  }
  return parts.join('\n');
}

/** 数字是否在该步骤的证据里出现（容忍千分位与小数省略写法） */
function containsNumber(hay: string, num: string): boolean {
  if (hay.includes(num)) return true;
  // 1,234 → 1234
  const grouped = Number(num).toLocaleString('en-US');
  if (hay.includes(grouped)) return true;
  // 12.50 与 12.5 等价
  if (num.includes('.')) {
    const trimmed = num.replace(/\.?0+$/, '');
    if (trimmed && hay.includes(trimmed)) return true;
  }
  return false;
}

export function auditReport(run: AgentRun): AuditIssue[] {
  const issues: AuditIssue[] = [];
  const rep = run.report;
  if (!rep) {
    issues.push({ level: 'error', section: '(整份)', message: '没有报告（stopped=' + run.stopped + '）' });
    return issues;
  }
  const byIdx = new Map<number, AgentStep>(run.steps.map((s) => [s.idx, s]));

  for (const sec of rep.sections) {
    const ev = parseEvidence(sec.evidence);
    if (!sec.evidence) {
      // 纯定性小节允许没有证据，但含数字就必须有
      const nums = extractNumbers(sec.body);
      if (nums.length) {
        issues.push({
          level: 'warn',
          section: sec.heading,
          message: `含 ${nums.length} 个数字但没有 evidence，无法核对：${nums.slice(0, 5).join('、')}`,
        });
      }
      continue;
    }
    if (!ev) {
      issues.push({ level: 'error', section: sec.heading, message: `evidence 格式不对：${sec.evidence}（应形如 get_progress#2）` });
      continue;
    }
    const step = byIdx.get(ev.idx);
    if (!step) {
      issues.push({ level: 'error', section: sec.heading, message: `evidence 指向第 ${ev.idx} 步，但该步不存在` });
      continue;
    }
    if (step.tool !== ev.tool) {
      issues.push({
        level: 'error',
        section: sec.heading,
        message: `evidence 写的是 ${ev.tool}，但第 ${ev.idx} 步实际调的是 ${step.tool ?? 'final'}`,
      });
      continue;
    }
    if (step.observation && !step.observation.ok) {
      issues.push({ level: 'error', section: sec.heading, message: `evidence 指向的步骤本身是失败的（${step.observation.brief.slice(0, 60)}）` });
      continue;
    }
    const hay = haystack(step);
    const miss = extractNumbers(sec.body).filter((n) => !containsNumber(hay, n));
    if (miss.length) {
      issues.push({
        level: 'warn',
        section: sec.heading,
        message: `这些数字在 ${sec.evidence} 的证据里找不到：${miss.join('、')}`,
        detail: miss.join(','),
      });
    }
  }

  // labOutput 必须是某次 run_python 的真实 stdout（逐字包含）
  if (rep.labOutput && rep.labOutput.trim()) {
    const runs = run.steps.filter((s) => s.tool === 'run_python' && s.observation?.ok && (s.observation.raw ?? '').trim());
    if (!runs.length) {
      issues.push({ level: 'error', section: '主实验', message: 'labOutput 存在但这次会话没有任何成功的 run_python' });
    } else {
      const hit = runs.some((s) => (s.observation?.raw ?? '').includes(rep.labOutput!.trim().slice(0, 120)));
      if (!hit) {
        issues.push({ level: 'error', section: '主实验', message: 'labOutput 不是任何一次 run_python 的真实 stdout（疑似改写或编造）' });
      }
    }
  }

  return issues;
}

/* ============================================================================
 * 二、.ipynb 导出
 * ========================================================================== */

interface NbCell {
  cell_type: 'markdown' | 'code';
  metadata: Record<string, unknown>;
  source: string[];
  execution_count?: number | null;
  outputs?: unknown[];
}

export interface Notebook {
  cells: NbCell[];
  metadata: Record<string, unknown>;
  nbformat: 4;
  nbformat_minor: 5;
}

const toLines = (s: string): string[] => {
  const lines = s.split('\n');
  return lines.map((l, i) => (i < lines.length - 1 ? `${l}\n` : l));
};

/**
 * 报告 → notebook。
 * 结构约定（和主人「Markdown 单元格 + 可运行代码单元格」的习惯一致）：
 *   1. 标题 + headline + 生成元信息
 *   2. 每个 section 一个 markdown cell，末尾附数据来源
 *   3. 主实验：一个 code cell，outputs 里放真实 stdout 与图片（不是 markdown 文本）
 *   4. 结尾一个「复现说明」
 */
export function toIpynb(rep: AgentReport, opts?: { generatedAt?: string; subject?: string }): Notebook {
  const cells: NbCell[] = [];
  const at = opts?.generatedAt ?? new Date().toISOString();

  cells.push({
    cell_type: 'markdown',
    metadata: {},
    source: toLines(
      [
        `# ${rep.title}`,
        '',
        rep.headline ? `> ${rep.headline}` : '',
        '',
        `- 场景：${rep.scenario === 'diagnose' ? '学情诊断' : '实验陪跑'}`,
        opts?.subject ? `- 学科：${opts.subject}` : '',
        `- 生成时间：${at}`,
        '- 生成方式：CppMind Agent（所有数字来自工具真实返回，见各节「数据来源」）',
      ]
        .filter((x) => x !== '')
        .join('\n'),
    ),
  });

  for (const sec of rep.sections) {
    const tail = sec.evidence ? `\n\n---\n<sub>数据来源：\`${sec.evidence}\`</sub>` : '';
    cells.push({
      cell_type: 'markdown',
      metadata: {},
      source: toLines(`## ${sec.heading}\n\n${sec.body}${tail}`),
    });
  }

  if (rep.labCode && rep.labCode.trim()) {
    const outputs: unknown[] = [];
    if (rep.labOutput && rep.labOutput.trim()) {
      outputs.push({ name: 'stdout', output_type: 'stream', text: toLines(rep.labOutput) });
    }
    for (const img of rep.images ?? []) {
      const b64 = img.includes(',') ? img.slice(img.indexOf(',') + 1) : img;
      outputs.push({
        output_type: 'display_data',
        data: { 'image/png': b64, 'text/plain': ['<Figure>'] },
        metadata: {},
      });
    }
    cells.push({
      cell_type: 'code',
      metadata: {},
      execution_count: 1,
      source: toLines(rep.labCode),
      outputs,
    });
  }

  cells.push({
    cell_type: 'markdown',
    metadata: {},
    source: toLines(
      [
        '## 复现说明',
        '',
        '1. 本 notebook 的代码单元可以直接运行（numpy / scipy / sklearn 足够，**不需要 torch**）。',
        '2. 代码单元下的输出是**当时真实运行的 stdout**，不是手抄；改代码后请重新运行并对比。',
        '3. 各节的「数据来源」标注了数字出自哪一步工具调用，可在会话记录里逐条核对。',
      ].join('\n'),
    ),
  });

  return {
    cells,
    metadata: {
      kernelspec: { display_name: 'Python 3', language: 'python', name: 'python3' },
      language_info: { name: 'python', version: '3.11' },
      cppmind: { scenario: rep.scenario, generatedAt: at, subject: opts?.subject ?? null },
    },
    nbformat: 4,
    nbformat_minor: 5,
  };
}

/** 便于直接落盘：JSON 字符串（缩进 1，与原 .ipynb 惯例一致） */
export function ipynbJson(nb: Notebook): string {
  return `${JSON.stringify(nb, null, 1)}\n`;
}

/** 审计结果 → 一行人类可读结论（UI 顶部提示用） */
export function summarizeAudit(issues: AuditIssue[]): string {
  const err = issues.filter((i) => i.level === 'error').length;
  const warn = issues.length - err;
  if (!issues.length) return '数据自检通过：所有数字都能溯源';
  if (err) return `数据自检发现 ${err} 处硬错误、${warn} 处待核对`;
  return `数据自检：${warn} 处数字待核对（可能是叙述性数量词）`;
}
