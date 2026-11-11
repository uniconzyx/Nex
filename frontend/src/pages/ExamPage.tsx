/**
 * ExamPage.tsx —— 考研题库三视图（框架 / 套卷 / 训练）
 *
 * 定位：把已就绪的考研后端 API（docs/API-Exam.md）接入前端。三视图：
 *   框架：解题框架 / 知识点 / 分类总结 —— 教你怎么想、考什么、怎么归类；
 *   套卷：整卷或单科套卷 → 分区题目，解析按需展开（不默认剧透答案）；
 *   训练：按专题/题型/难度筛题 → 答题 → POST grade → 四层讲解复盘。
 *
 * 视觉沿用凯喵设计体系的 km-* 令牌（在 .km-app 作用域内对内容区也生效），
 * 不另起视觉方向，也不引入渐变/发丝线/玻璃拟态等模板化装饰。
 */

import { useEffect, useMemo, useState } from 'react';

import { Tex, TexMixed } from '../components/Tex';
import {
  getCatalog,
  getFrameworks,
  getKnowledge,
  getSummaries,
  getQuestions,
  getQuestion,
  getPapers,
  getPaper,
  getVocab,
  getListening,
  getFormulas,
  grade,
  type Catalog,
  type ExamSummary,
  type SubjectSummary,
  type FrameworkDoc,
  type KnowledgeDoc,
  type SummaryDoc,
  type QuestionCard,
  type QuestionList,
  type QuestionDetail,
  type PaperCard,
  type PaperList,
  type PaperDetail,
  type Walkthrough,
  type VocabDoc,
  type ListeningDoc,
  type FormulaDoc,
  type GradeResult,
} from '../lib/exam';

// ─────────────────────────── 通用小工具 ───────────────────────────

type Load<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** 手动重试：deps 不变时也能重新拉一次（Phase18 断线重连入口）。 */
  reload: () => void;
};

/** 错误态统一入口：给出「重试」而不只是一段文字指引。 */
function LoadError({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="km-empty">
      <b>加载失败</b>
      <p>{error}</p>
      <p>
        <button
          type="button"
          className="km-btn km-btn-primary km-btn-sm"
          data-testid="load-retry"
          onClick={onRetry}
        >
          重试
        </button>
      </p>
    </div>
  );
}

