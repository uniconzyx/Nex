# 远端协作：三类引用、fetch/pull 语义与 push 的安全边界
> 本节目标：把「和远端打交道」这件事精确到引用级别。每个主题按三视角解析。

---

## 一、`pull` 不是「拉取」：`fetch` / `pull` / `push` 到底动了什么

远端协作涉及**三类引用**，混淆它们是一切事故的起点：

```
本地仓库                                  远端仓库(origin)
refs/heads/main       ──push──▶         refs/heads/main
refs/remotes/origin/main ◀──fetch──      refs/heads/main   （快照，只在 fetch/push 时更新）
```

- `git fetch`：把远端有、本地没有的对象搬回来，**只更新远端跟踪引用** `refs/remotes/origin/*`。
  它不碰 `refs/heads/*`、不碰暂存区、不碰工作区——所以 fetch 是**只读感知型**命令，随时可安全执行。
- `git pull` = `git fetch` + 一次整合（`merge` 或 `rebase`，取决于 `pull.rebase` 配置）：
  - 默认 `merge`：fast-forward 时只移指针；否则生成一个新的 **merge commit**。
  - `pull.rebase=true` / `--rebase`：把本地新提交**重放**到 `origin/main` 之上，历史线性，本地 SHA 被改写。
- `git push`：把本地 commit 推给远端，并要求**远端引用更新后是纯快进**（fast-forward），否则拒绝。

判断是否需要整合的标准动作是 `git fetch` 之后看 `git log --oneline --left-right main...origin/main`，
左右两侧的提交数就是 ahead / behind（分歧度）。`examples/ex01` 用模型仓库复刻了这三种形态。

### 🧑‍💻 程序员视角
- **日常顺序应该反过来**：先 `git fetch`，自己看完差异（`git log -p main..origin/main`）再决定 merge 还是 rebase；
  不要盲信 `git pull`——它会在你不知情的情况下改写 HEAD，还可能当场产生一次冲突而你不在线。
- **CI 里的黄金组合**：`git pull --rebase` 适合个人分支（避免无意义的 merge commit 串），
  而**共享集成分支**用 `--no-ff` merge，保留「确实发生过并行开发」的拓扑证据，便于事后 blame 与回滚。
- **典型上线事故**：本地落后 12 个提交，习惯性 `--force` 推上去，队友一天的工作消失；
  事后用 `git reflog` 只能找回本地的旧位置，远端他人的提交需要从别人的本地库捞回来。
- **排查顺序**：push 被拒 → `git fetch` → `git rev-list --left-right --count main...origin/main` →
  落后则 rebase 或 merge → 冲突逐个解决 → 再 push。全程不要 `--force`。

### 🎓 博士生视角
- 引用模型的形式化：远端跟踪引用是「**上次通信时远端状态的不可变快照**」。
  它存在的意义是把「网络往返」与「本地整合」这两件事**解耦**：fetch 只改变这一个变量，因此幂等且可逆。
- `pull` 的分解式不是实现细节而是语义定义：`pull = fetch ∘ (merge | rebase)`。
  merge 的语义是**保拓扑的单调合并**（结果有两个 parent，父集是双方的祖先并集）；
  rebase 的语义是**补丁序列的重放**（对每个本地提交做三方合并，base 是它的父，ours 是已落地的新 tip）。
- 为什么 push 只允许快进：因为 push 是**对远端引用的赋值**，非快进赋值会让远端的若干 commit
  从「可达」变成「不可达」，而对端无法感知；这条约束是分布式系统里「用 CAS（比较并交换）代替无条件写」的实例——
  `--force-with-lease` 就是把无条件写改回 CAS。
- 复杂度：一次三方合并的代价是 O(N·M) 级的行匹配（Git 用 Myers / histogram 算法 + 索引优化），
  因此把长命分支拖上几周再一次性合并，成本远高于每天 rebase。

### 📚 考研者视角
- 本节属**工具链操作**，不在 408 统考大纲（数据结构 / 组成原理 / 操作系统 / 计网）内；
  但其背后的判定会被移植成笔试题：**版本号的偏序关系、DAG 上的最近公共祖先、CAS vs 无条件赋值**。
- 易混口径对比表：

  | 命令 | 更新 refs/remotes？ | 更新 refs/heads？ | 动工作区？ | 可能改写 SHA？ |
  |---|---|---|---|---|
  | `fetch` | 是 | 否 | 否 | 否 |
  | `pull`（merge） | 是 | 是（新增 merge commit） | 是 | 否 |
  | `pull --rebase` | 是 | 是 | 是 | **是**（本地提交被重写） |
  | `push` | 是（成功时） | 否 | 否 | 否 |

