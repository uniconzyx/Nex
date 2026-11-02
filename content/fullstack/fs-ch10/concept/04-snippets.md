# fs-ch10 · 响应式实战代码片段

> 把 §1–§3 的机制落到可粘贴运行的最小例子。每个片段都能在 `<script setup lang="ts">` 里跑。

### ref 与 reactive 的基本形态

```ts
import { ref, reactive } from 'vue'
const count = ref(0)          // 原始值用 ref
const state = reactive({ n: 0, list: [] as number[] }) // 对象用 reactive
count.value++                 // 逻辑里必须 .value
state.n++                     // reactive 直接读写
```

### computed 派生

```ts
import { computed } from 'vue'
const double = computed(() => count.value * 2)
// 只读派生；要可写用 computed({ get, set })
```

### watch 精确监听某个字段

```ts
import { watch } from 'vue'
watch(() => state.n, (nv, ov) => {
  console.log(`n: ${ov} -> ${nv}`)
})
// 不要传整个 reactive 对象又不 deep，否则深层变更不触发
```

### watchEffect 自动追踪

```ts
import { watchEffect } from 'vue'
watchEffect(() => {
  // 这里读到的响应式依赖会被自动收集
  document.title = `count=${count.value}`
})
```

### 解构保持响应性：storeToRefs

```ts
import { storeToRefs } from 'pinia'
const store = useUserStore()
const { name, avatar } = storeToRefs(store) // 仍是 ref，保响应
// 不要 const { name } = store —— 会丢响应性
```

### Pinia setup store

```ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
export const useUserStore = defineStore('user', () => {
  const name = ref('')
  const isLogin = computed(() => name.value.length > 0)
  function login(n: string) { name.value = n }
  return { name, isLogin, login }
})
```

### Pinia options store（对照）

```ts
import { defineStore } from 'pinia'
export const useCartStore = defineStore('cart', {
  state: () => ({ items: [] as string[] }),
  getters: { count: (s) => s.items.length },
  actions: { add(i: string) { this.items.push(i) } },
})
```

### 列表渲染与 key

```vue
<template>
  <li v-for="item in state.list" :key="item.id">{{ item.name }}</li>
</template>
```

### 异步 setup 配合 Suspense

```ts
// 组件 <script setup> 内
const { data } = await useFetch('/api/user')
// 父组件需用 <Suspense> 包裹，否则渲染时 data 还是空
```

## 三视角解析
### 🧑‍💻 程序员视角
`ref` 适合基本类型、`reactive` 适合对象，但 `reactive` 解构会丢响应性——解构出来的是普通值。`computed` 有缓存、`watchEffect` 没有，前者适合派生状态、后者适合副作用。`watch` 默认浅监听，监听对象内部字段要加 `deep: true`，但深监听大对象会有性能开销。`v-if` 与 `v-for` 不要写在同一元素上，`v-if` 的优先级更高会导致「拿不到循环变量」。

### 🎓 博士生视角
Vue 3 的响应式基于 `Proxy`：读取时 `track` 收集依赖、写入时 `trigger` 派发更新，相比 Vue 2 的 `Object.defineProperty` 能拦截新增/删除属性与数组索引。`ref` 与 `reactive` 的差异源于「基本类型无法被 Proxy 代理」，因此 `ref` 用 `.value` 包装。响应式系统的本质是「依赖图 + 精确触发」，理解它才能解释「为什么某些修改不触发更新」（未在渲染中读取、或对象被 `markRaw`）。

### 📚 考研者视角
前端面试高频：
1. **`ref` 与 `reactive`**：适用类型、解构丢响应性的原因、`toRefs` 的作用。
2. **`computed` 与 `watch`**：缓存机制、副作用场景、`immediate`/`deep` 选项。
3. **生命周期**：`setup` 中 `onMounted` 等钩子的执行时机、与 Vue 2 的对应关系。
4. **响应式原理**：`Proxy` 的拦截点、依赖收集与派发更新流程。
