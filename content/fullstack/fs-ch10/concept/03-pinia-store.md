# Pinia 状态管理与组合式 store

Pinia 是 Vue 官方推荐的状态管理库，定位是「Vuex 的继任者，但更简单」。它建立在 Vue 3 响应式
之上，所以你写的 store 内部就是 ref / reactive / computed，没有 Vuex 那一套 `state`、`mutations`、
`actions`、`getters` 的割裂。理解 Pinia 的关键，是先理解它只是「把一组响应式状态 + 派生值 +
修改方法，按模块封装，并保证全局单例」。

```text
defineStore 的两种写法：
    Option 式   state / getters / actions          直观，像 Vuex
    Setup 式    ref / computed / function           与组合式 API 一致，更灵活

    export const useUser = defineStore('user', () => {
      const profile = ref(null)
      const isLogin = computed(() => !!profile.value)
      async function login() { /* ... */ }
      return { profile, isLogin, login }
    })

store 之间依赖：在 action 里调另一个 useXxxStore()
    （不要放模块顶层，避免初始化顺序问题）
    循环依赖 -> 拆出第三个 store，或用事件/回调解耦

要点：
    store 是单例，跨组件共享同一份状态
    直接解构会丢响应性 -> 用 storeToRefs()
    setup 式返回的 ref 在模板里自动解包
```

## 一、写法、依赖与 Vuex 对照

### defineStore 的两种写法

Pinia 提供两种定义 store 的风格：

1. **Options 写法**（贴近 Vuex 心智）：`defineStore('id', { state: () => ({}), getters: {...},
   actions: {...} })`。state 是返回初始对象的函数（必须函数，避免多实例共享同一对象引用），
   getters 类似组件的 computed，actions 里放修改逻辑。
2. **Setup 写法**（贴近 `<script setup>` 心智）：`defineStore('id', () => { const count = ref(0);
   const double = computed(() => count.value * 2); function increment(){ count.value++ }
   return { count, double, increment } })`。函数体内你直接用 Vue 的组合式 API，返回要暴露的成员。

Setup 写法更灵活：你可以在 store 里用 `watch`、用其他 composable、甚至用条件逻辑决定暴露什么。
绝大多数新项目推荐 Setup 写法，因为它复用了你已经在组件里熟悉的响应式思维，没有额外概念。

### store 之间的依赖

真正的应用很少只有一个 store。Pinia 允许 store 之间互相调用：在某个 store 的 setup 函数（或
action）里，直接 `useOtherStore()` 拿到另一个 store 的实例并用它的状态/方法。因为是单例，
「A store 依赖 B store」只是「A 在某处调用了 B 的 getter/action」，不会造成重复实例化。
要注意避免**循环依赖**（A 用 B、B 又用 A）：把共享逻辑抽到第三个 store 或 composable 里，是
更干净的解法。

### 持久化

Pinia 本身不内置持久化，但官方有 `pinia-plugin-persistedstate` 插件：在 `createPinia()` 上
`use()` 它，然后在 store 里声明 `persist: true`（Options 写法直接加字段；Setup 写法用
`defineStore` 第三个参数）。它会把指定状态序列化进 `localStorage`/`sessionStorage`，刷新页面
后自动 hydrate。这里要分清：持久化的是「状态数据」，不是「getter 的派生结果」——派生值应当
每次从 state 算出来。还要注意别把敏感信息（token、密码）塞进持久化，那会落盘到浏览器。

### 与 Vuex 的区别

| 维度 | Vuex | Pinia |
|---|---|---|
| 写法 | state/mutations/actions/getters 分离 | Setup 或 Options，内部就是 ref/composable |
| mutations | 必须，且同步 | 没有，action 可直接改 state |
| 类型推导 | 一般，需声明 | 基于 TS 原生推断，几乎零样板 |
| 模块 | modules + 命名空间 | 每个 store 天然独立，无需命名空间 |
| 体积/复杂度 | 较重 | 轻，API 更少 |

Vuex 的 `mutations` 当初是为了「所有状态变更可追踪、可被 devtools 时间旅行」。但实践中它造成了
大量样板（`commit('SET_X')` 的字符串魔法），而 Pinia 借助 `patch` 和 devtools 插件同样能做到
变更追踪，却不必强迫你写 mutation。所以 Vue 官方明确：新项目用 Pinia，Vuex 进入维护模式。

