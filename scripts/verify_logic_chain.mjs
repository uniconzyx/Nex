/**
 * verify_logic_chain.mjs —— 游戏逻辑链「严密性」守门脚本（可玩性增强 · 第 4 项）
 * ============================================================================
 * 把 lib/logicChain.ts 的三个纯函数（isUnlocked / dependencyIssues / stateViolations）
 * 在真实运行时跑一遍断言，确保逻辑链地基与 LearnPage / nextAction 的接线是对的。
 *
 * 为什么是 .mjs 套 esbuild：
 *   逻辑层是 TypeScript（在 frontend/src/lib 里），本机没有全局 tsx/vite-node，
 *   但 frontend 依赖里带 esbuild。这里用 esbuild 把 logic_chain_checks.ts 打包成
 *   临时 .mjs 再 node 执行，零额外安装、和 vite build 同一套工具链。
 *
 * 退出码：全过 = 0；任意断言失败 = 1。
 * 用法：node scripts/verify_logic_chain.mjs
 * ============================================================================
 */
import { build } from '../frontend/node_modules/esbuild/lib/main.js';
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const root = process.cwd();
const mode = process.argv.includes('--check-summary') ? 'summary' : 'logic';
const entry = join(root, 'scripts', mode === 'summary' ? 'summary_checks.ts' : 'logic_chain_checks.ts');
const out = join(mkdtempSync(join(tmpdir(), mode === 'summary' ? 'sum-' : 'logic-')), 'checks.mjs');

console.log(`› esbuild 打包${mode === 'summary' ? '总结表层' : '逻辑层'}…`);
await build({
  entryPoints: [entry],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile: out,
  logLevel: 'warning',
  absWorkingDir: root,
});

console.log('› 运行断言…\n');
const mod = await import('file://' + out);
// logic_chain_checks.ts 在底部自行 process.exit；这里兜底清理临时文件
rmSync(out, { recursive: true, force: true });
void mod;
