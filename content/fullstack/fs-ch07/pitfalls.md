# fs-ch07 易错点（Pitfalls）

1. **把服务端状态和客户端状态一锅端进全局 store** —— 服务端状态是「可被他人修改、随时过期」的副本，需要 TTL/失效/去重/重试；客户端状态（弹窗开关、输入草稿）本地存活即可。✅ 分两类：服务端状态交给专用数据层（本章 ex04 的 TTL/SWR、ex02 的去重取消、ex09 的分页合并），客户端状态用组件本地 state 或轻量 store（ex01）。判据一句话：「刷新页面后还要从服务器重新取吗？」

2. **以为「状态变了才重渲染」是自动的** —— 只有**引用**变化才触发重渲染。若 reducer 的 `default` 分支返回新对象（如 `{...state}`），无意义的 action 也会通知订阅者。✅ 未知 action 必须原样返回旧引用：本章 ex01 实跑 `unknown_action_keeps_identity=true` 且 `renders_after_noop_action=3`（3 次真实变更对应 3 次通知，无操作不通知）。

3. **乐观更新只写「成功路径」，不写回滚** —— 断网或 422 时，本地乐观插入的条目会永远停留在「待同步」状态，用户看到幽灵数据。✅ 乐观更新必须具备三件套：临时 id、失败回滚、并发有序结算。本章 ex03 用正反两组证明：成功 `success_count_kept=true`（保留且 id 由 tmp-1 变 101），失败 `after_rollback_count=0` 且 `failure_state_restored=true`（状态回到操作前）。

4. **并发请求同一资源重复发出、且不取消过期请求** —— 既不省带宽，又会「竞态覆盖」：先发的慢请求后到，把新数据覆盖回旧值（搜索框输入 `a`→`ab` 的经典 bug）。✅ in-flight map 去重 + 取消过期请求。ex02 实跑：3 个并发同 key 只发 1 次（`sent_while_inflight=1`，`deduped_flags=false,true,true`），取消的请求 `cancelled_result=null` 不投递。

5. **把 TTL 缓存当成二态（命中/未命中）** —— 漏掉 `stale` 这一态，就无法实现「先给旧值、后台刷新」的丝滑体验，只能白屏等待。✅ 三态建模：`fresh`（直接可用）、`stale`（先给旧值 + 后台刷新）、`expired`（返回空）。ex04 用整数逻辑时钟给出精确边界：`ttl=100, swr=200` 时 `t50=fresh`、`t110=stale`（`t110_value_served=v1`，`t110_is_usable=true`）、`t310=expired`（`t310_value=null`）。

6. **无限滚动只做「追加」，不做「去重 + 稳定排序」** —— 网络乱序到达时，第 2 页可能与第 1 页重叠（并发写入或重复触发加载），表现为列表里出现重复项或顺序错乱。✅ 合并层必须幂等 + 可交换。ex09 实跑：乱序到达（p3,p1,p2）合并后 `out_of_order_ids=1,2,3,4,5` 且 `order_stable=true`；重叠页去重后 `merged_count=4`（`raw_count=5`，`duplicates_removed=1`，`no_duplicate_ids=true`）。

7. **嵌套结构直接在组件里消费，不归一化** —— 同一条用户数据在 N 条记录里出现 N 次，改一次要改 N 处（更新异常），且深比较成本高。✅ normalize 成实体表 + id 索引。ex08 实跑：3 条 post 携带 3 份 author，归一化后 `normalized_user_count=2`、`dedup_saved=1`，且还原无损 `roundtrip_equal=true`。

8. **把高频变化的值（输入框内容）放进 Context** —— Context 变化会广播给所有消费者，导致整棵树每次按键都重渲染，主线程卡顿。✅ Context 只放低频环境值（主题、语言、当前用户）；高频值用组件本地 state，或按关注点拆分多个 Context，或引入支持选择器的外部 store。