## 二、四个高频陷阱与组织方式

### state 必须是函数，不是对象

`defineStore('id', { state: () => ({...}) })` 里 state 是函数，不是对象字面量。原因和 React 的 `useState` 初始化函数一样：如果写成对象，所有 store 实例会**共享同一份引用**（因为对象字面量只求值一次），一个地方改了，别处全跟着变，等于全局可变单例的灾难。写成函数，每次实例化都返回全新对象，单例由 Pinia 自己保证（同一个 id 只建一次），二者分工清晰。Setup 写法里 `const x = ref(0)` 同理——ref 每次调用都新建，不会有共享问题，所以 Setup 写法天然避开了这个坑。

### Options 写法里 action 的 this 绑定

Options 写法的 action 里用 `this` 访问 state 和别的 action（`this.count++`、`this.otherAction()`）。要注意：**不要在 action 里把 `this` 传给别的函数的回调并期望它还是 store**——回调里的 `this` 取决于调用方式。需要传递 store 本身时，用 `getActivePinia()` 或把 `this` 先存到局部变量 `const store = this`。Setup 写法天然没有这个问题，因为所有成员都是闭包里的局部变量，不存在 `this` 绑定陷阱，这也是推荐 Setup 写法的一个隐形理由。

### Pinia 是 Vue 插件，也是可组合的能力

`createPinia()` 产生的 pinia 实例通过 `app.use(pinia)` 安装，之后 `useStore()` 才能工作。这意味着 store 能拿到 Vue 的注入上下文、能配合 `provide/inject`、能在测试里用 `setActivePinia(createPinia())` 重置——每个测试前重置，避免跨测试串状态。持久化、请求管理等都是以「Pinia 插件」形式挂在 pinia 实例上的，插件统一在 store 创建后对其加工（加 `$subscribe`、加持久化字段）。理解「Pinia 是插件体系」能帮你把横切能力收敛到一处，而不是散在业务代码里。

### 多 store 的组织与依赖图

中大项目不会只有一个 store。按「业务域」切分（user / cart / catalog / ui）比按「数据类型」切分更利于维护。store 间可以互相 `useXStore()`，但要把依赖画成图：确保无环、控制深度（一个 store 调太多别的 store 会难推理事务与一致性）。如果 A 和 B 互相需要，把共享逻辑抽到第三个 store 或 composable，这是分层纪律在状态层的体现。devtools 里能看到每个 store 的依赖与变更历史，是排查「谁改了我的状态」的利器，也是相比散落 ref 最大的可观测性优势。

## 三、跨框架对照、边界与反模式

### 与 React 状态管理对照

把 Pinia 和 React 生态对照很有启发：Zustand 也是「create 一个 store、组件里 hook 取用、默认浅比较订阅」，思想上和 Pinia Setup 写法几乎一致；Redux 则强制单一 store + reducer 纯函数 + action 派发，样板更重、可预测性更强。Vuex 当年更接近 Redux 的范式（mutation/action 二分），Pinia 则向 Zustand 靠拢——这说明在「可预测」与「少样板」之间，社区整体选择了后者，前提是底层响应式足够可靠。选型时看清这条演进线，比盲目追新更有意义。

### 状态该放在 Pinia 还是组件内

一个实用的判据是问「这份状态会被多少个组件同时需要」。如果只有一个组件使用、并且生命周期随组件生灭，那就放组件内的局部状态即可，没必要请出全局 store，否则会让简单的东西变复杂。如果多个互不相关的组件都要读同一份数据，或者数据需要在组件卸载之后依然存活（比如当前登录用户、界面主题、购物车），那就放进全局 store。在这两个极端之间，还有一种中间情况，比如两个相邻的父子组件共享状态，这时候优先用属性下发配合事件上抛，或者用法提供与注入，而不是动辄上全局状态。滥用全局状态会让依赖关系变得隐式，任何组件都能改任何状态，等于退回全局变量的混乱年代，出问题时根本不知道是谁改的。

### 与后端的数据流关系

前端 store 绝对不是后端的缓存，这个姿态必须摆正。正确的认知是：store 持有的是「当前视图需要的、已经拉取过的数据」，而真正权威的数据源始终是后端。刷新、失效、跨标签页同步这些事情，应该向后端或者持久化层负责，而不是假设前端 store 永远是对的。常见的错误做法是把后端返回直接塞进 store 当成真相，结果多个页面各自改了 store、彼此互不一致，用户在一个页面改了名字，另一个页面还是旧的。记住一句话：store 是本地工作副本，不是权威数据源，需要强一致的时候，回去问后端，而不是相信本地那一份。

