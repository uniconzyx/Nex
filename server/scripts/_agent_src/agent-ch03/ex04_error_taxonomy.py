# title: 错误码分类与降级决策表：把 if-else 变成可审计的策略表
# 本地模拟：不联网，只演示「同一套错误语义 → 统一的重试/降级动作」。
# 核心判据：可重试 != 值得重试。401 重试 3 次只是把 300ms 的故障拖成 3 秒。

RULES = {
    # 错误码: (类别, 可重试, 最大次数, 退避, 用户侧动作)
    "invalid_api_key":   ("鉴权", False, 0, 0.0, "fail_fast"),
    "permission_denied": ("鉴权", False, 0, 0.0, "fail_fast"),
    "model_not_found":   ("配置", False, 0, 0.0, "fail_fast"),
    "invalid_request":   ("入参", False, 0, 0.0, "fix_request"),
    "content_filter":    ("策略", False, 0, 0.0, "refuse"),
    "context_too_long":  ("入参", False, 0, 0.0, "truncate"),
    "insufficient_quota":("配额", False, 0, 0.0, "fail_fast"),
    "rate_limited":      ("限流", True, 4, 1.0, "backoff"),
    "overloaded":        ("过载", True, 3, 2.0, "backoff_or_fallback"),
    "server_error":      ("服务端", True, 3, 2.0, "retry"),
    "bad_gateway":       ("网关", True, 2, 1.0, "retry"),
    "timeout":           ("超时", True, 2, 0.5, "retry_or_degrade"),
}


def decide(code: str, attempt: int):
    cls, retryable, max_n, backoff, action = RULES.get(code, ("未知", False, 0, 0.0, "fail_fast"))
    if not retryable:
        return cls, False, action
    if attempt >= max_n:
        return cls, False, "exhausted->fallback"
    return cls, True, f"sleep {backoff * 2 ** (attempt - 1):.1f}s then {action}"


print("决策表（错误码 → 类别 / 是否重试 / 动作），重试次数按指数增长\n")
print(f"{'错误码':<20}{'类别':<6}{'重试':<4}{'尝试1的动作':<34}{'耗尽后的用户侧'}")
for code in RULES:
    cls, yes, act = decide(code, 1)
    _, _, _, _, fallback = RULES[code]
    print(f"{code:<20}{cls:<6}{'是' if yes else '否':<4}{act:<34}{fallback}")

print("\n模拟 24 个请求（错误码按固定序列抽样，不是随机猜测）：")
sequence = ["rate_limited", "timeout", "server_error", "invalid_request",
            "rate_limited", "context_too_long", "invalid_api_key", "overloaded",
            "bad_gateway", "content_filter", "server_error", "rate_limited"] * 2
counts = {}
for i, code in enumerate(sequence):
    attempt = 1 + i % 3
    cls, retry, action = decide(code, attempt)
    key = action.split(" then ")[-1].split("->")[-1] if retry else action
    counts[key] = counts.get(key, 0) + 1

print(f"{'最终动作':<26}{'请求数':>6}")
for k in sorted(counts):
    print(f"{k:<26}{counts[k]:>6}")

retryable = sum(1 for c in RULES.values() if c[1])
print(f"\n共 {len(RULES)} 类错误，其中可重试 {retryable} 类（{retryable/len(RULES):.0%}）。")
print("读法：鉴权/配置/入参错误必须快速失败——它们重试一万次也不会变对；")
print("      限流看 Retry-After，过载看熔断器，超时只在幂等请求上重试。")
print("结论：分类的价值在于「把不可重试错误挡在重试循环之外」，这比调退避参数省得多。")