9. **组件「又受控又非受控」** —— 初始由内部 state 管理、后来又传 `value` 控制，运行时会警告「已把受控组件改为非受控」，且行为在两次渲染间不一致。✅ 二选一并写进 API：受控用 `value + onChange`（父是唯一事实来源），非受控用 `defaultValue` 并明确「仅初始值」。不能混用。

10. **以为前端校验能替代后端校验** —— 前端运行在攻击者完全控制的环境，校验逻辑可被绕过；把安全依赖前端等于没有安全边界。✅ 双重防线：前端拦体验（即时反馈、少一次往返），后端守边界（不可绕过）；且两端**共享同一份 schema**，避免「前端说合法、后端说 422」的割裂。ex06 的 6 类非法用例既是前端也是后端的判据。

11. **校验只做类型、不做边界/正则/多余字段** —— ex06 实跑要求：缺必填 `req_missing_title=$.title: required`、正则不过 `req_bad_pattern=$.status: must match ^(draft|published)$`、类型不符 `req_bad_float=$.score: expected integer`、越上界 `req_bad_max=$.score: maximum is 100`、多余字段 `req_bad_extra=$.extra: additional property not allowed`。✅ 六类（必填/类型/边界/枚举或正则/多余字段/顶层类型）都要显式声明，并输出字段路径供前端精确定位。

12. **只校验请求、不校验响应** —— 服务端也可能违约（字段类型不符、本该非空却返回 null），客户端会拿到「类型正确、语义错误」的对象，崩在渲染层而不是接口层。✅ 边界处双向校验。ex06 的 `res_bad_all_rejected=true (2/2)`、`res_bad_min=$.id: minimum is 1` 就是拦服务端自身违约的用例。

13. **列表页只写 success 态，漏掉 empty / error** —— 请求成功但结果为空时显示空白区（用户以为坏了），请求失败时显示 `undefined` 或整页崩溃。✅ 四态状态机。ex05 实跑：`happy=loading->success`、`empty=loading->empty`、`error_then_retry=loading->error->loading->success`、`retry_ignored_when_ok=loading->success->success`（非错误态 RETRY 必须是幂等无操作）。

14. **把所有错误都做成一个「出错了 + 重试」按钮** —— 400/422 是参数错（重试必然再失败），401 需重新登录，403 无权限，5xx/超时才可重试。✅ 按错误类型分支：可重试显示重试、不可重试显示修正提示、需认证跳登录；并让错误体携带机器可读的 `type`（承接 fs-ch05 的 RFC 9457），使分支程序化而非匹配文案。

15. **长列表全量渲染、或以为「代码切得越碎越好」** —— 1000 行全量渲染会创建上千 DOM 节点；而过度代码分割会因请求往返（RTT）惩罚反而拖慢首屏。✅ 列表用虚拟化：ex07 的窗口公式在任何滚动位置只渲染 3~14 行（`total=1000` 而 `count` 仅 3~14），并保证 `end ≤ total`；代码按「路由 / 重组件」切，切分点数由「字节收益」与「往返惩罚」平衡决定。

16. **并发请求不设上限、或设了上限却等整批完成才补位** —— 无上限会打满连接、抢占关键请求并压垮后端；等整批完成才启动下一批会让并发出现空档。✅ 优先级队列 + 并发上限，且**完成一个立刻补位**。ex10 实跑：上限 2 时 `peak_after_admit=2`、`max_concurrency_respected=true`，完成 `b` 后立即补入 `c`，最终 `all_finished=b,d,c,e,a`（高优先级先出、同优先级 FIFO）。

17. **用 `div` 当按钮、图标按钮不写可访问名** —— `<div onClick>` 没有键盘焦点、不响应回车/空格、屏幕阅读器也不播报；图标按钮若无 `aria-label`，辅助技术只能读成「按钮」。✅ 语义化标签 + 可访问名。ex12 静态遍历实跑：`rules=img-alt,button-name`、`a11y_violations=2`（一张缺 `alt` 的图 + 一个既无文本又无 `aria-label` 的按钮），这两条都是可被程序自动判定的硬约束。
