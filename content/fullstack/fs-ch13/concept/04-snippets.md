# fs-ch13 · 关键实现片段：E2E、组件、契约与门禁

> 承接 `01-测试金字塔`、`02-E2E 与组件`、`03-契约与门禁`。本节把前面反复提到的「等待条件」「行为断言」「消费者契约」「门禁配置」落成最小可运行代码。

## 1. 本节定位

测试的原则容易讲、难落地。下面四段是 §1~§3 各自最容易写错处的对照实现。

### 2. E2E：用等待条件替代 sleep

Playwright 的 web-first 断言自带自动重试，等「条件成立」而不是等「固定时间」，这是消除 flaky 的头号手段：

```ts
// 错误：await page.waitForTimeout(2000);
// 正确：断言针对不变量自动重试
await expect(page.getByRole('button', { name: '提交' })).toBeEnabled();
await page.getByTestId('order-total').waitFor({ state: 'visible' });
const total = await page.getByTestId('order-total').textContent();
expect(Number(total)).toBeGreaterThan(0);
```

### 3. 组件测试：按用户感知查询，不碰实现细节

用 `role` / `text` / `label` 这类「用户如何感知元素」的查询，重构内部实现时测试仍绿：

```ts
import { render, screen } from '@testing-library/react';

test('提交后展示总价', () => {
  render(<Cart items={[{ name: '书', price: 30 }]} />);
  expect(screen.getByRole('status')).toHaveTextContent('30'); // 不读组件私有 state
});
```

### 4. 契约测试：消费者驱动（CDC）

消费者端先写期望，生成契约文件给提供者校验，字段级破坏立即红灯：

```ts
import { Pact } from '@pact-foundation/pact';

await provider.addInteraction({
  state: '订单已创建',
  uponReceiving: '获取订单总额',
  withRequest: { method: 'GET', path: '/orders/1' },
  willRespondWith: {
    status: 200,
    body: { id: 1, total: Matchers.number() },  // 校验字段类型/存在性
  },
});
```

### 5. 质量门禁：CI 双卡（PR + 主干）

门禁既卡 PR 也卡主干 push，保证主干始终是可发布基线；覆盖率设合理下限而非 100%：

```yaml
# .github/workflows/ci.yml
jobs:
  gate:
    steps:
      - run: npm test -- --coverage
      - run: npx playwright test
    # 门禁在 pull_request 与 push(main) 都触发
on:
  pull_request:
  push:
    branches: [main]
```

覆盖率低于 80% 或 E2E 失败则红灯，红灯优先于新功能——这才是「可发布基线」的意义。

## 三视角解析
### 🧑‍💻 程序员视角
E2E 测试用 `sleep` 等待是「不稳定测试」的头号来源，应改用「等待条件」（元素可见、网络空闲）。组件测试要按「用户感知」查询（`getByRole`/`getByLabelText`），而不是按实现细节（class 名），否则重构一次测试全红。契约测试（CDC）让消费者定义期望、提供者验证，能在不启动全链路的情况下发现接口不兼容。质量门禁要双卡：PR 上跑单测 + lint（快），主干部跑 E2E（慢），否则开发者会被慢测试劝退。

### 🎓 博士生视角
测试金字塔的本质是「成本与反馈速度的权衡」：单测多、集成少、E2E 精。E2E 的脆弱性来自「跨越多层依赖」，其稳定性取决于「等待策略」而非「断言数量」。契约测试填补了「单测与 E2E 之间」的空档——它验证的是「接口契约」而非「业务逻辑」，因此比 E2E 快、比单测真实。质量门禁的设计要考虑「信噪比」：误报多的门禁会被绕过，最终形同虚设。

### 📚 考研者视角
前端/测试面试高频：
1. **测试分层**：单测、集成、E2E 的边界与比例。
2. **E2E 稳定性**：等待策略、测试隔离、数据准备与清理。
3. **契约测试**：CDC 的原理、消费者驱动的好处。
4. **CI 门禁**：lint、类型检查、单测覆盖率、构建产物体积。

```text
04-snippets.md · 结构速览（节点=小节，括号=该节代码块语言）

  [01] 2. E2E：用等待条件替代 sleep  (ts)
    |
    v
  [02] 3. 组件测试：按用户感知查询，不碰实现细节  (ts)
    |
    v
  [03] 4. 契约测试：消费者驱动（CDC）  (ts)
    |
    v
  [04] 5. 质量门禁：CI 双卡（PR + 主干）  (yaml)
    |
    v
  [END] 三视角解析收口
```
