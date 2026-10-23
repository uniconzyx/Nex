# title: 容器健康检查与灰度发布：探针抖动保护、就绪摘除与金丝雀自动回滚
# 纯标准库实现：liveness/readiness 两个探针的状态机（含 flap 保护）与灰度放量/回滚模拟。


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


class LivenessProbe:
    """存活探针：连续 K 次失败才重启——单点抖动不误杀（flap 保护）。"""

    def __init__(self, k=3):
        self.k = k
        self.streak = 0
        self.restarts = 0

    def tick(self, alive):
        if alive:
            self.streak = 0
            return "OK"
        self.streak += 1
        if self.streak >= self.k:
            self.restarts += 1
            self.streak = 0
            return f"RESTART(连续{self.k}次失败)"
        return f"FAIL({self.streak}/{self.k})"


class ReadinessGate:
    """就绪探针：查真依赖（模型加载+下游连通）；失败 -> 摘除流量，不重启。"""

    def __init__(self):
        self.ready = True
        self.detached_min = 0

    def tick(self, deps_ok):
        if deps_ok and not self.ready:
            self.ready = True
            return "REATTACH(依赖恢复,重新接流量)"
        if not deps_ok:
            if self.ready:
                self.ready = False
                return "DETACH(摘除流量,不重启)"
            self.detached_min += 1
            return "DETACHED(持续不可用)"
        return "READY"


print("== 1) liveness 探针：连续 3 次失败才重启（ flap 保护） ==")
# 探测序列：True=存活。含两组考验：抖动+双连失败后恢复 vs 持续死亡
seq = [True, False, True, False, True, True, False, False, True, True, False, False, False, False]
lv = LivenessProbe(k=3)
print("  " + pad("探测", 6) + pad("结果", 8) + "动作")
for i, alive in enumerate(seq, 1):
    act = lv.tick(alive)
    print("  " + pad(f"#{i}", 6) + pad("存活" if alive else "失败", 8) + act)
print(f"  重启次数 = {lv.restarts}：间歇抖动（#2/#4/#7）与双连失败后恢复（#7-8）零误杀，持续死亡（#11-14）第 3 次拉闸")
print("  若 K=2：#8 就会误杀那次恢复中的抖动——阈值 3 是误杀/漏杀的折中（经验判断）")

print("\n== 2) readiness 探针：查真依赖，失败摘除而不重启 ==")
rg = ReadinessGate()
deps = [True, True, False, False, True, True, True]
print("  " + pad("探测", 6) + pad("依赖", 8) + "动作")
for i, ok in enumerate(deps, 1):
    act = rg.tick(ok)
    print("  " + pad(f"#{i}", 6) + pad("连通" if ok else "断开", 8) + act)
print(f"  摘除期间不计重启；进程活着但依赖挂 -> 流量被摘除，用户看到的是「暂不可用」而非 500")
print("  判据：liveness 查「进程要不要重建」，readiness 查「流量要不要进」——两探针职责不同")

print("\n== 3) 金丝雀发布：按错误率自动放量/回滚 ==")
# 版本错误率（每次探测的模拟值）：v2.0 有缺陷（错误率 ~4x 基线），v2.1 修复
stages = [
    ("v1.0 100%", 0.008, 100, "稳定运行"),
    ("v2.0 5%", 0.041, 5, "错误率 5.1x 基线 -> 触发回滚条件"),
    ("回滚 v1.0 100%", 0.008, 100, "金丝雀熔断,全量回退"),
    ("v2.1 5%", 0.009, 5, "错误率回落,继续观察"),
    ("v2.1 25%", 0.010, 25, "稳定,扩大灰度"),
    ("v2.1 100%", 0.009, 100, "全量上线"),
]
BASELINE_ERR = 0.008
ROLLBACK_FACTOR = 3.0
print("  " + pad("阶段", 16) + pad("错误率", 9) + pad("流量占比", 9) + "决策")
for name, err, share, note in stages:
    decision = "回滚!" if err > BASELINE_ERR * ROLLBACK_FACTOR else ("放量" if share < 100 else "保持")
    print("  " + pad(name, 16) + pad(f"{err:.1%}", 9) + pad(f"{share}%", 9)
          + f"{decision}  {note}")
print("  回滚判据：金丝雀错误率 > 基线 3 倍且样本量足够（经验阈值，按业务错误成本标定）")
print("  放量阶梯 5% -> 25% -> 100%：每级观察窗口内指标不劣化才进下一级")

print("\n结论：健康检查与灰度是把「演示时祈祷」变成「故障自愈」的两个最小机制；")
print("读法：1. liveness 连续 K=3 次失败才重启，防 flap 误杀；readiness 查真依赖，失败摘除不重启；2. 灰度按 5/25/100 阶梯放量，错误率超基线 3 倍自动回滚，回滚要能一键全量退；3. 探针查的内容比探针本身重要：查 PID 的 readiness 会在「进程活着服务不可用」时把流量送进黑洞；4. 本示例为本地状态机模拟，真实实现见 Docker HEALTHCHECK 与 K8s probe/rollout 文档。")
