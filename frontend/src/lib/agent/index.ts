/**
 * agent/index.ts —— Agent 层的唯一入口
 *
 * 分层的读法：
 *   types.ts     契约（工具、动作、观察、报告、planner）
 *   tools.ts     手（7 个工具，全部纯函数 + 注入式 runner）
 *   scenarios.ts 场景（S1 诊断 / S2 实验）+ 规则兜底序列 + 实验模板
 *   loop.ts      脑与手的连接（plan → act → observe → 回填，含降级）
 *   report.ts    交付（数字可溯源审计 + .ipynb 导出）
 *
 * 外部只需要 import 这个文件（一个例外：llmPlanner.ts 依赖网络层，
 * 单独 import `./llmPlanner`，不从这里导出——见该文件头的说明）。
 */

export * from './types';
export * from './tools';
export * from './scenarios';
export * from './loop';
export * from './report';