### 常见反模式与坏味道

第一种，在 store 里放会随着渲染变化的瞬时界面状态，比如某个弹窗是否打开，这类状态本属于组件，放进全局会让完全无关的组件发生无谓的重渲染。第二种，把异步请求的加载中与出错状态散落在各个组件里，而不是用统一的异步动作去封装，导致加载逻辑重复且难以统一处理。第三种，在状态之外用模块级的可变变量当隐藏的全局状态，测试和刷新都会出问题，因为它绕过了 store 的管理。第四种，每个组件都取出 store 之后直接改状态，绕过了动作的语义，应该通过动作去修改，让每一次变更都可追踪、可加副作用。识别这些坏味道，store 才能长期保持清爽，否则用久了必然膨胀成泥潭。

## 四、拆分策略与收口

### 大型应用的 store 拆分策略

当单个 store 膨胀到几百行的时候，就该拆了。拆分的维度建议按业务域来拆，比如用户、订单、商品、界面，这比按数据类型拆（所有列表放一起、所有表单放一起）更利于维护，因为需求变更通常是按业务域发生的。拆分之后要注意依赖方向：底层域不应该依赖上层域，共享逻辑抽到第三个 store 或者组合式函数里，跨域调用用显式函数而不是隐式全局读取。开发工具能直观地看到每个 store 的变更流，是验证拆分是否合理的好工具，如果某个 store 被几乎所有其它 store 依赖，说明它可能承担了不该承担的共享职责，需要再拆。

### 一句话收口

Pinia 不是全局变量的新马甲，而是被单例管理、可被开发工具追踪、有明确边界的一组响应式状态。用它的纪律，决定了它帮你还是害你。

## 三视角解析

### 🧑‍💻 程序员视角
- 新项目无脑选 Setup 写法：store 里就是 `ref`/`computed`/`function`，和组件里一个样，迁移成本为零。需要持久化加 `pinia-plugin-persistedstate`，别手搓 localStorage。
- store 间依赖直接在被依赖处 `useOtherStore()` 调用即可，单例保证不会重复建。出现循环依赖就把公共逻辑抽成第三个 composable。
- store 里不要在 state 之外放可变模块级变量——那会变成「store 之外的隐藏全局态」，刷新/测试时行为诡异。所有可变状态都进 `ref`/`reactive`。
- 持久化只存 state、不存 getter 结果，更不存 token 这类敏感信息。这就和「不要把堆栈返前端」一样，是边界安全意识在状态层的延伸。

### 🎓 博士生视角
- Pinia 把「状态管理」从「框架特供的范式」（mutation/action 二分）降维成「响应式原语的组合」，本质上承认了：一旦有了可靠细粒度响应式，全局状态只是「被单例共享的一组 ref」。这是 API 极简主义对历史冗余的清理。
- Vuex 的 mutations 是把「状态变更」当作一等公民来约束（类似把数据库写操作集中化），代价是开发体验；Pinia 转而信任响应式 + devtools 的变更捕获。这反映了前端状态管理从「强约束范式」向「约定 + 工具」的范式迁移，与 React 社区从 Redux 向 Zustand/Jotai 的迁移同构。
- store 间调用即「依赖注入」的轻量形式：每个 store 是带状态的服务，通过函数调用而非全局总线互联。其依赖图若失控（循环），与任何 DI 容器一样会爆炸，因此同样需要「分层」与「抽取共享」的纪律——这恰好和 fs-ch11 的分层边界思想呼应。

### 📚 考研者视角
- 与 408「单例模式」对照：Pinia 的 store 是全局单例，保证全应用拿到同一份状态；这正是单例模式「全局唯一访问点」的落地。但要小心单例的副作用（测试隔离），Pinia 在测试里提供 `setActivePinia` 重置。
- 记忆锚点：**Pinia = 单例 + 组合式响应式；Setup 写法复用 ref/computed；不再有 mutation**。
- 对比记忆：Vuex 强制 mutation（同步改 state）、action（可异步）分离，像「写操作走专用通道」；Pinia 取消这层强制，更贴近直觉但少了一道约束。
