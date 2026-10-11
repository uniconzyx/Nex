# fs-ch03 易错点（Pitfalls）

1. **`typeof null === 'object'`** —— `typeof null` 返回 `'object'`，无法用它区分 null 与对象。✅ 判对象用 `x !== null && typeof x === 'object' && !Array.isArray(x)`。

2. **用 `==` 做宽松比较引发隐式转换** —— `0 == ''`、`'0' == false`、`[] == false`、`null == undefined` 都为真，导致逻辑错误。✅ 默认用 `===`，需要容错用 `Object.is` 或 `??`/`?.`。

3. **把 `NaN` 当普通值比较** —— `NaN === NaN` 为 `false`，`NaN == NaN` 也为 `false`，无法用相等判断。✅ 用 `Number.isNaN(x)`（不会把非数字误判成 NaN）。

4. **`var` 循环闭包打印「最后一项」** —— `for (var i...) { cb(() => i) }` 所有回调共享同一个 `i`，最终都拿到终值。✅ 用 `let`（每块新绑定）或在循环内 `bind(i)`。

5. **TDZ 中访问 `let/const`** —— 在声明语句之前访问会抛 `ReferenceError`，而非像 `var` 那样得到 `undefined`。✅ 把 `let/const` 声明放在使用前，避免块顶部「先引用」。

6. **`this` 在回调中丢失** —— `const f = obj.method; f()` 或把方法当回调传入，隐式绑定丢失、`this` 变 `undefined`/全局。✅ 用箭头函数捕获外层 `this`，或 `bind` 固化。

7. **箭头函数当对象方法** —— 箭头没有自己的 `this`，`obj = { fn: () => this.x }` 里的 `this` 指向外层词法作用域而非 `obj`。✅ 需要 `this` 归对象时用普通方法。

8. **混淆 `prototype` 与 `__proto__`（原型）** —— `F.prototype` 是构造函数上给实例用的原型；实例的内部原型是 `[[Prototype]]`（`Object.getPrototypeOf`）。改 `__proto__` 性能差。✅ 用 `class` / `Object.create` / `Object.getPrototypeOf`。

9. **继承后忘记补 `constructor`** —— 手写 `Sub.prototype = Object.create(Base.prototype)` 后，`sub.constructor` 会沿链指到 `Base`。✅ 补 `Sub.prototype.constructor = Sub`。

10. **把微任务当成宏任务排序** —— 认为 `setTimeout(fn,0)` 比 `Promise.then` 先执行。实际微任务（Promise.then / queueMicrotask / await 续体）一定早于下一轮宏任务。✅ 记住「同步→清空微任务→一个宏任务」的节奏。

11. **`Promise.all` 因一个失败整体挂掉** —— 任一 reject 立刻让整个 `all` reject，即使其他已成功。✅ 需要「成败都要」用 `Promise.allSettled`；需要「取第一个成功」用 `Promise.any`。

12. **`await` 串行拖慢** —— 写 `for` 里逐个 `await` 请求，本可并行的被串行化。✅ 先 `const ps = arr.map(fetch)` 建好 Promise，再 `await Promise.all(ps)`。

13. **`async` 函数被当同步返回** —— `async function f(){ return 1 }` 返回的是 `Promise`，调用处拿到的是 Promise 而非 `1`。✅ 用 `await f()` 取值，或对结果 `.then`。

14. **`JSON.parse(JSON.stringify(x))` 深拷贝丢信息** —— `undefined`、函数、`Symbol` 键会被丢弃，`Date` 变字符串、`RegExp` 变 `{}`，循环引用直接报错。✅ 结构化数据用 `structuredClone`，特殊类型用专用库（如 lodash.cloneDeep）。
