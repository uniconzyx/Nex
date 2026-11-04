/**
 * LabPage.tsx —— 交互实验台
 * ============================================================================
 * 章节卡里已经挂了「本章实验」（见 components/ChapterLab），那为什么还要这一页：
 *
 *   1. **有三个学科没有章节卡**：agent（16 章）、ml（9 章）、discrete-math（1 章）
 *      走的是 AI 助手 / 408 专轨 / 考研页，不经过 LearnPage 的章节列表。
 *      它们的实验数据同样是齐的，没有入口就等于没有。
 *   2. **想比较着玩**：同一知识点在不同章里的玩法不一样（这章是沙盒、那章是
 *      拼装），要在两章之间来回切，比在长页面里上下滚要顺手。
 *   3. 它是练习的一部分（题库 / 判题台 / 实验台），所以放在练习页当第三个 Tab，
 *      不新增侧栏项 —— 侧栏 14 项已经排满了。
 *
 * 数据：`data/labs`（按学科懒加载），学科胶囊直接用 LAB_SUBJECTS，
 * 不写死列表 —— 生成器多出一个学科，这里就自动多一个胶囊。
 */
import { useMemo, useState } from 'react';

import { ChapterLab } from '../components/ChapterLab';
import { LAB_INDEX, LAB_SUBJECTS, labIndexBySubject } from '../data/labs';
import { subjectLabel, useSubject } from '../lib/subject';

const KIND_NAME: Record<string, string> = {
  sequence: '时序',
  match: '配对',
  boss: '打靶',
  fill: '挖空',
  sandbox: '沙盒',
  debug: '拼装',
};

export function LabPage() {
  const [globalSubject] = useSubject();
  /** 初值跟随全局学科；若全局学科没有实验数据，落到第一个有数据的学科 */
  const [subject, setSubject] = useState<string>(() =>
    LAB_SUBJECTS.includes(globalSubject) ? globalSubject : (LAB_SUBJECTS[0] ?? 'cpp'),
  );
  const [chapter, setChapter] = useState<string | null>(null);

  const items = useMemo(() => labIndexBySubject(subject), [subject]);
  const counts = useMemo(() => {
    const m = new Map<string, number>();
    LAB_INDEX.forEach((x) => m.set(x.subject, (m.get(x.subject) ?? 0) + 1));
    return m;
  }, []);

  const current = chapter && items.some((x) => x.chapter === chapter) ? chapter : (items[0]?.chapter ?? null);

  const pickSubject = (k: string) => {
    setSubject(k);
    // 换学科后落在该科第一章：不保留上一科的章号（名字完全不同，会直接空态）
    setChapter(null);
  };

  return (
    <div className="lab-bench">
      {LAB_SUBJECTS.length === 0 ? (
        <div className="km-lab km-lab-empty">
          <b>还没有任何实验数据</b>
          <span>
            跑一次 <code>python scripts/gen_interactive.py</code> 生成后刷新即可。
          </span>
        </div>
      ) : (
        <>
          <div className="lab-bench-subjects" role="tablist" aria-label="实验学科">
            {LAB_SUBJECTS.map((k) => (
              <button
                key={k}
                type="button"
                role="tab"
                aria-selected={k === subject}
                className={`lab-bench-subject${k === subject ? ' on' : ''}`}
                data-lab-subject={k}
                onClick={() => pickSubject(k)}
              >
                {subjectLabel(k)}
                <em>{counts.get(k) ?? 0}</em>
              </button>
            ))}
          </div>

          <div className="lab-bench-grid" role="list" aria-label="实验章节">
            {items.map((x) => (
              <button
                key={x.key}
                type="button"
                role="listitem"
                className={`lab-bench-item${x.chapter === current ? ' on' : ''}`}
                data-lab-pick={x.key}
                onClick={() => setChapter(x.chapter)}
              >
                <span className="lab-bench-item-id">{x.chapter}</span>
                <span className="lab-bench-item-title">{x.title}</span>
                <span className="lab-bench-item-kinds">
                  {x.kinds.map((k) => KIND_NAME[k] ?? k).join(' · ')}
                </span>
              </button>
            ))}
          </div>

          {current && (
            <div className="lab-bench-stage" data-lab-stage={current}>
              <ChapterLab subject={subject} chapterId={current} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default LabPage;
