# title: 工具调用的幂等键与重复调用抑制：重试为什么不能变成重复下单
# 本地模拟：脚本化 Agent 重试序列 + 带幂等键的副作用工具，不调用真实 API。
import hashlib
import json

# ---------- 1) 副作用工具：send_email，带全局幂等键登记簿 ----------
class SideEffectTool:
    """模拟有副作用的工具（发邮件/下单/写库）。同一个 idem_key 只真执行一次。"""

    def __init__(self):
        self.executed = {}        # idem_key -> 首次执行结果（回放缓存）
        self.exec_count = 0       # 真实副作用次数（= 邮件真的发出去的次数）
        self.suppressed = 0       # 被抑制的重复次数

    def call(self, idem_key, **payload):
        if idem_key in self.executed:
            self.suppressed += 1
            return {"ok": True, "replayed": True, "data": self.executed[idem_key]}
        result = {"to": payload["to"], "subject": payload["subject"], "status": "SENT"}
        self.executed[idem_key] = result
        self.exec_count += 1
        return {"ok": True, "replayed": False, "data": result}


def idem_key(tool, args, drop=("nonce", "ts")):
    """幂等键 = 工具名 + 归一化参数的哈希。
    归一化：剔除 nonce/时间戳等每次调用都不同的字段，按键排序保证顺序无关。"""
    canon = {k: v for k, v in sorted(args.items()) if k not in drop}
    blob = tool + "|" + json.dumps(canon, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


mailer = SideEffectTool()

# ---------- 2) 模拟一个「失败重试」的 Agent 轨迹 ----------
# 场景：agent 要给客户发告警邮件。第 1 次发成功但响应超时（客户端没收到 ack），
# agent 按重试策略重发 3 次；其中 1 次带了 nonce，1 次参数 genuinely 不同（不同收件人）。
trace = [
    ("attempt-1 首次发送",     {"to": "ops@corp.com", "subject": "磁盘告警", "body": "/data 使用率 91%"}),
    ("attempt-2 超时重试",     {"to": "ops@corp.com", "subject": "磁盘告警", "body": "/data 使用率 91%"}),
    ("attempt-3 又超时重试",   {"to": "ops@corp.com", "subject": "磁盘告警", "body": "/data 使用率 91%"}),
    ("attempt-4 带 nonce 重试", {"to": "ops@corp.com", "subject": "磁盘告警", "body": "/data 使用率 91%",
                               "nonce": "r4"}),
    ("attempt-5 换收件人",     {"to": "boss@corp.com", "subject": "磁盘告警", "body": "/data 使用率 91%"}),
]

def dw(s):
    """终端显示宽度：中文等宽字符按 2 列计。"""
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


print(f"{'调用':<20}{'幂等键':<14}{'结果':<10}{'真实副作用数':>12}{'被抑制':>8}")
for name, args in trace:
    key = idem_key("send_email", args)
    r = mailer.call(key, **args)
    print(f"{pad(name, 20)}{key:<14}{'回放' if r['replayed'] else '新执行':<10}"
          f"{mailer.exec_count:>12}{mailer.suppressed:>8}")

# ---------- 3) 反证：没有幂等键会怎样 ----------
naive_sent = 0
for name, args in trace:
    naive_sent += 1                      # 每次都真发
print(f"\n反证：无幂等键时 5 次调用 = {naive_sent} 封邮件（客户收 4 封重复告警）")
print(f"有幂等键时真实副作用 = {mailer.exec_count} 次（同收件人同内容只发 1 次；换收件人是新意图）")

assert mailer.exec_count == 2          # ops 一次 + boss 一次
assert mailer.suppressed == 3          # attempt-2/3/4 被抑制
assert idem_key("send_email", {"a": 1, "b": 2}) == idem_key("send_email", {"b": 2, "a": 1})  # 顺序无关
assert idem_key("send_email", {"a": 1, "nonce": "x"}) == idem_key("send_email", {"a": 1, "nonce": "y"})

print("\n结论：重试 + 副作用工具 = 重复事故，幂等键是唯一的结构性防线，")
print("读法：1. 幂等键 = 工具名 + 归一化参数哈希，nonce/时间戳类字段必须剔除，否则键永远不同、抑制失效；2. 客户端超时 ≠ 服务端未执行，这是重试风暴的根源——ack 丢失时重发是必然动作，幂等由服务端/工具层保证；3. 抑制时返回首次结果（replayed=True），调用方无感；4. 「换收件人」参数 genuinely 不同，必须放行——幂等抑制的是重复，不是新意图；5. 真实系统里键还要带 TTL 与租约，避免无限回放缓存。")
