# fs-ch04 · 模块系统与并发


## 一、CommonJS vs ESM（模块封装、循环依赖、require 缓存）

CommonJS（require / module.exports）同步加载、有缓存；ESM（import / export）静态可分析、异步加载、严格模式。二者在循环依赖、缓存、语法上差异显著，Node 用 .cjs/.mjs 或 package.json 的 type 字段区分。

### 🧑‍💻 程序员视角
- 新项目优先 ESM；要兼容老生态或同步加载时用 CommonJS。
- exports 只是 module.exports 的别名：一旦重赋值 module.exports = {...}，再用 exports.xxx 会失效（指向旧对象）。
- 循环依赖下 CommonJS 易拿到「未填充完」的半截 exports（属性为 undefined）；ESM 用 live binding 更安全；避免循环依赖或延迟 require。

### 🎓 博士生视角
- 每个 CJS 模块被包进 (function(exports, require, module, __filename, __dirname){}) 执行，module.exports 是返回接口；require 维护 cache[key]=module.exports，同路径第二次命中缓存不再执行。
- 循环依赖陷阱：若 a 在填充 exports 前 require(b)，而 b 又 require(a)，则 a 拿到部分 exports（尚未赋值的属性为 undefined）——因为模块执行是「边执行边暴露」。
- ESM 的绑定是 live binding（只读引用），import 的不是值拷贝而是绑定；循环依赖下不出现未定义，而是「暂存」到对方初始化完成，语义更稳。

### 📚 考研者视角
- 常考：CommonJS 与 ESM 区别（加载方式/缓存/循环依赖/语法）；require 缓存机制；module.exports 与 exports 的关系。
- 易错：认为 CJS 循环依赖总能得到完整 exports（错，可能 undefined）；认为重赋值 module.exports 后 exports.xxx 仍生效。
- 经典陈述：ESM 的 import/export 是静态的（编译期可分析、可做 tree-shaking），CJS 是动态的（运行时 require）。

## 二、worker_threads 与多核（CPU 密集 vs I/O 密集、事件循环边界）

Node 的 JS 在主线程单调用栈执行；CPU 密集任务若在主线程同步执行会占满调用栈、饿死事件循环。worker_threads 在独立 V8 实例/线程上并行执行 JS，突破「单线程」对 CPU 的限制；cluster 则 fork 多进程各占一核。

### 🧑‍💻 程序员视角
- I/O 密集业务逻辑放主线程事件循环即可（异步非阻塞足矣）；CPU 密集（压缩、加密、图像处理、重计算）放 worker_threads 避免卡 UI/接口。
- worker_threads 多线程共享内存（SharedArrayBuffer），适合需共享状态的计算；cluster 多进程内存独立，适合水平扩展无状态 HTTP 服务。
- 选 worker_threads 当任务要共享数据/频繁通信；选 cluster 当要一键利用多核且无状态扩容。

### 🎓 博士生视角
- 单线程事件循环的形式化边界：JS 主线程一次只执行一个调用栈；CPU 密集任务同步执行会占满调用栈，使事件循环无法推进（所有 I/O 回调延迟）——即「饿死」。
- worker_threads 不阻塞主事件循环，于独立线程并行执行 JS，是突破「单线程」CPU 限制的正解；libuv 线程池则负责文件/DNS/crypto 等系统调用级并行。
- cluster 的每 worker 是独立进程、独立事件循环与 V8 实例；与 worker_threads 的区别在「进程 vs 线程、内存独立 vs 共享」。

### 📚 考研者视角
- 常考：Node 为什么适合 I/O 密集、不适合 CPU 密集；worker_threads 与 cluster 区别（线程/进程、内存）。
- 易错：认为 Node 全程单线程（忽略 libuv 线程池与 worker_threads）；认为 worker 能直接共享主线程变量（需 SharedArrayBuffer/消息传递）。
- 经典陈述：事件循环被长任务阻塞的后果是「所有 I/O 延迟、请求堆积」，用 worker_threads 卸载 CPU 密集任务解决。
