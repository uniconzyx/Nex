# title: 熔断器状态机：closed / open / half-open 的 40 次请求实录
# 本地模拟：下游在 1.0s~2.5s 故障，2.6s 恢复。对比「无熔断」与「3 次失败即熔断」。
# 关键指标不是「拦了多少请求」，而是「故障期间浪费了多少上游调用」与「恢复要多久」。

class Breaker:
    def __init__(self, threshold=3, open_sec=1.0, probes=2):
        self.threshold = threshold
        self.open_sec = open_sec
        self.probes = probes
        self.state = "closed"
        self.fails = 0
        self.opened_at = 0.0
        self.probe_ok = 0
        self.log = []
        self.calls = 0
        self.fast_fail = 0
        self.success = 0

    def _to(self, state, t, why):
        self.state = state
        self.log.append((t, state, why))

    def call(self, t, healthy):
        if self.state == "open":
            if t - self.opened_at >= self.open_sec:
                self._to("half-open", t, "冷却结束，放探针")
                self.probe_ok = 0
            else:
                self.fast_fail += 1
                return "fast_fail"

        self.calls += 1
        ok = healthy
        if ok:
            self.success += 1
            if self.state == "half-open":
                self.probe_ok += 1
                if self.probe_ok >= self.probes:
                    self.fails = 0
                    self._to("closed", t, f"{self.probes} 次探针成功")
        else:
            if self.state == "half-open":
                self.opened_at = t
                self._to("open", t, "探针失败，重新计时")
            else:
                self.fails += 1
                if self.fails >= self.threshold:
                    self.opened_at = t
                    self._to("open", t, f"连续 {self.threshold} 次失败")
        return "ok" if ok else "error"


def healthy_at(t):
    return not (1.0 <= t < 2.6)


print("场景：40 次请求，每 100ms 一次；下游 1.0s 起故障，2.6s 恢复")
print("熔断配置：连续 3 次失败 → open 1.0s → half-open 放 2 个探针\n")

b = Breaker()
timeline = []
for i in range(40):
    t = i * 0.1
    r = b.call(t, healthy_at(t))
    timeline.append(r)

print("状态迁移：")
for t, state, why in b.log:
    print(f"  t={t:>4.1f}s  -> {state:<9} ({why})")

print(f"\n有熔断：上游调用 {b.calls} 次，快速失败 {b.fast_fail} 次，成功 {b.success} 次，"
      f"调用浪费率 {1 - b.success / max(1, b.calls):.0%}")
print(f"无熔断：上游调用 40 次，成功 {sum(1 for i in range(40) if healthy_at(i*0.1))} 次，"
      f"失败 {sum(1 for i in range(40) if not healthy_at(i*0.1))} 次（全部打在下游身上）")

recovered = next((t for t, s, _ in b.log if s == "closed" and t > 2.6), None)
print(f"恢复时间：下游 2.6s 恢复，熔断器 {recovered:.1f}s 回到 closed，"
      f"额外延迟约 {recovered - 2.6:.1f}s")

print("\n读法：熔断在故障期把 6 次调用变成 0 次上游调用，代价是恢复时多等一个探针周期；")
print("      open 窗口太短会反复打下游（抖动），太长会让恢复变慢——它是个可用性旋钮。")
print("结论：熔断阈值按「连续失败」而不是「失败率」更稳（低流量下失败率没有统计意义）；")
print("      half-open 只能放少量探针，且必须限制并发，否则恢复瞬间又是一次雪崩。")
