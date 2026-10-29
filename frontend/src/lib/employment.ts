/**
 * employment.ts —— 就业八股专轨（P5）纯函数层
 * ============================================================================
 * 读 EMPLOYMENT（由 content/_tracks/employment.json 经 gen_tracks.py 生成），
 * 把四区资源 + Agent 专项整理成「八股图」节点集合，按区/专轨/模块着色。
 * 纯函数、只读、零 dispatch，与 examTracks.ts 同构，便于
 * verify_logic_chain.mjs --check-employment 断言。
 *
 * 注意：就业八股图是「资源分区图」（节点 = 仓库/网站），不依赖章节掌握度；
 * 未来若接入 interview.json 已答率，可在 buildInterviewGraph 叠加掌握度着色。
 * ============================================================================
 */
import {
  EMPLOYMENT,
  type EmpZone,
  type EmpSource,
  type AgentModule,
  type AgentLayer,
  type EmpMockPaper,
} from '../data/employment';

export interface ZoneNode extends EmpZone {
  count: number;
}

export interface GraphSource extends EmpSource {
  /** 所属区（A/B/C/D） */
  zone: string;
}

export interface InterviewGraph {
  trackId: string;
  name: string;
  zones: ZoneNode[];
  agentLayers: AgentLayer[];
  agentModules: AgentModule[];
  mockPapers: EmpMockPaper[];
  totalSources: number;
  sourceById: Record<string, GraphSource>;
}

/** 构建八股图：四区资源 + Agent 专项，节点按区着色 */
export function buildInterviewGraph(): InterviewGraph {
  const zones: ZoneNode[] = EMPLOYMENT.zones.map((z) => ({
    ...z,
    count: z.sources.length,
  }));
  const flat: GraphSource[] = zones.flatMap((z) =>
    z.sources.map((s) => ({ ...s, zone: z.zone })),
  );
  const sourceById: Record<string, GraphSource> = {};
  for (const s of flat) sourceById[s.id] = s;

  return {
    trackId: EMPLOYMENT.trackId,
    name: EMPLOYMENT.name,
    zones,
    agentLayers: EMPLOYMENT.agentTrack.layers,
    agentModules: EMPLOYMENT.agentTrack.modules,
    mockPapers: EMPLOYMENT.agentTrack.mockPapers,
    totalSources: flat.length,
    sourceById,
  };
}

/* ------------------------------------------------------------------ 导出 */

/** 把八股图渲染成 Markdown（用于导出 / 复盘） */
export function interviewGraphToMarkdown(g: InterviewGraph): string {
  const head = [
    `### ${g.name} · 八股资源分区图`,
    '',
    `> 四区 ${g.zones.length} · 资源节点 ${g.totalSources} · Agent 专项 ${g.agentModules.length} 模块`,
    '',
    '| 区 | 名称 | 资源数 | 定位 |',
    '|---|---|---|---|',
  ];
  const zrows = g.zones.map((z) => `| ${z.zone} | ${z.name} | ${z.count} | ${z.desc} |`);
  const srcHead = ['', '| 资源 | 区 | 类型 | 角色 / 特色 |', '|---|---|---|---|'];
  const srcRows = g.zones.flatMap((z) =>
    z.sources.map((s) => `| ${s.name} | ${z.zone} | ${s.type} | ${s.role} |`),
  );
  const agHead = [
    '',
    '**Agent 八股专项 · 四层骨架**',
    '',
    '| 层 | 含义 | 参考 |',
    '|---|---|---|',
  ];
  const agRows = g.agentLayers.map((l) => `| ${l.layer} | ${l.desc} | ${l.ref} |`);
  const modHead = ['', '**专项模块 → 题库**', '', '| 模块 | 题库来源 | 规模/特色 |', '|---|---|---|'];
  const modRows = g.agentModules.map(
    (m) => `| ${m.module} | ${m.sources.join('、')} | ${m.scale} |`,
  );
  const paperHead = ['', '**模拟考卷（虚拟试卷）**', '', '| 难度 | 规则 | 来源 |', '|---|---|---|'];
  const paperRows = g.mockPapers.map((p) => `| ${p.level} | ${p.rule} | ${p.source} |`);

  return [
    ...head,
    ...zrows,
    ...srcHead,
    ...srcRows,
    ...agHead,
    ...agRows,
    ...modHead,
    ...modRows,
    ...paperHead,
    ...paperRows,
    '',
  ].join('\n');
}
