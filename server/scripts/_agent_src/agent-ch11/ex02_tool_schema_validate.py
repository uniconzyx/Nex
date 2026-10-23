# title: 工具 schema 校验与参数修复：把模型的「自由发挥」拦在执行前
# 本地模拟：脚本化的「模型输出」+ JSON-schema-lite 校验器，不调用真实 LLM/API。
import json

# ---------- 1) 三个工具的 schema（lite：类型/必填/枚举/范围） ----------
SCHEMAS = {
    "search": {
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    "calc": {
        "properties": {"expr": {"type": "string", "max_len": 64,
                                "charset": "0123456789+-*/(). "}},
        "required": ["expr"],
    },
    "send_email": {
        "properties": {
            "to": {"type": "string", "pattern": "@"},
            "subject": {"type": "string", "max_len": 40},
            "body": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            "retries": {"type": "integer", "min": 0, "max": 5},
        },
        "required": ["to", "subject", "body", "priority"],
    },
}

# ---------- 2) 模拟「模型」产生的 8 次工具调用（含常见错误形态） ----------
RAW_CALLS = [
    {"tool": "calc", "args": {"expr": "1,234.50 * 2"}},                      # 千分位逗号
    {"tool": "send_email", "args": {"to": "ops@corp.com", "subject": "告警",
                                    "priority": "urgent"}},                 # 缺 body + 枚举越界
    {"tool": "send_email", "args": {"to": "boss@corp.com", "subject": "周报",
                                    "body": "详见附件", "priority": "high",
                                    "retries": 10}},                        # 范围越界
    {"tool": "search", "args": {"query": 2024}},                             # 类型错误
    {"tool": "calc", "args": {"expr": "8450 / 0"}},                          # schema 拦不住的语义错误
    {"tool": "lookup", "args": {"key": "timeout"}},                          # 工具不存在 + 缺参数
    {"tool": "send_email", "args": {"to": "no-at-sign", "subject": "x" * 50,
                                    "body": "b", "priority": "low"}},       # pattern + 长度越界
    {"tool": "search", "args": {"query": "sales_q3"}},                       # 完全合法
]

# ---------- 3) 校验器：返回错误列表 ----------
def validate(call):
    errs = []
    tool, args = call["tool"], call["args"]
    if tool not in SCHEMAS:
        return [f"未知工具 {tool!r}（工具白名单外，直接拒发）"]
    spec = SCHEMAS[tool]
    for f in spec["required"]:
        if f not in args:
            errs.append(f"缺必填字段 {f!r}")
    for f, v in args.items():
        if f not in spec["properties"]:
            errs.append(f"未知字段 {f!r}")
            continue
        rule = spec["properties"][f]
        t = rule["type"]
        if t == "string" and not isinstance(v, str):
            errs.append(f"{f} 应为 string，实为 {type(v).__name__}")
        elif t == "integer" and not isinstance(v, int):
            errs.append(f"{f} 应为 integer，实为 {type(v).__name__}")
        if t == "string" and isinstance(v, str):
            if "max_len" in rule and len(v) > rule["max_len"]:
                errs.append(f"{f} 超长 {len(v)}>{rule['max_len']}")
            if "charset" in rule and not set(v) <= set(rule["charset"]):
                bad = sorted(set(v) - set(rule["charset"]))
                errs.append(f"{f} 含白名单外字符 {bad}")
            if "pattern" in rule and rule["pattern"] not in v:
                errs.append(f"{f} 不含 {rule['pattern']!r}")
        if "enum" in rule and v not in rule["enum"]:
            errs.append(f"{f}={v!r} 不在枚举 {rule['enum']}")
        if t == "integer" and isinstance(v, int):
            if "min" in rule and v < rule["min"]:
                errs.append(f"{f}={v} < min {rule['min']}")
            if "max" in rule and v > rule["max"]:
                errs.append(f"{f}={v} > max {rule['max']}")
    return errs

# ---------- 4) 修复器：只做「语义等价」的修复，不可猜的一律拒发 ----------
def repair(call):
    """返回 (修复后 call, 修复动作列表, 是否仍拒发)。"""
    tool, args = call["tool"], dict(call["args"])
    fixes, reject = [], False
    if tool not in SCHEMAS:
        return call, [], True
    spec = SCHEMAS[tool]
    for f in spec["required"]:                      # 必填缺失不可猜 → 拒发
        if f not in args:
            fixes.append(f"缺 {f} 不可猜→拒发"); reject = True
    for f in list(args):
        if f not in spec["properties"]:
            fixes.append(f"删除未知字段 {f}"); args.pop(f); continue
        rule = spec["properties"][f]
        v = args[f]
        if rule["type"] == "string" and isinstance(v, (int, float)):
            args[f] = str(v); fixes.append(f"{f}: 数字转字符串")
        elif rule["type"] == "integer" and isinstance(v, str) and v.isdigit():
            args[f] = int(v); fixes.append(f"{f}: 数字串转 int")
        v = args[f]
        if rule["type"] == "string" and isinstance(v, str):
            if "charset" in rule and not set(v) <= set(rule["charset"]):
                args[f] = "".join(c for c in v if c in rule["charset"])
                fixes.append(f"{f}: 剔除白名单外字符")
            if "max_len" in rule and len(v) > rule["max_len"]:
                args[f] = v[: rule["max_len"]]; fixes.append(f"{f}: 截断到 {rule['max_len']}")
            if "pattern" in rule and rule["pattern"] not in v:
                fixes.append(f"{f} 缺 {rule['pattern']!r}，不可猜→拒发"); reject = True
        if "enum" in rule and v not in rule["enum"]:
            args[f] = rule["enum"][-1]; fixes.append(f"{f}: {v!r}→枚举最近值 {rule['enum'][-1]!r}")
        if rule["type"] == "integer" and isinstance(v, int):
            if "min" in rule and v < rule["min"]:
                args[f] = rule["min"]; fixes.append(f"{f}: 提升到 min")
            if "max" in rule and v > rule["max"]:
                args[f] = rule["max"]; fixes.append(f"{f}: 截到 max {rule['max']}")
    return {"tool": tool, "args": args}, fixes, reject

# ---------- 5) 跑 8 个调用：原始校验 → 修复 → 复校验 ----------
n_pass, n_fixed, n_reject = 0, 0, 0
print(f"{'#':>2} {'工具':<10}{'原始错误数':>10}  {'处置':<6} 修复动作")
for i, call in enumerate(RAW_CALLS, 1):
    errs0 = validate(call)
    if not errs0:
        n_pass += 1
        print(f"{i:>2} {call['tool']:<10}{0:>10}  {'放行':<6} -")
        continue
    fixed, fixes, reject = repair(call)
    errs1 = validate(fixed)
    if errs1:
        n_reject += 1
        print(f"{i:>2} {call['tool']:<10}{len(errs0):>10}  {'拒发':<6} {'; '.join(errs1)}")
    else:
        n_fixed += 1
        print(f"{i:>2} {call['tool']:<10}{len(errs0):>10}  {'修复':<6} {'; '.join(fixes) if fixes else '-'}")

# 语义错误专项：schema 全过但执行期爆炸
call_div0 = {"tool": "calc", "args": {"expr": "8450 / 0"}}
assert validate(call_div0) == []
print(f"\n专项：calc(expr='8450 / 0') schema 校验 {len(validate(call_div0))} 错误——"
      "除零是语义错误，schema 拦不住，只能靠执行期异常 + 重试策略兜底。")

print(f"\n统计：一次放行 {n_pass} / 修复后放行 {n_fixed} / 拒发 {n_reject}")
assert (n_pass, n_fixed, n_reject) == (2, 3, 3)

print("\n结论：schema 校验是工具调用的第一道闸，但只能拦「形状」错误，拦不住语义错误，")
print("读法：1. 错误分三类——可修复（千分位/枚举越界/范围越界，做语义等价变换）、不可猜（缺必填/缺 pattern，拒发让模型重试）、schema 盲区（除零/权限，靠执行期与沙箱）；2. 修复必须语义等价，宁可拒发也不要「猜一个值」硬执行；3. 拒发时要把错误信息回给模型重试，这是 ReAct 的 observation（见 ex01）；4. 本示例的 schema 是 lapse 版 JSON Schema，真实可用 jsonschema 库或 MCP server 自带的 inputSchema。")
