# fs-ch10 · Vue 3 + TypeScript + Pinia：响应式原理与 ref/reactive 边界 · 常见错误

1. **解构 reactive 对象导致响应性丢失** —— 错在：`const { count } = useStore()` 或 `const { name } = reactive(form)`，之后改 `state.count` 视图不更新。

   *为什么*：解构出来的 `count`/`name` 只是那一刻的值（原始值或普通引用），和原 Proxy 断了联系。后续对原对象的修改不会再反映到这个局部变量上，effect 也早已不订阅它。

   *怎么改*：需要解构并保响应性时，用 `toRefs(state)`（或 Pinia 的 `storeToRefs(store)`）把每个字段转成 ref；props 用 `toRef(props, 'key')`。不要直接解构响应式源。

2. **在响应式对象上整体替换却指望旧引用更新** —— 错在：`let state = reactive({ a: 1 }); state = reactive({ a: 2 })`，然后发现旧的订阅没反应。

   *为什么*：你把变量指到了一个全新的代理对象，旧代理上的 effect 依赖仍然挂在旧对象上，新对象没人订阅。这是「重新赋值变量」与「更新对象内容」混淆。

   *怎么改*：原地修改而非替换：`Object.assign(state, newObj)` 或 `state.a = newObj.a`。确实需要替换时用 ref 包一层（`const state = ref({...})`），替换 `state.value`。

3. **忘记 ref 要写 .value** —— 错在：`if (count > 0)`、`count++`、`emit(count)` 直接拿 ref 当值用，得到的是 ref 对象。

   *为什么*：ref 是个容器对象，`count` 本身不是数字。模板里编译器帮你拆了 `.value`，但 `<script setup>` 逻辑里不会，于是比较、自增、传参都作用在对象上，结果恒为 NaN 或 `[object Object]`。

   *怎么改*：逻辑代码里一律 `count.value` 读写。若值要频繁当普通变量用，先 `const count = toRefs(state).count` 或在一开始就用 computed 派生。

4. **对 Proxy 手写的玩具响应式发现 push 不触发** —— 错在：自己用 `new Proxy` 写了 reactive，数组 `list.push(1)` 后 effect 不重跑。

   *为什么*：V8 里 `Array.prototype.push` 对 `length` 的改写走快速路径，会绕过 Proxy 的 set 拦截。真正的 Vue 在 get 拦截里对 push/splice 等方法做了 instrument，执行完原方法后手动 `trigger(length)`。

   *怎么改*：若自研响应式，必须在 get 拦截里对数组方法包一层：调用原方法后手动派发 length 及索引。直接项目里用 Vue 自带的 `reactive`，不要重造轮子。

5. **shallowRef 内部改字段不触发** —— 错在：`const big = shallowRef({ items: [] }); big.value.items.push(1)`，视图没更新。

   *为什么*：shallowRef 只对 `.value` 的**整体替换**做响应，它不会递归代理内部对象，所以 `big.value.items.push` 改的是内部普通数组，没经过任何拦截。

   *怎么改*：要么整体替换 `big.value = { ...big.value, items: [...big.value.items, 1] }`，要么改用 `ref`/`reactive` 拿深层响应，要么明确你就是要 shallow 并手动 `triggerRef(big)`。

6. **把响应式对象直接当 Map 的 key** —— 错在：`const m = new Map(); m.set(reactiveObj, 'x')`，之后用另一个看起来一样的对象去查却查不到。

   *为什么*：Map 用 `SameValueZero` 比较 key，两个「内容相同但引用不同」的代理对象不相等。而且普通 Map 对 key 的存取不经过 Vue 的 instrument，无法触发响应。

   *怎么改*：用对象的稳定 id（如 `user.id`）当 key，而非对象本身；若需要响应式集合，用 Vue 提供的 `reactive(new Map())` 或 `Map` 的响应式封装，保证 set/delete 能派发。

7. **在 store 的 state 之外放模块级可变变量** —— 错在：store 文件里写了 `let cache = {}`，在 action 里改它，以为它是「全局状态」。

   *为什么*：这个 `cache` 脱离了 Pinia 的响应式与单例管理：它不受 devtools 追踪、刷新不重置、多个测试间会串味，和「藏在组件外的全局变量」没区别。

   *怎么改*：所有可变状态都进 `ref`/`reactive` 并由 store 返回；需要跨 store 共享就抽到 composable 或第三个 store，让状态始终在响应式系统里。

8. **Pinia 持久化把 token/敏感信息落盘** —— 错在：`persist: true` 把整个 user store（含 token、权限）写进 localStorage。

   *为什么*：localStorage 任何脚本可读、易被 XSS 窃取，把认证凭据持久化等于把钥匙放门口。而且刷新后 hydrate 可能读到过期/被篡改的权限。

   *怎么改*：持久化只挑非敏感的偏好类字段（主题、语言）；token 放内存（ref）或 httpOnly cookie。用 `persist: { paths: ['theme', 'lang'] }` 白名单精确控制。

9. **store 间循环依赖** —— 错在：`storeA` 里 `useStoreB()`，`storeB` 里又 `useStoreA()`，初始化时报错或状态错乱。

   *为什么*：两个 store 互相引用，初始化时谁先建谁就被对方拉去建另一个，形成环。轻则报错，重则拿到半成品实例、派生值算错。

   *怎么改*：把共享逻辑抽到第三个 store 或纯 composable；如果 A 真需要 B 的某个值，考虑让 B 只暴露 getter、A 在 action 里按需调用而非在 setup 顶层互相调用。

10. **用 reactive 包原始值** —— 错在：`const x = reactive(5)` 或 `reactive('hello')`，结果不是想要的。

   *为什么*：reactive 只接受对象/数组/集合。传入原始值会被直接原样返回（非代理），此后读写都不具备响应性，等于白写。

   *怎么改*：原始值一律用 `ref`：`const x = ref(5)`。需要「可能是值也可能是对象」的匀质处理时，也优先 ref（ref 可以装对象）。
