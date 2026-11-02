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
