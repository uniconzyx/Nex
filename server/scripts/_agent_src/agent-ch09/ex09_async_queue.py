# title: 异步任务队列与进度反馈：批量提交、回调、失败重试与汇总
import time


class TaskQueue:
    """纯标准库 FIFO 任务队列：提交 -> 处理 -> 进度回调 -> 结果汇总，支持失败重试。"""

    def __init__(self, milestones=(0.25, 0.5, 0.75, 1.0)):
        self.tasks = []
        self.results = {}
        self.milestones = milestones
        self.fired = []
        self.retried = 0

    def submit(self, tid, fn):
        self.tasks.append((tid, fn))

    def _process(self, tid, fn):
        try:
            return fn(), "ok"
        except Exception as e:  # noqa: BLE001 - 模拟失败注入需要兜底
            return None, f"fail:{type(e).__name__}"

    def run(self):
        total = len(self.tasks)
        done = 0
        pending = list(self.tasks)
        while pending:
            tid, fn = pending.pop(0)
            out, status = self._process(tid, fn)
            if status.startswith("fail") and self.retried < 2:  # 每任务最多重试一次
                self.retried += 1
                pending.append((tid, fn))
                continue
            self.results[tid] = (out, status)
            done += 1
            for m in self.milestones:
                if done / total >= m and m not in self.fired:
                    self.fired.append(m)
                    bar = "#" * int(m * 20)
                    print(f"  进度 {bar:<20} {done}/{total} ({m:.0%})")
        return self.results


def extract(payload):
    """模拟一次抽取任务：编号 3 与 7 第一次必失败（每个任务只失败一次）。"""
    tid, n = payload
    if tid in (3, 7) and tid not in extract.failed_once:
        extract.failed_once.add(tid)
        raise RuntimeError("simulated timeout")
    return f"fields={n}"


extract.failed_once = set()

q = TaskQueue()
for i in range(1, 21):
    q.submit(i, lambda i=i: extract((i, 5)))
print("== 批量提交 20 个抽取任务（含 2 个首次失败后重试） ==")
t0 = time.monotonic()
results = q.run()
dt = time.monotonic() - t0

ok = [t for t, (o, s) in results.items() if s == "ok"]
bad = [t for t, (o, s) in results.items() if s != "ok"]
print(f"\n完成 {len(results)}/20，成功 {len(ok)}，失败 {len(bad)}")
print(f"重试次数 = {q.retried}（期望 2），失败任务列表 = {bad}（期望 []）")
assert len(results) == 20 and len(bad) == 0 and q.retried == 2
assert q.fired == [0.25, 0.5, 0.75, 1.0], "进度回调应单调触发"
print(f"进度回调触发点 = {[f'{m:.0%}' for m in q.fired]}（顺序单调）")
print(f"结果样例: task1 -> {results[1][0]}, task20 -> {results[20][0]}")

print("\n结论：队列把「批量 50 张图」变成可观测的进度与可重试的失败，用户侧拿到的是百分比而不是转圈，")
print("读法：1. 进度回调按里程碑（25/50/75/100%）触发，顺序必须单调；2. 失败重试要有上限，否则坏任务会饿死队列；3. 汇总输出要与各任务落盘结果一一对应，否则对账困难；4. 本示例为纯标准库模拟，未使用任何消息中间件。")