- 常见笔试问法：「什么是 fast-forward」「`git merge` 与 `git rebase` 的本质区别」
  —— 标准答法是**是否改写已有提交的 SHA / 是否保留真实拓扑**，而不是「哪个更好」。

---

## 二、push 为什么被拒绝，以及 `--force-with-lease` 为什么比 `--force` 安全

push 被拒的唯一常见原因是 **non-fast-forward**：你要写入的目标引用当前值不是你新值的祖先，
也就是说远端出现了你尚未整合的提交。其次是权限问题（protect branch、无写权限）与 hook 校验失败。

两种「强行推」的差别：

| 行为 | 校验 | 后果 |
|---|---|---|
| `git push --force` | 无 | 直接用本地分片覆盖远端引用，他人未整合的提交**静默丢失** |
| `git push --force-with-lease` | 校验「远端引用 == 我记录的 `origin/main`」 | 不一致就 `rejected (stale info)`，不动远端任何东西 |

`--force-with-lease` 的 lease（租约）就是**本地那份远端跟踪引用**。它保证的是
「我不会覆盖我没看过的提交」，而不是「我可以随便改写历史」——这两句话的区别常被混为一谈。
`examples/ex10` 构造了同一份落后状态，分别施加两种推送，可见 force 丢失两个队友提交，lease 直接拒绝。

### 🧑‍💻 程序员视角
- **决策树**：push 被拒 → 先 fetch → 落后则 rebase（个人分支）/ merge（共享分支）→ 冲突解决 → 再 push；
  只有在「确实必须重写**（已沟通确认过的）个人分支**历史」时才用 `--force-with-lease`。
- **共享分支回滚的正确姿势**：用 `git revert <sha>` 生成反向提交，历史只增不减，所有人拉下来都一致；
  永远不要 `reset --hard` + 强推共享分支。
- **工程护栏**：给 main / release/* 配 branch protection（禁止 force push、要求 PR 与 CI 全绿），
  把「能不能强推」从人的自觉变成**平台的硬约束**；CI 里禁止使用 `--force`，只允许 `--force-with-lease`。
- **事故复盘模板**：谁在什么时候用哪条命令推的 → 远端丢失了哪些提交 → 从谁的本地 reflog 恢复 →
  加什么护栏（保护分支 / pre-push hook）。

### 🎓 博士生视角
- push 在协议层是一次 **ref 更新协商**（receive-pack 端会检查 old-oid 是否为 new-oid 的祖先，除非命令行给出 force）；
  `--force-with-lease=<ref>:<expect>` 可显式指定期望值，等价于一次 **CAS(old=expect, new=local)**。
- 为什么 lease 仍不完美：它只对**被 fetch 更新过的那个 ref** 生效；
  如果你 `--force-with-lease` 之前刚 fetch 过，租约自然与远端一致，保护退化为「允许覆盖刚看到的提交」。
  这就是为什么语义上它叫 lease（有时效的断言）而不是 lock（锁）。
- 「引用不可变性」与「对象不可变性」要分清：Git 的**对象**是内容寻址、永远不可变的；
  **引用**是可变的指针。强推改的是引用，旧对象在 GC 前仍在对象库里——所以才有人能救回来。

### 📚 考研者视角
- 本节不属 408 纲内；相关笔试/面试问法是：「push 被 rejected 的原因是什么，怎么处理」
  标准答：远端有新提交（non-fast-forward），先 fetch 再 rebase/merge 整合后再推。
- 易错点辨析：**「`--force-with-lease` 是安全的强推」** —— 准确说法是「它是**带 CAS 校验**的强推，
  能防止覆盖未知提交，但仍会改写历史」；真正安全的回滚是 revert（追加而非篡改）。
- 可能与计网结合的提问点：把 lease 类比为 HTTP 的 `If-Match`/ETag 乐观并发控制，属于**乐观锁**而非悲观锁。

---

## 三视角小结

| 视角 | 关注 | 本节落点 |
|---|---|---|
| 🧑‍💻 程序员 | 工程决策与上线事故 | fetch 后再整合、共享分支用 revert、保护分支护栏、事故复盘顺序 |
| 🎓 博士生 | 第一性原理与协议机制 | 引用模型的解耦、merge/rebase 的语义定义、CAS 类比、对象 vs 引用不可变性 |
| 📚 考研者 | 标准考法与易错口径 | 三类引用对照表、merge vs rebase 本质区别、lease 是乐观锁而非免死金牌 |
