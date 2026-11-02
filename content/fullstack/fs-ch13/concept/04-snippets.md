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
