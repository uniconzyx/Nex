/**
 * ExerciseBank.tsx —— 题库浏览器
 * ============================================================================
 * 818 道题按学科 / 题型 / 难度 / 关键词筛，点开看题面、作答、对答案。
 *
 * 【为什么客观题不放进判题台】
 *   选择题、看码写输出、找错改错这些题，判据是「答案文本相等」，不需要
 *   编译也不需要沙箱。塞进判题台等于为了比两个字符串起一个进程。
 *   这里就地判：选择题按集合比对，输出题按 OJ 归一化比对。
 *
 * 【为什么编程题只给「去判题台」而不是自己跑】
 *   真正的编译、资源限制、超时击杀都在 JudgeEngine 后面（桌面 go-judge /
 *   移动 Pyodide）。在这里另起一套执行路径 = 两套判题语义，必然对不上。
 *
 * 【可判性】
 *   不是每道编程题都能判。有 cases 且语言有运行时的才放行，
 *   其余给「参考实现 + 自评」——不假装能判。
 * ============================================================================
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { renderMarkdown } from '../lib/markdown';
import { normalizeOutput } from '../lib/JudgeEngine';
import { recordAnswer } from '../lib/progress';
import { submitDaily } from '../lib/daily';
import { submitWeekly } from '../lib/weekly';
import { pushToast } from '../lib/feedback';
import {
  DIFF_META,
  TYPE_META,
  chapterTitle,
  filterExercises,
  isJudgeable,
  isUnsupportedLang,
  languageLabel,
  sendToJudge,
  subjectStats,
  toJudgeProblem,
  markBankDone,
  useBankDone,
  useCloudCatalog,
  useFocusedChapter,
  useFocusedExercise,
  focusChapter,
  focusExercise,
  type BankExercise,
  type BankFilter,
  type BankType,
} from '../lib/exerciseBank';

const TYPE_ORDER: BankType[] = ['choice', 'coding', 'output', 'fix_error', 'explain', 'design'];

const EMPTY_FILTER: BankFilter = {
  subject: '',
  type: 'all',
  diff: 'all',
  judgeableOnly: false,
  todoOnly: false,
  keyword: '',
};

export function ExerciseBank({
  subject,
  onGoJudge,
}: {
  subject: string;
  /** 点「去判题台」后由外层切 Tab；不传则只 toast 式提示 */
  onGoJudge?: () => void;
}) {
  const [filter, setFilter] = useState<BankFilter>({ ...EMPTY_FILTER, subject });
  const [openId, setOpenId] = useState<string | null>(null);
  const done = useBankDone();
  /** 云端目录：拉取后端 GET /exercises 的 bundle_id，与本地 1:1 标注 */
  const cloud = useCloudCatalog();
  /** 从学习页某章跳进来时的章节锁定 */
  const focused = useFocusedChapter();
  /** 图鉴 / 每日试炼指名要打开的那道题 */
  const focusedEx = useFocusedExercise();

  useEffect(() => {
    if (!focusedEx) return;
    setOpenId(focusedEx);
    // 消费掉：否则以后每次切回题库都会自动弹开同一道题
    focusExercise(null);
  }, [focusedEx]);

  // 学科切换时重置筛选里的 subject（其余条件保留，符合「我还在找同类题」的心智）；
  // chapter 不在本地 state 里，它由 focusChapter() 的全局目标决定。
  const active: BankFilter = { ...filter, subject, chapter: focused };
  const stats = useMemo(() => subjectStats(subject), [subject]);
  const list = useMemo(
    () => filterExercises(subject, active, done),
    [subject, active.type, active.diff, active.judgeableOnly, active.todoOnly, active.keyword, active.chapter, done],
  );
  const current = openId ? list.find((e) => e.id === openId) ?? null : null;

  const patch = (p: Partial<BankFilter>) => setFilter({ ...active, ...p });

  const goJudge = useCallback(
    (e: BankExercise) => {
      sendToJudge(toJudgeProblem(e));
      onGoJudge?.();
    },
    [onGoJudge],
  );

  return (
    <div className="bank">
      {/* ---------- 筛选条 ---------- */}
      <div className="bank-bar">
        <input
          className="bank-search"
          value={active.keyword}
          onChange={(ev) => patch({ keyword: ev.target.value })}
          placeholder="搜题目标题 / 题面 / 标签"
        />
        <div className="bank-chips">
          <button
            type="button"
            className={`bank-chip${active.type === 'all' ? ' on' : ''}`}
            onClick={() => patch({ type: 'all' })}
          >
            全部 <i>{stats.total}</i>
          </button>
          {TYPE_ORDER.filter((t) => (stats.byType[t] ?? 0) > 0).map((t) => (
            <button
              key={t}
              type="button"
              className={`bank-chip${active.type === t ? ' on' : ''}`}
              onClick={() => patch({ type: active.type === t ? 'all' : t })}
            >
              {TYPE_META[t].short} <i>{stats.byType[t] ?? 0}</i>
            </button>
          ))}
        </div>
        <div className="bank-toggles">
          <select
            className="bank-select"
            value={active.diff}
            onChange={(ev) => patch({ diff: ev.target.value as BankFilter['diff'] })}
          >
            <option value="all">不限难度</option>
            <option value="easy">简单</option>
            <option value="medium">中等</option>
            <option value="hard">困难</option>
          </select>
          <label className="bank-check">
            <input
              type="checkbox"
              checked={active.judgeableOnly}
              onChange={(ev) => patch({ judgeableOnly: ev.target.checked })}
            />
            <span>仅可判 {stats.judgeable}</span>
          </label>
          <label className="bank-check">
            <input
              type="checkbox"
              checked={active.todoOnly}
              onChange={(ev) => patch({ todoOnly: ev.target.checked })}
            />
            <span>未完成</span>
          </label>
        </div>
        <div className="bank-sync">
          {cloud.status === 'loading' && <span className="bank-sync-pill loading">同步云端目录…</span>}
          {cloud.status === 'ok' && (
            <span className="bank-sync-pill ok">云端同步 {cloud.ids.size} 题</span>
          )}
          {cloud.status === 'error' && <span className="bank-sync-pill err">离线 · 本地题库</span>}
        </div>
      </div>

      {active.chapter && (
        <div className="bank-focus">
          <span>已锁定章节：{chapterTitle(active.chapter)}</span>
          <button type="button" onClick={() => focusChapter(null)}>
            看全学科
          </button>
        </div>
      )}

      {/* ---------- 列表 + 详情 ---------- */}
      <div className={`bank-body${current ? ' has-detail' : ''}`}>
        <div className="bank-list-wrap">
          {list.length === 0 ? (
            <div className="bank-empty">
              <b>这个筛选条件下没有题</b>
              <span>换个题型，或清掉关键词试试。</span>
            </div>
          ) : (
            <ul className="bank-list">
              {list.map((e) => (
                <li key={e.id}>
                  <button
                    type="button"
                    className={`bank-item${openId === e.id ? ' on' : ''}${done.has(e.id) ? ' done' : ''}`}
                    onClick={() => setOpenId(openId === e.id ? null : e.id)}
                  >
                    <span className={`bank-type t-${e.type}`}>{TYPE_META[e.type].short}</span>
                    <span className="bank-item-main">
                      <b>{e.title}</b>
                      <span>
                        {chapterTitle(e.ch)} · {DIFF_META[e.diff]?.label ?? e.diff}
                        {e.lang ? ` · ${languageLabel(e.lang)}` : ''}
                      </span>
                    </span>
                    {isJudgeable(e) && (
                      <span className="bank-mark" title="可直接判题">
                        ▶
                      </span>
                    )}
                    {done.has(e.id) && <span className="bank-mark ok" title="已完成">✓</span>}
                    {cloud.ids.has(e.id) && (
                      <span className="bank-mark cloud" title="云端也有此题">
                        ☁
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {current && <ExerciseDetail ex={current} onClose={() => setOpenId(null)} onGoJudge={goJudge} />}
      </div>
    </div>
  );
}

/* ============================================================ 题目详情 */

type ObjectiveState = { picked: string[]; text: string; checked: boolean };

function ExerciseDetail({
  ex,
  onClose,
  onGoJudge,
}: {
  ex: BankExercise;
  onClose: () => void;
  onGoJudge: (e: BankExercise) => void;
}) {
  const done = useBankDone();
  const [st, setSt] = useState<ObjectiveState>({ picked: [], text: '', checked: false });
  const [shown, setShown] = useState(false);
  /** 上一次真正提交过的作答签名：用来防「反复点检查」把同一只怪刷成首领 */
  const lastSig = useRef('');

  // 换题时重置作答状态（用 key 包一层也行，但这里状态少，直接比较 id 更省事）
  const [lastId, setLastId] = useState(ex.id);
  if (lastId !== ex.id) {
    setLastId(ex.id);
    setSt({ picked: [], text: '', checked: false });
    setShown(false);
    lastSig.current = '';
  }

  const isChoice = ex.type === 'choice' && (ex.options?.length ?? 0) > 0;
  // 「看码写输出」有时也带选项；带选项就按选择判，不带就按文本判
  const asText = !isChoice && (ex.type === 'output' || ex.type === 'fix_error') && hasTextAnswer(ex);

  const judgeable = isJudgeable(ex);
  const unsupported = isUnsupportedLang(ex);
  const needReveal = !isChoice && !asText;
  /**
   * 只有「写代码」的题才该出现判题入口。
   * 选择题也带 reference_code（解析里附的正确写法），如果不加这道闸，
   * 一道纯选择题下面会冒出「没有内置用例 · 自由运行」，纯属噪音。
   */
  const codeLike = (ex.type === 'coding' || ex.type === 'fix_error') && !!ex.code;

  /**
   * 判分纯函数：不写状态、不产生副作用。
   * 之所以从 useMemo 里拿出来，是因为「提交」这一刻要拿着结果去写进度，
   * 而 setState 之后的 effect 里再读 verdict 会拿到上一轮的值（也难防 StrictMode 双跑）。
   */
  const evalNow = (): 'right' | 'wrong' | null => {
    if (isChoice) {
      const right = new Set((ex.correct ?? []).map((s) => s.trim().toUpperCase()));
      const mine = new Set(st.picked.map((s) => s.trim().toUpperCase()));
      const same = right.size === mine.size && [...right].every((r) => mine.has(r));
      return same ? 'right' : 'wrong';
    }
    if (asText) {
      const want = textAnswer(ex);
      return normalizeOutput(st.text) === normalizeOutput(want) ? 'right' : 'wrong';
    }
    return null;
  };

  const verdict = st.checked ? evalNow() : null;

  /**
   * 提交作答：判分 + 记账 + 反馈，一次做完。
   *
   * 记账走 recordAnswer（错题变怪物 / 重做收服 / 金币流水），
   * 同一天同一题进了今日试炼还会顺带推进 3/3 进度。
   */
  const submit = () => {
    const v = evalNow();
    setSt((s) => ({ ...s, checked: true }));
    if (!v) return;

    const sig = `${isChoice ? [...st.picked].sort().join('') : st.text.trim()}|${v}`;
    if (lastSig.current === sig) {
      // 同一份答案重复提交：只重放判定，不再记一次失败
      return;
    }
    lastSig.current = sig;

    const ok = v === 'right';
    recordAnswer({
      questionId: ex.id,
      chapterId: ex.ch,
      subject: ex.subj,
      title: ex.title,
      diff: ex.diff,
      qtype: ex.type,
      ok,
      mode: 'objective',
    });
    submitDaily(ex.id, ok);
    submitWeekly(ex.id, ok);
    if (ok) markBankDone(ex.id);
  };

  /** 自评完成：没有标准答案的题走这里，等价于「我做过了」 */
  const selfAssess = () => {
    markBankDone(ex.id);
    recordAnswer({
      questionId: ex.id,
      chapterId: ex.ch,
      subject: ex.subj,
      title: ex.title,
      diff: ex.diff,
      qtype: ex.type,
      ok: true,
      mode: 'self',
    });
    submitDaily(ex.id, true);
    submitWeekly(ex.id, true);
    pushToast({ kind: 'info', title: '已标记完成', desc: ex.title, icon: '✎' });
  };

  const togglePick = (key: string) => {
    setSt((s) => ({
      ...s,
      checked: false,
      picked: s.picked.includes(key) ? s.picked.filter((k) => k !== key) : [...s.picked, key],
    }));
  };

  return (
    <div className="bank-detail">
      <div className="bank-detail-head">
        <div>
          <h3>{ex.title}</h3>
          <div className="bank-detail-meta">
            <span className={`bank-type t-${ex.type}`}>{TYPE_META[ex.type].label}</span>
            <span>{chapterTitle(ex.ch)}</span>
            <span>{DIFF_META[ex.diff]?.label ?? ex.diff}</span>
            {ex.lang && <span>{languageLabel(ex.lang)}</span>}
            {ex.cases?.length ? <span className="ok">{ex.cases.length} 个判题用例</span> : null}
          </div>
        </div>
        <button type="button" className="bank-close" onClick={onClose} aria-label="关闭">
          ×
        </button>
      </div>

      {ex.md && (
        <div className="md-body bank-stem" dangerouslySetInnerHTML={{ __html: renderMarkdown(ex.md) }} />
      )}

      {/* ---------- 选择题 ---------- */}
      {isChoice && (
        <div className="bank-options">
          {ex.options!.map((o) => {
            const picked = st.picked.includes(o.key);
            const right = st.checked && (ex.correct ?? []).includes(o.key);
            const wrong = st.checked && picked && !right;
            return (
              <button
                key={o.key}
                type="button"
                className={`bank-opt${picked ? ' picked' : ''}${right ? ' right' : ''}${wrong ? ' wrong' : ''}`}
                onClick={() => togglePick(o.key)}
              >
                <i>{o.key}</i>
                <span>{o.text}</span>
              </button>
            );
          })}
          <div className="bank-actions">
            <button
              type="button"
              className="km-btn km-btn-sm km-btn-primary"
              disabled={st.picked.length === 0}
              onClick={submit}
            >
              对照答案
            </button>
            {verdict === 'right' && <span className="bank-verdict ok">答对了</span>}
            {verdict === 'wrong' && <span className="bank-verdict bad">再想想，答案标绿的是正确项</span>}
          </div>
        </div>
      )}

      {/* ---------- 文本作答（看码写输出 / 找错改错） ---------- */}
      {asText && (
        <div className="bank-text">
          <textarea
            className="bank-input"
            rows={4}
            value={st.text}
            placeholder="写下你的答案 / 输出"
            onChange={(ev) => setSt((s) => ({ ...s, text: ev.target.value, checked: false }))}
            spellCheck={false}
          />
          <div className="bank-actions">
            <button
              type="button"
              className="km-btn km-btn-sm km-btn-primary"
              disabled={!st.text.trim()}
              onClick={submit}
            >
              检查
            </button>
            {verdict === 'right' && <span className="bank-verdict ok">一致</span>}
            {verdict === 'wrong' && <span className="bank-verdict bad">不一致，展开参考答案对一下</span>}
          </div>
        </div>
      )}

      {/* ---------- 编程题：去判题台 ---------- */}
      {judgeable && codeLike && (
        <div className="bank-cta">
          <div>
            <b>这题可以真判</b>
            <span>
              已内置 {ex.cases!.length} 个用例，{languageLabel(ex.lang)} 在当前设备可运行。
            </span>
          </div>
          <button type="button" className="km-btn km-btn-sm km-btn-primary" onClick={() => onGoJudge(ex)}>
            去判题台
          </button>
        </div>
      )}

      {!judgeable && codeLike && !unsupported && (
        <div className="bank-cta ghost">
          <div>
            <b>没有内置用例</b>
            <span>
              可以把参考实现送进判题台，自己填 stdin / 期望输出后运行。
            </span>
          </div>
          <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={() => onGoJudge(ex)}>
            自由运行
          </button>
        </div>
      )}

      {unsupported && codeLike && (
        <div className="bank-cta warn">
          <div>
            <b>{languageLabel(ex.lang)} 暂无本地运行时</b>
            <span>两端都还不能判这道题，先看题面与参考实现自评。</span>
          </div>
        </div>
      )}

      {/* ---------- 答案 ---------- */}
      <div className="bank-answer">
        <button
          type="button"
          className="km-btn km-btn-sm km-btn-ghost"
          onClick={() => setShown((s) => !s)}
        >
          {shown ? '收起参考答案' : '显示参考答案'}
        </button>
        {!done.has(ex.id) && (
          <button type="button" className="km-btn km-btn-sm km-btn-ghost" onClick={selfAssess}>
            标记已完成
          </button>
        )}
        {done.has(ex.id) && <span className="bank-verdict ok">已完成</span>}
      </div>

      {shown && (
        <div className="bank-reveal">
          {ex.correct?.length ? (
            <p>
              <b>答案：</b>
              {ex.correct.join(' / ')}
            </p>
          ) : null}
          {ex.expect && (
            <>
              <div className="bank-sub">期望输出</div>
              <pre className="bank-pre">{ex.expect}</pre>
            </>
          )}
          {ex.code && (
            <>
              <div className="bank-sub">参考实现 · {languageLabel(ex.lang)}</div>
              <pre className="bank-pre">{ex.code}</pre>
            </>
          )}
          {ex.note && (
            <>
              <div className="bank-sub">参考答案说明</div>
              <div className="md-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(ex.note) }} />
            </>
          )}
          {ex.external && (
            <p className="bank-ext">
              <a href={ex.external} target="_blank" rel="noreferrer">
                原题链接
              </a>
            </p>
          )}
          {ex.explain && (
            <>
              <div className="bank-sub">解析</div>
              <div className="md-body" dangerouslySetInnerHTML={{ __html: renderMarkdown(ex.explain) }} />
            </>
          )}
          {!ex.correct?.length && !ex.expect && !ex.code && !ex.note && !ex.explain && (
            <p className="bank-hint">这道题没有存答案，需要按题面自己完成。</p>
          )}
        </div>
      )}

      {ex.src && <p className="bank-src">来源：{ex.src}</p>}
      {needReveal && !ex.code && !ex.correct?.length && (
        <p className="bank-hint">提示：这类题没有唯一的标准答案，自评即可。</p>
      )}
    </div>
  );
}

/* -------------------------------------------------------------- 小工具 */

/** 这题有没有可比的文本答案（看码写输出 / 找错改错的短结论） */
function hasTextAnswer(e: BankExercise): boolean {
  const t = textAnswer(e);
  return t.length > 0 && t.length <= 400;
}

function textAnswer(e: BankExercise): string {
  if (e.expect) return e.expect;
  const c = e.correct?.join('\n') ?? '';
  // 判断题的 correct 有时是 "见解析""见链接" 这类占位，不能当比对目标
  if (/^见(解析|链接|参考|上文)/.test(c)) return '';
  return c;
}