function useExamData<T>(fn: () => Promise<T>, deps: unknown[]): Load<T> {
  const [state, setState] = useState<Omit<Load<T>, 'reload'>>({
    data: null,
    loading: true,
    error: null,
  });
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    fn()
      .then((d) => {
        if (!cancelled) setState({ data: d, loading: false, error: null });
      })
      .catch((e: unknown) => {
        if (!cancelled && (e as Error)?.name !== 'AbortError') {
          setState({ data: null, loading: false, error: (e as Error).message || '加载失败' });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);
  return { ...state, reload: () => setNonce((n) => n + 1) };
}

const TYPE_LABEL: Record<string, string> = {
  choice: '单选',
  multi: '多选',
  blank: '填空',
  calc: '计算',
  design: '设计',
  analysis: '分析',
};

function typeLabel(t: string): string {
  return TYPE_LABEL[t] ?? t;
}

function optionLetter(i: number): string {
  return String.fromCharCode(65 + i);
}

function Difficulty({ n }: { n: number | null }) {
  if (n == null) return null;
  return (
    <span className="ex-diff" title={`难度 ${n}/5`}>
      难度{' '}
      {[1, 2, 3, 4, 5].map((k) => (
        <i key={k} className={k <= n ? 'on' : ''} />
      ))}
    </span>
  );
}

// ───────────────────────── 四层讲解渲染 ─────────────────────────

function WalkthroughView({ wt }: { wt: Walkthrough }) {
  // 键顺序固定：framework → approach → points → solution（契约 §5.6）
  return (
    <div className="ex-wt">
      <section className="ex-layer">
        <h5>
          <span className="ex-layer-no">1</span>解题框架
        </h5>
        <div className="ex-layer-title">{wt.framework.title}</div>
        <div className="ex-kv">
          <b>题型定位</b>
          <span>{wt.framework.pattern}</span>
        </div>
        <ol className="ex-steps">
          {wt.framework.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
        {wt.framework.trap && (
          <div className="ex-trap">
            <b>陷阱</b>
            {wt.framework.trap}
          </div>
        )}
      </section>

      <section className="ex-layer">
        <h5>
          <span className="ex-layer-no">2</span>解题思路
        </h5>
        <p>{wt.approach}</p>
      </section>

      <section className="ex-layer">
        <h5>
          <span className="ex-layer-no">3</span>涉及知识点
        </h5>
        <ul className="ex-points">
          {wt.points.map((p) => (
            <li key={p.id}>
              <b>{p.title}</b>
              <span className="ex-point-core">{p.core}</span>
              {p.note && <span className="ex-point-note">提示 · {p.note}</span>}
              {p.pitfall && <span className="ex-point-note">易错 · {p.pitfall}</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="ex-layer">
        <h5>
          <span className="ex-layer-no">4</span>详细解法
        </h5>
        <p className="ex-solution">{wt.solution}</p>
      </section>
    </div>
  );
}

// ─────────────────────────── 顶层：考试/科目/视图 ───────────────────────────

type ExamView = 'framework' | 'papers' | 'training';
type FrameworkSub = 'framework' | 'knowledge' | 'summary' | 'vocab' | 'listening' | 'formulas';

export function ExamPage({
  embedded = false,
  initialExam,
  initialSubject,
  initialView = 'framework',
  initialSub,
}: {
  embedded?: boolean;
  /** 外部入口直达：从考研中枢点「数英政」进来时直接落在指定考试 */
  initialExam?: string;
  initialSubject?: string;
  initialView?: ExamView;
  /** 框架视图下的子页直达（词表 / 听力），中枢子入口用得到 */
  initialSub?: FrameworkSub;
}) {
  const cat = useExamData<Catalog>(() => getCatalog(), []);
  const [examKey, setExamKey] = useState(initialExam ?? '');
  const [subjectKey, setSubjectKey] = useState(initialSubject ?? '');
  const [view, setView] = useState<ExamView>(initialView);

  const exam: ExamSummary | undefined = useMemo(
    () => cat.data?.items.find((e) => e.key === examKey),
    [cat.data, examKey],
  );

  // 外部指定了考试：目录回来后只校正科目，不把用户拽回第一场考试
  useEffect(() => {
    if (!cat.data) return;
    const target = initialExam
      ? cat.data.items.find((e) => e.key === initialExam)
      : cat.data.items[0];
    if (!target) return;
    if (!examKey) setExamKey(target.key);
    if (!subjectKey || !(target.subjects.some((s) => s.key === subjectKey))) {
      setSubjectKey(target.subjects[0]?.key ?? '');
    }
  }, [cat.data, examKey, subjectKey, initialExam]);

  useEffect(() => {
    if (!exam) return;
    if (!exam.subjects.some((s) => s.key === subjectKey)) {
      setSubjectKey(exam.subjects[0]?.key ?? '');
    }
  }, [exam, subjectKey]);

  if (cat.loading) {
    return (
      <div className="km-view">
        <div className="km-empty">正在连接考研题库…</div>
      </div>
    );
  }
  if (cat.error || !cat.data) {
    return (
      <div className="km-view">
        <div className="km-empty">
          <b>题库连接失败</b>
          <p>{cat.error || '目录为空'}</p>
          <p>
            题库由 Nex 后端提供。请确认后端已启动（在 <code>server</code> 目录执行{' '}
            <code>uvicorn app.main:app --host 127.0.0.1 --port 8000</code>），
            或到「设置 → 内容服务」里检查服务地址。
          </p>
          <p>
            <button
              type="button"
              className="km-btn km-btn-primary km-btn-sm"
              data-testid="load-retry"
              onClick={cat.reload}
            >
              重试
            </button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="km-view">
      {!embedded && (
        <header className="cp-head">
          <div>
            <h2 className="cp-title">考研题库</h2>
            <p className="cp-sub">
              {cat.data.items.length} 场考试 · 题库版本 v{cat.data.content_version} ·
              数据来自在线题库（非离线打包）
            </p>
          </div>
        </header>
      )}

      {/* 考试选择 */}
      <div className="cp-chips" role="tablist" aria-label="选择考试">
        {cat.data.items.map((e) => (
          <button
            key={e.key}
            type="button"
            role="tab"
            aria-selected={examKey === e.key}
            className={`cp-chip${examKey === e.key ? ' on' : ''}`}
            onClick={() => setExamKey(e.key)}
          >
            {e.label}
            <span className="cp-chip-n">{e.counts.questions}</span>
          </button>
        ))}
      </div>

      {/* 科目选择 */}
      {exam && (
        <div className="cp-chips" role="tablist" aria-label="选择科目">
          {exam.subjects.map((s: SubjectSummary) => (
            <button
              key={s.key}
              type="button"
              role="tab"
              aria-selected={subjectKey === s.key}
              className={`cp-chip${subjectKey === s.key ? ' on' : ''}`}
              onClick={() => setSubjectKey(s.key)}
            >
              {s.label}
              <span className="cp-chip-n">{s.counts.questions}</span>
            </button>
          ))}
        </div>
      )}

      {/* 三视图切换 */}
      <div className="ex-tabs" role="tablist" aria-label="视图">
        <button
          type="button"
          role="tab"
          aria-selected={view === 'framework'}
          className={`ex-tab${view === 'framework' ? ' on' : ''}`}
          onClick={() => setView('framework')}
        >
          解题框架
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'papers'}
          className={`ex-tab${view === 'papers' ? ' on' : ''}`}
          onClick={() => setView('papers')}
        >
          套卷演练
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'training'}
          className={`ex-tab${view === 'training' ? ' on' : ''}`}
          onClick={() => setView('training')}
        >
          专项训练
        </button>
      </div>

      {exam && subjectKey && view === 'framework' && (
        <FrameworkView exam={exam.key} subject={subjectKey} initialSub={initialSub} />
      )}
      {exam && view === 'papers' && <PapersView exam={exam.key} subjects={exam.subjects} />}
      {exam && subjectKey && view === 'training' && (
        <TrainingView exam={exam.key} subject={subjectKey} />
      )}
    </div>
  );
}

// ─────────────────────────── 视图一：框架 ───────────────────────────

function FrameworkView({
  exam,
  subject,
  initialSub = 'framework',
}: {
  exam: string;
  subject: string;
  initialSub?: FrameworkSub;
}) {
  const [sub, setSub] = useState<FrameworkSub>(initialSub);

  const fw = useExamData<FrameworkDoc>(() => getFrameworks(exam, subject), [exam, subject, sub === 'framework']);
  const kd = useExamData<KnowledgeDoc>(() => getKnowledge(exam, subject), [exam, subject, sub === 'knowledge']);
  const sm = useExamData<SummaryDoc>(() => getSummaries(exam, subject), [exam, subject, sub === 'summary']);
  // 词表目前只有英语有；空组会被 VocabBody 渲染成「本页暂无」而不是报错
  const vb = useExamData<VocabDoc>(() => getVocab(exam, subject), [exam, subject, sub === 'vocab']);
  const ls = useExamData<ListeningDoc>(() => getListening(exam, subject), [exam, subject, sub === 'listening']);
  const fm = useExamData<FormulaDoc>(() => getFormulas(exam, subject), [exam, subject, sub === 'formulas']);

  // 词表与听力只有英语有、公式只有数学有。无关科目的标签不显示，
  // 否则数英政共用一套子页签时会点出三个「暂无」，看起来像功能坏了。
  const hasVocab = exam === 'english';
  const hasListening = exam === 'english';
  const hasFormulas = exam === 'math';

  return (
    <div className="ex-subwrap">
      <div className="ex-tabs ex-tabs-sm" role="tablist" aria-label="框架子视图">
        <button type="button" role="tab" aria-selected={sub === 'framework'} className={`ex-tab${sub === 'framework' ? ' on' : ''}`} onClick={() => setSub('framework')}>
          解题框架
        </button>
        <button type="button" role="tab" aria-selected={sub === 'knowledge'} className={`ex-tab${sub === 'knowledge' ? ' on' : ''}`} onClick={() => setSub('knowledge')}>
          知识点
        </button>
        <button type="button" role="tab" aria-selected={sub === 'summary'} className={`ex-tab${sub === 'summary' ? ' on' : ''}`} onClick={() => setSub('summary')}>
          分类总结
        </button>
        {hasFormulas && (
          <button type="button" role="tab" aria-selected={sub === 'formulas'} className={`ex-tab${sub === 'formulas' ? ' on' : ''}`} onClick={() => setSub('formulas')}>
            公式速查
          </button>
        )}
        {hasVocab && (
          <button type="button" role="tab" aria-selected={sub === 'vocab'} className={`ex-tab${sub === 'vocab' ? ' on' : ''}`} onClick={() => setSub('vocab')}>
            高频词表
          </button>
        )}
        {hasListening && (
          <button type="button" role="tab" aria-selected={sub === 'listening'} className={`ex-tab${sub === 'listening' ? ' on' : ''}`} onClick={() => setSub('listening')}>
            听力
          </button>
        )}
      </div>

      {sub === 'framework' &&
        (fw.loading ? (
          <div className="km-empty">加载解题框架…</div>
        ) : fw.error ? (
          <LoadError error={fw.error} onRetry={fw.reload} />
        ) : (
          <FrameworkBody doc={fw.data!} />
        ))}

      {sub === 'knowledge' &&
        (kd.loading ? (
          <div className="km-empty">加载知识点…</div>
        ) : kd.error ? (
          <LoadError error={kd.error} onRetry={kd.reload} />
        ) : (
          <KnowledgeBody doc={kd.data!} />
        ))}

      {sub === 'summary' &&
        (sm.loading ? (
          <div className="km-empty">加载分类总结…</div>
        ) : sm.error ? (
          <LoadError error={sm.error} onRetry={sm.reload} />
        ) : (
          <SummaryBody doc={sm.data!} exam={exam} subject={subject} />
        ))}

      {sub === 'vocab' &&
        (vb.loading ? (
          <div className="km-empty">加载高频词表…</div>
        ) : vb.error ? (
          <LoadError error={vb.error} onRetry={vb.reload} />
        ) : (
          <VocabBody doc={vb.data!} />
        ))}

      {sub === 'listening' &&
        (ls.loading ? (
          <div className="km-empty">加载听力训练…</div>
        ) : ls.error ? (
          <LoadError error={ls.error} onRetry={ls.reload} />
        ) : (
          <ListeningBody doc={ls.data!} />
        ))}

      {sub === 'formulas' &&
        (fm.loading ? (
          <div className="km-empty">加载公式表…</div>
        ) : fm.error ? (
          <LoadError error={fm.error} onRetry={fm.reload} />
        ) : (
          <FormulasBody doc={fm.data!} />
        ))}
    </div>
  );
}

/**
 * 阅读高频词表：按组折叠展示，默认只展开第一组。
 * 做成折叠而不是一次铺 80 个词，是因为背单词需要「一组一组过」，
 * 全铺会让人一眼看晕、无法聚焦。
 */
function VocabBody({ doc }: { doc: VocabDoc }) {
  const [open, setOpen] = useState<Set<string>>(() => {
    const first = doc.groups[0]?.id;
    return new Set(first ? [first] : []);
  });
  const [q, setQ] = useState('');

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (!doc.groups.length) {
    return (
      <div className="cp-state">
        <b>本考试暂无高频词表</b>
        <p>词表目前为考研英语（一）/（二）准备，其它科目可先看「知识点」。</p>
      </div>
    );
  }

  const kw = q.trim().toLowerCase();
  const match = (w: { word: string; cn: string }) =>
    !kw || w.word.toLowerCase().includes(kw) || w.cn.includes(kw);

  return (
    <div className="ex-vocab">
      {doc.note && <p className="ex-vocab-note">{doc.note}</p>}

      <div className="ex-vocab-bar">
        <span className="ex-vocab-total">
          共 {doc.total} 词 · {doc.groups.length} 组
        </span>
        <input
          className="ex-vocab-search"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜单词或中文释义…"
          aria-label="搜索词表"
        />
      </div>

      {doc.groups.map((g) => {
        const words = g.words.filter(match);
        const isOpen = open.has(g.id) || !!kw;
        return (
          <section key={g.id} className="ex-vocab-group">
            <button
              type="button"
              className={`ex-vocab-head${isOpen ? ' on' : ''}`}
              onClick={() => toggle(g.id)}
              aria-expanded={isOpen}
            >
              <span className="ex-vocab-title">{g.title}</span>
              <span className="ex-vocab-count">{words.length} 词</span>
              <span className="ex-vocab-caret" aria-hidden="true">
                {isOpen ? '−' : '+'}
              </span>
            </button>

            {isOpen && (
              <>
                {g.desc && <p className="ex-vocab-desc">{g.desc}</p>}
                {words.length === 0 ? (
                  <p className="ex-vocab-empty">这一组没有匹配「{q}」的词。</p>
                ) : (
                  <ul className="ex-vocab-list">
                    {words.map((w) => (
                      <li key={`${g.id}-${w.word}`} className="ex-vocab-item">
                        <span className="ex-vocab-word">{w.word}</span>
                        <span className="ex-vocab-pos">{w.pos}</span>
                        <span className="ex-vocab-cn">{w.cn}</span>
                        {w.note && <span className="ex-vocab-note2">{w.note}</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>
        );
      })}
    </div>
  );
}

/**
 * 听力训练：不依赖音频文件，把听力能力拆成可练的单元。
 * 每个单元固定三段——练什么(goal)、怎么练(steps)、别踩什么(traps)，
 * 中间按单元类型插入不同的练习板（场景词 / 同义替换 / 速记符号 / 复述题）。
 */
function ListeningBody({ doc }: { doc: ListeningDoc }) {
  const [open, setOpen] = useState<Set<string>>(() => new Set(doc.units[0]?.id ? [doc.units[0].id] : []));

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (!doc.units.length) {
    return (
      <div className="cp-state">
        <b>本考试暂无听力训练</b>
        <p>听力模块为考研英语准备，覆盖复试口语听力与四六级式听力训练。</p>
      </div>
    );
  }

  return (
    <div className="ex-listen">
      {doc.note && <p className="ex-listen-note">{doc.note}</p>}
      <p className="ex-listen-total">
        共 {doc.total} 个训练单元 · 建议按顺序过，每单元 10~15 分钟
      </p>

      {doc.units.map((u, i) => {
        const isOpen = open.has(u.id);
        return (
          <section key={u.id} className={`ex-listen-unit${isOpen ? ' on' : ''}`}>
            <button
              type="button"
              className="ex-listen-head"
              onClick={() => toggle(u.id)}
              aria-expanded={isOpen}
            >
              <span className="ex-listen-no">{String(i + 1).padStart(2, '0')}</span>
              <span className="ex-listen-title">{u.title}</span>
              <span className="ex-listen-caret" aria-hidden="true">
                {isOpen ? '−' : '+'}
              </span>
            </button>

            {isOpen && (
              <div className="ex-listen-body">
                {u.goal && (
                  <p className="ex-listen-goal">
                    <b>目标</b>
                    {u.goal}
                  </p>
                )}

                {u.steps.length > 0 && (
                  <ol className="ex-listen-steps">
                    {u.steps.map((s, k) => (
                      <li key={k}>{s}</li>
                    ))}
                  </ol>
                )}

                {u.scenes && u.scenes.length > 0 && (
                  <div className="ex-listen-board">
                    <h5>场景定场词</h5>
                    <div className="ex-listen-scenes">
                      {u.scenes.map((sc) => (
                        <article key={sc.name} className="ex-listen-scene">
                          <h6>{sc.name}</h6>
                          <div className="ex-listen-keys">
                            {sc.keys.map((k) => (
                              <span key={k} className="ex-listen-key">
                                {k}
                              </span>
                            ))}
                          </div>
                          <p className="ex-listen-ask">{sc.ask}</p>
                        </article>
                      ))}
                    </div>
                  </div>
                )}

                {u.pairs && u.pairs.length > 0 && (
                  <div className="ex-listen-board">
                    <h5>原文 → 选项 同义替换对照</h5>
                    <ul className="ex-listen-pairs">
                      {u.pairs.map((p) => (
                        <li key={p.heard} className="ex-listen-pair">
                          <span className="ex-listen-heard">{p.heard}</span>
                          <span className="ex-listen-arrow" aria-hidden="true">
                            →
                          </span>
                          <span className="ex-listen-option">{p.option}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {u.symbols && u.symbols.length > 0 && (
                  <div className="ex-listen-board">
                    <h5>速记符号表</h5>
                    <div className="ex-listen-symbols">
                      {u.symbols.map((s) => (
                        <div key={s.sym} className="ex-listen-symbol">
                          <span className="ex-listen-sym">{s.sym}</span>
                          <span className="ex-listen-means">{s.means}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {u.drills && u.drills.length > 0 && (
                  <div className="ex-listen-board">
                    <h5>复述练习</h5>
                    <ol className="ex-listen-drills">
                      {u.drills.map((d, k) => (
                        <li key={k} className="ex-listen-drill">
                          <p className="ex-listen-prompt">{d.prompt}</p>
                          {d.tip && <p className="ex-listen-tip">{d.tip}</p>}
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {u.traps.length > 0 && (
                  <div className="ex-listen-traps">
                    <h5>常见陷阱</h5>
                    <ul>
                      {u.traps.map((t, k) => (
                        <li key={k}>{t}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}

/**
 * 公式速查：章节折叠 + 组内条目 + 关键词过滤。
 * 折叠层级只到「章」，组内直接列条目——查公式时人脑里想的是
 * 「我在找哪个章」，而不是「哪个组」，再套一层只会多点一次。
 */
function FormulasBody({ doc }: { doc: FormulaDoc }) {
  const [open, setOpen] = useState<Set<string>>(() => {
    const first = doc.chapters[0]?.id;
    return new Set(first ? [first] : []);
  });
  const [q, setQ] = useState('');
  const [onlyNotes, setOnlyNotes] = useState(false);

  const toggle = (id: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  if (!doc.chapters.length) {
    return (
      <div className="cp-state">
        <b>本考试暂无公式表</b>
        <p>公式速查目前为考研数学（一）/（二）准备。</p>
      </div>
    );
  }

  const kw = q.trim().toLowerCase();
  const hit = (it: { name: string; tex: string; note?: string }) =>
    !kw ||
    it.name.toLowerCase().includes(kw) ||
    it.tex.toLowerCase().includes(kw) ||
    (it.note || '').toLowerCase().includes(kw);

  return (
    <div className="ex-formulas">
      {doc.note && <p className="ex-fm-note">{doc.note}</p>}

      <div className="ex-fm-bar">
        <span className="ex-fm-total">共 {doc.total} 条 · {doc.chapters.length} 章</span>
        <label className="ex-fm-switch">
          <input
            type="checkbox"
            checked={onlyNotes}
            onChange={(e) => setOnlyNotes(e.target.checked)}
          />
          只看有「用法提示」的结论
        </label>
        <input
          className="ex-fm-search"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜公式名 / 符号 / 说明…"
          aria-label="搜索公式"
        />
      </div>

      {doc.chapters.map((ch) => {
        // 过滤后统计命中条数：搜索时自动展开命中的章
        const filtered = ch.groups
          .map((g) => ({ ...g, items: g.items.filter((it) => hit(it) && (!onlyNotes || it.note)) }))
          .filter((g) => g.items.length > 0);
        const count = filtered.reduce((n, g) => n + g.items.length, 0);
        const isOpen = open.has(ch.id) || !!kw || onlyNotes;
        if ((kw || onlyNotes) && count === 0) return null;

        return (
          <section key={ch.id} className={`ex-fm-chapter${isOpen ? ' on' : ''}`}>
            <button
              type="button"
              className="ex-fm-head"
              onClick={() => toggle(ch.id)}
              aria-expanded={isOpen}
            >
              <span className="ex-fm-title">{ch.title}</span>
              <span className="ex-fm-count">{count} 条</span>
              <span className="ex-fm-caret" aria-hidden="true">
                {isOpen ? '−' : '+'}
              </span>
            </button>

            {isOpen && (
              <div className="ex-fm-body">
                {ch.note && <p className="ex-fm-intro">{ch.note}</p>}
                {filtered.map((g) => (
                  <div key={g.title} className="ex-fm-group">
                    <h5>{g.title}</h5>
                    <ul className="ex-fm-list">
                      {g.items.map((it) => (
                        <li key={it.name} className="ex-fm-item">
                          <div className="ex-fm-name">{it.name}</div>
                          <div className="ex-fm-tex">
                            <Tex tex={it.tex} display />
                          </div>
                          {it.note && (
                            <p className="ex-fm-tip">
                              <TexMixed text={it.note} />
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}

function FrameworkBody({ doc }: { doc: FrameworkDoc }) {
  return (
    <div className="ex-stack">
      {doc.intro && <p className="ex-intro">{doc.intro}</p>}
      {doc.pattern && (
        <div className="ex-intro ex-intro-pattern">
          <b>题型结构</b>
          {doc.pattern}
        </div>
      )}
      {doc.topics.map((t) => (
        <article key={t.id} className="ex-topic">
          <div className="ex-topic-head">
            <h4>{t.title}</h4>
            {t.heat != null && <span className="ex-heat">考频 {t.heat}/5</span>}
            <span className="ex-qcount">{t.question_count} 题</span>
          </div>
          {t.seen_in.length > 0 && (
            <div className="ex-tags">
              {t.seen_in.map((y) => (
                <span key={y} className="ex-tag">
                  {y} 考
                </span>
              ))}
            </div>
          )}
          {t.points.length > 0 && (
            <ul className="ex-points ex-points-inline">
              {t.points.map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          )}
          {t.patterns.map((p) => (
            <div key={p.id} className="ex-pat">
              <div className="ex-pat-head">
                <b>{p.title}</b>
                {p.freq && <span className={`ex-freq ex-freq-${p.freq}`}>{p.freq}</span>}
              </div>
              {p.ask && <div className="ex-pat-ask">题型长相 · {p.ask}</div>}
              <ol className="ex-steps">
                {p.steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
              {p.traps.length > 0 && (
                <div className="ex-trap">
                  <b>易错</b>
                  {p.traps.map((tr, i) => (
                    <span key={i}>{tr}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </article>
      ))}
    </div>
  );
}

function KnowledgeBody({ doc }: { doc: KnowledgeDoc }) {
  return (
    <div className="ex-stack">
      {doc.book && (
        <p className="ex-intro">
          <b>参考教材</b>
          {doc.book}
        </p>
      )}
      {doc.items.map((b) => (
        <article key={b.topic} className="ex-block">
          <h4 className="ex-block-title">
            {b.topic_title}
            {b.chapter && <span className="ex-chapter">{b.chapter}</span>}
          </h4>
          <div className="ex-grid">
            {b.knowledge.map((k) => (
              <div key={k.id} className="ex-kp">
                <div className="ex-kp-title">{k.title}</div>
                <div className="ex-kp-core">{k.core}</div>
                {k.tip && <div className="ex-kp-tip">易错 · {k.tip}</div>}
                {k.patterns.length > 0 && (
                  <div className="ex-tags">
                    {k.patterns.map((pp, i) => (
                      <span key={i} className="ex-tag ex-tag-soft">
                        {pp}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function SummaryBody({ doc, exam, subject }: { doc: SummaryDoc; exam: string; subject: string }) {
  const [open, setOpen] = useState<{ id: string; order: string[] } | null>(null);

  return (
    <div className="ex-stack">
      {doc.groups.map((g) => (
        <article key={g.topic} className="ex-sum">
          <h4 className="ex-sum-title">{g.title}</h4>
          <div className="ex-kv">
            <b>认题信号</b>
            <span>{g.recognize}</span>
          </div>
          <ol className="ex-steps">
            {g.framework.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
          {g.skills.length > 0 && (
            <div className="ex-skills">
              {g.skills.map((sk, i) => (
                <div key={i} className="ex-skill">
                  <b>{sk.title}</b>
                  <span>{sk.body}</span>
                </div>
              ))}
            </div>
          )}
          {g.traps.length > 0 && (
            <div className="ex-trap">
              <b>陷阱</b>
              {g.traps.map((tr, i) => (
                <span key={i}>{tr}</span>
              ))}
            </div>
          )}
          {g.question_ids.length > 0 && (
            <div className="ex-qids">
              本专题题目：{g.question_ids.length} 道（去「专项训练」按题型刷）
            </div>
          )}
          {g.suggested_order.length > 0 && (
            <div className="ex-order">
              <div className="ex-order-head">
                建议刷题顺序
                <span className="ex-order-hint">由易到难 · 相邻题尽量不重复考点 · 点击进入练习/讲解</span>
              </div>
              <ol className="ex-order-list">
                {g.suggested_order.map((id, i) => (
                  <li key={id}>
                    <button type="button" className="ex-order-item" onClick={() => setOpen({ id, order: g.suggested_order })}>
                      <span className="ex-order-no">{i + 1}</span>
                      <span className="ex-order-id">{id}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </article>
      ))}

      {open && (
        <TrainModal
          exam={exam}
          subject={subject}
          questionId={open.id}
          onClose={() => setOpen(null)}
          onNext={() => {
            const cur = open.order.indexOf(open.id);
            const next = open.order[(cur + 1) % open.order.length];
            setOpen({ id: next, order: open.order });
          }}
        />
      )}
    </div>
  );
}

// ─────────────────────────── 视图二：套卷 ───────────────────────────

function PapersView({ exam, subjects }: { exam: string; subjects: SubjectSummary[] }) {
  const [subjectFilter, setSubjectFilter] = useState<string | null>(null);
  const [papers, setPapers] = useState<PaperCard[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const SIZE = 20;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPage(1);
    getPapers(exam, { subject: subjectFilter ?? undefined, page: 1, size: SIZE })
      .then((r: PaperList) => {
        if (cancelled) return;
        setPapers(r.items);
        setTotal(r.total);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError((e as Error).message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [exam, subjectFilter]);

  const loadMore = () => {
    const next = page + 1;
    setPage(next);
    getPapers(exam, { subject: subjectFilter ?? undefined, page: next, size: SIZE }).then((r) => {
      setPapers((prev) => [...prev, ...r.items]);
    });
  };

  return (
    <div className="ex-stack">
      <div className="cp-chips" role="tablist" aria-label="套卷科目筛选">
        <button type="button" role="tab" aria-selected={subjectFilter === null} className={`cp-chip${subjectFilter === null ? ' on' : ''}`} onClick={() => setSubjectFilter(null)}>
          全部
        </button>
        {subjects.map((s) => (
          <button key={s.key} type="button" role="tab" aria-selected={subjectFilter === s.key} className={`cp-chip${subjectFilter === s.key ? ' on' : ''}`} onClick={() => setSubjectFilter(s.key)}>
            {s.label}
          </button>
        ))}
      </div>

      {loading && <div className="km-empty">加载套卷…</div>}
      {error && (
        <div className="km-empty">
          <b>加载失败</b>
          <p>{error}</p>
        </div>
      )}
      {!loading && !error && papers.length === 0 && <div className="km-empty">该筛选下暂无套卷</div>}

      <div className="ex-grid ex-grid-paper">
        {papers.map((p) => (
          <PaperRow key={p.id} exam={exam} paper={p} />
        ))}
      </div>

      {!loading && papers.length < total && (
        <button type="button" className="km-btn km-btn-ghost km-btn-sm ex-more" onClick={loadMore}>
          加载更多（{papers.length}/{total}）
        </button>
      )}
    </div>
  );
}

function PaperRow({ exam, paper }: { exam: string; paper: PaperCard }) {
  const [open, setOpen] = useState(false);
  const det = useExamData<PaperDetail | null>(() => (open ? getPaper(exam, paper.id) : Promise.resolve(null)), [exam, paper.id, open]);

  return (
    <article className="ex-paper">
      <button type="button" className="ex-paper-head" onClick={() => setOpen((v) => !v)}>
        <div>
          <div className="ex-paper-title">
            {paper.title}
            {paper.scope === 'full' && <span className="ex-badge ex-badge-full">整卷</span>}
          </div>
          <div className="ex-paper-meta">
            {paper.question_count} 题 · {paper.section_count} 区
            {paper.duration != null && ` · ${paper.duration} 分钟`}
            {paper.total_score != null && ` · ${paper.total_score} 分`}
          </div>
        </div>
        <span className={`ex-caret${open ? ' on' : ''}`}>▾</span>
      </button>

      {open && det.loading && <div className="ex-paper-body">加载套卷详情…</div>}
      {open && det.error && (
        <div className="ex-paper-body">
          <b>加载失败</b>
          <p>{det.error}</p>
        </div>
      )}
      {open && det.data && <PaperDetailView paper={det.data} />}
    </article>
  );
}

function PaperDetailView({ paper }: { paper: PaperDetail }) {
  return (
    <div className="ex-paper-body">
      {paper.disclaimer && <p className="ex-disclaimer">{paper.disclaimer}</p>}
      {paper.blueprint.length > 0 && (
        <div className="ex-blueprint">
          {paper.blueprint.map((b, i) => (
            <span key={i} className="ex-bp">
              {b.name} {b.score}分
            </span>
          ))}
        </div>
      )}
      {paper.sections.map((sec) => (
        <section key={sec.no} className="ex-section">
          <h5 className="ex-section-head">
            第 {sec.no} 区 · {sec.name}
            <span>
              {sec.type} · {sec.score}分{sec.per_score != null ? ` / 题${sec.per_score}` : ''}
              {sec.range ? ` · ${sec.range}` : ''}
            </span>
          </h5>
          {sec.note && <div className="ex-section-note">{sec.note}</div>}
          <ol className="ex-sec-items">
            {sec.items.map((it) => (
              <PaperItemView key={it.id} item={it} />
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function PaperItemView({ item }: { item: PaperDetail['sections'][number]['items'][number] }) {
  const [show, setShow] = useState(false);
  const objective = item.type === 'choice' || item.type === 'multi' || item.type === 'blank';
  return (
    <li className="ex-pitem">
      <div className="ex-pitem-head">
        <span className="ex-pitem-no">{item.order}</span>
        <span className="ex-type-tag">{typeLabel(item.type)}</span>
        {item.topic_title && <span className="ex-topic-tag">{item.topic_title}</span>}
        {!item.in_bank && <span className="ex-badge ex-badge-only">仅卷内</span>}
        {item.difficulty != null && <Difficulty n={item.difficulty} />}
      </div>
      <div className="ex-stem">{item.stem}</div>
      {item.options.length > 0 && (
        <ul className="ex-opts">
          {item.options.map((o, i) => (
            <li key={i} className="ex-opt ex-opt-static">
              <span className="ex-opt-key">{optionLetter(i)}</span>
              <span>{o}</span>
            </li>
          ))}
        </ul>
      )}
      {item.ask.length > 0 && (
        <ol className="ex-asks">
          {item.ask.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ol>
      )}
      {objective && (
        <button type="button" className="km-btn km-btn-ghost km-btn-sm" onClick={() => setShow((v) => !v)}>
          {show ? '收起解析' : '看解析'}
        </button>
      )}
      {show && item.walkthrough && <WalkthroughView wt={item.walkthrough} />}
    </li>
  );
}

// ─────────────────────────── 视图三：训练 ───────────────────────────

function TrainingView({ exam, subject }: { exam: string; subject: string }) {
  const [qtype, setQtype] = useState('');
  const [difficulty, setDifficulty] = useState<number | ''>('');
  const [kw, setKw] = useState('');
  const [items, setItems] = useState<QuestionCard[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const SIZE = 20;

  const filters = { type: qtype, difficulty: difficulty === '' ? undefined : difficulty, q: kw || undefined };

  const fetchPage = (p: number) => {
    setLoading(true);
    setError(null);
    getQuestions(exam, subject, { ...filters, page: p, size: SIZE })
      .then((r: QuestionList) => {
        setItems(p === 1 ? r.items : [...items, ...r.items]);
        setTotal(r.total);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError((e as Error).message);
        setLoading(false);
      });
  };

  useEffect(() => {
    setPage(1);
    setItems([]);
    fetchPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exam, subject, qtype, difficulty, kw]);

  const loadMore = () => {
    const next = page + 1;
    setPage(next);
    getQuestions(exam, subject, { ...filters, page: next, size: SIZE }).then((r) => {
      setItems((prev) => [...prev, ...r.items]);
    });
  };

  return (
    <div className="ex-stack">
      <div className="ex-filters">
        <input
          className="ex-search"
          placeholder="题干关键词…"
          value={kw}
          onChange={(e) => setKw(e.target.value)}
          aria-label="题干关键词"
        />
        <select className="ex-select" value={qtype} onChange={(e) => setQtype(e.target.value)} aria-label="题型">
          <option value="">全部题型</option>
          {['choice', 'multi', 'blank', 'calc', 'design', 'analysis'].map((t) => (
            <option key={t} value={t}>
              {typeLabel(t)}
            </option>
          ))}
        </select>
        <select className="ex-select" value={difficulty} onChange={(e) => setDifficulty(e.target.value === '' ? '' : Number(e.target.value))} aria-label="难度">
          <option value="">全部难度</option>
          {[1, 2, 3, 4, 5].map((d) => (
            <option key={d} value={d}>
              难度 {d}
            </option>
          ))}
        </select>
      </div>

      {loading && <div className="km-empty">加载题目…</div>}
      {error && (
        <div className="km-empty">
          <b>加载失败</b>
          <p>{error}</p>
        </div>
      )}
      {!loading && !error && items.length === 0 && <div className="km-empty">没有符合条件的题目</div>}

      <ol className="ex-qlist">
        {items.map((q) => (
          <li key={q.id} className="ex-q">
            <button type="button" className="ex-q-main" onClick={() => setOpenId(q.id)}>
              <span className="ex-q-no">{q.order}</span>
              <span className="ex-type-tag">{typeLabel(q.type)}</span>
              <span className="ex-q-stem">{q.stem}</span>
              <Difficulty n={q.difficulty} />
              <span className="ex-q-go">去练习 →</span>
            </button>
          </li>
        ))}
      </ol>

      {!loading && items.length < total && (
        <button type="button" className="km-btn km-btn-ghost km-btn-sm ex-more" onClick={loadMore}>
          加载更多（{items.length}/{total}）
        </button>
      )}

      {openId && <TrainModal exam={exam} subject={subject} questionId={openId} onClose={() => setOpenId(null)} onNext={() => {
        const idx = items.findIndex((q) => q.id === openId);
        if (idx >= 0 && idx + 1 < items.length) setOpenId(items[idx + 1].id);
        else setOpenId(null);
      }} />}
    </div>
  );
}

function TrainModal({ exam, subject, questionId, onClose, onNext }: {
  exam: string;
  subject: string;
  questionId: string;
  onClose: () => void;
  onNext: () => void;
}) {
  const det = useExamData<QuestionDetail>(() => getQuestion(exam, subject, questionId), [exam, subject, questionId]);
  const [choice, setChoice] = useState<number | null>(null);
  const [choices, setChoices] = useState<number[]>([]);
  const [text, setText] = useState('');
  const [result, setResult] = useState<GradeResult | null>(null);
  const [grading, setGrading] = useState(false);
  const [gradeErr, setGradeErr] = useState<string | null>(null);
  const [reveal, setReveal] = useState(false);

  useEffect(() => {
    setChoice(null);
    setChoices([]);
    setText('');
    setResult(null);
    setGradeErr(null);
    setReveal(false);
  }, [questionId]);

  if (det.loading) {
    return (
      <Overlay onClose={onClose}>
        <div className="km-empty">加载题目…</div>
      </Overlay>
    );
  }
  if (det.error || !det.data) {
    return (
      <Overlay onClose={onClose}>
        <div className="km-empty">
          <b>加载失败</b>
          <p>{det.error}</p>
        </div>
      </Overlay>
    );
  }

  const q = det.data;
  const objective = q.type === 'choice' || q.type === 'multi' || q.type === 'blank';
  const isMulti = q.type === 'multi';
  const correctArr = Array.isArray(q.answer.correct) ? q.answer.correct : [q.answer.correct];

  const toggleMulti = (i: number) => {
    setChoices((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]));
  };

  const doGrade = async () => {
    if (!objective) return;
    setGrading(true);
    setGradeErr(null);
    try {
      const answer: { question_id: string; choice?: number; choices?: number[]; text?: string } = { question_id: q.id };
      if (q.type === 'choice' && choice != null) answer.choice = choice;
      else if (q.type === 'multi' && choices.length) answer.choices = [...choices].sort((a, b) => a - b);
      else if (q.type === 'blank') answer.text = text;
      const r = await grade(exam, subject, [answer]);
      setResult(r);
    } catch (e) {
      setGradeErr((e as Error).message);
    } finally {
      setGrading(false);
    }
  };

  const gradedItem = result?.items.find((it) => it.question_id === q.id) ?? null;

  return (
    <Overlay onClose={onClose}>
      <div className="ex-modal">
        <div className="ex-modal-head">
          <div>
            <span className="ex-type-tag">{typeLabel(q.type)}</span>
            <span className="ex-q-stem ex-q-stem-lg">{q.stem}</span>
          </div>
          <button type="button" className="ex-x" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        {q.passage && <div className="ex-passage">{q.passage}</div>}
        {q.ask.length > 0 && (
          <ol className="ex-asks">
            {q.ask.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        )}

        {q.options.length > 0 && (
          <ul className="ex-opts">
            {q.options.map((o, i) => {
              const selected = isMulti ? choices.includes(i) : choice === i;
              const isCorrect = gradedItem?.verdict === 'CORRECT' && correctArr.includes(i);
              const isWrong =
                (gradedItem?.verdict === 'INCORRECT' &&
                  ((isMulti && choices.includes(i) && !correctArr.includes(i)) ||
                    (!isMulti && choice === i && q.answer.correct !== i)));
              const cls = [
                'ex-opt',
                selected ? 'sel' : '',
                isCorrect ? 'ok' : '',
                isWrong ? 'no' : '',
              ].join(' ');
              return (
                <li key={i}>
                  <button type="button" className={cls} onClick={() => (isMulti ? toggleMulti(i) : setChoice(i))} disabled={!!result}>
                    <span className="ex-opt-key">{optionLetter(i)}</span>
                    <span>{o}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {q.type === 'blank' && (
          <input className="ex-blank" placeholder="写下你的答案…" value={text} onChange={(e) => setText(e.target.value)} disabled={!!result} />
        )}

        {!objective && (
          <div className="ex-subj-note">本题为「{typeLabel(q.type)}」主观题，无自动判分；可写下思路后查看参考解法。</div>
        )}

        <div className="ex-modal-actions">
          {objective ? (
            <button type="button" className="km-btn km-btn-primary" onClick={doGrade} disabled={grading || !!result}>
              {grading ? '判分中…' : result ? '已判分' : '提交判分'}
            </button>
          ) : (
            <button type="button" className="km-btn km-btn-primary" onClick={() => setReveal(true)}>
              看参考解法
            </button>
          )}
          <button type="button" className="km-btn km-btn-ghost" onClick={onNext}>
            下一题 →
          </button>
        </div>

        {gradeErr && <div className="ex-grade-err">判分失败：{gradeErr}</div>}

        {result && gradedItem && (
          <div className="ex-grade-result">
            <div className={`ex-verdict ex-verdict-${gradedItem.verdict}`}>
              {gradedItem.verdict === 'CORRECT' ? '答对' : gradedItem.verdict === 'INCORRECT' ? '答错' : '主观·不计分'}
            </div>
            <WalkthroughView wt={gradedItem.walkthrough} />
          </div>
        )}

        {!objective && reveal && <WalkthroughView wt={q.walkthrough} />}
      </div>
    </Overlay>
  );
}

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="ex-overlay" onClick={onClose}>
      <div className="ex-overlay-inner" onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

export default ExamPage;
