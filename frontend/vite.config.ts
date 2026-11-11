import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Nex 前端工程配置
// ---------------------------------------------------------------------------
// 目录约定（与 src-tauri/tauri.conf.json 对齐）：
//   frontend/            本工程（源码）
//   ../dist              构建产物 -> tauri.conf.json 的 "frontendDist": "../dist"
//                         （frontendDist 相对 tauri.conf.json 所在目录解析）
export default defineConfig({
  plugins: [react()],

  // tauri dev 会自己起 Rust 编译进程，别让 Vite 的清屏把它刷掉
  clearScreen: false,

  server: {
    // 必须与 tauri.conf.json 的 devUrl 一致
    port: 1420,
    // 端口被占用时直接报错，而不是偷偷换端口（否则 Tauri 加载到一个错的 dev server）
    strictPort: true,
    // 监听 0.0.0.0：`tauri android dev` 时真机要通过局域网访问本 dev server
    host: true,
    watch: {
      // Rust 侧编译产物别进 watch，否则 dev 时疯狂热更
      ignored: ['**/src-tauri/**', '**/dist/**'],
    },
  },

  build: {
    // 对齐 tauri.conf.json: "frontendDist": "../dist"
    outDir: '../dist',
    // 不清空 outDir：产物文件名带内容哈希，互不覆盖；
    // 清空会触发宿主安全守卫（批量删除保护），导致 tauri build 的
    // beforeBuildCommand 直接失败。需要彻底瘦身时手动 `rm -rf dist`。
    emptyOutDir: false,
    // Android WebView（系统 WebView 版本杂）保守一点，避免原生 ESM 兼容问题
    target: 'es2020',
    sourcemap: false,
    rollupOptions: {
      output: {
        // KaTeX 只服务「数学 → 公式速查」一个页面，打进主包会让首屏
        // 白白多背 ~800KB（gzip 后 ~250KB）。单独成 chunk 后，
        // 只有真的点进公式页才去拉它。
        manualChunks(id: string) {
          if (id.includes('node_modules/katex')) return 'katex';
          return undefined;
        },
      },
    },
  },

  // 依赖预构建：tauri 的 api 包走 ESM，交给 esbuild 处理
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-dom/client', '@tauri-apps/api/core'],
  },
});
