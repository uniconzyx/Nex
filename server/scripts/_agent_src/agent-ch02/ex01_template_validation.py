# title: 提示模板渲染与变量校验：把 prompt 当成有类型的接口
# 严格模式：占位符必须在 schema 里、必填变量不能缺、类型/长度/控制字符都要查。
# 同时对比「单次替换」与「顺序 replace」——后者会把用户值里的 {{...}} 二次展开。
import re

TPL = """你是{{role}}。
任务：{{task}}
约束：
{% for c in constraints %}- {{c}}
{% endfor %}示例数：{{n_examples}}"""

PLACEHOLDER = re.compile(r"{{\s*([A-Za-z_]\w*)\s*}}")
SCHEMA = {
    "role": {"type": str, "max_len": 40, "required": True},
    "task": {"type": str, "max_len": 120, "required": True},
    "constraints": {"type": list, "max_items": 4, "required": True},
    "n_examples": {"type": int, "min": 0, "max": 8, "required": True},
}

def validate(name, value, spec):
    if not isinstance(value, spec["type"]) or isinstance(value, bool) and spec["type"] is int:
        return f"{name}: 类型应为 {spec['type'].__name__}，实际 {type(value).__name__}"
    if spec["type"] is str and len(value) > spec["max_len"]:
        return f"{name}: 长度 {len(value)} 超过 {spec['max_len']}"
    if spec["type"] is list and len(value) > spec["max_items"]:
        return f"{name}: 元素 {len(value)} 超过 {spec['max_items']}"
    if spec["type"] is int and not (spec["min"] <= value <= spec["max"]):
        return f"{name}: 取值 {value} 不在 [{spec['min']},{spec['max']}]"
    if spec["type"] is str and any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        return f"{name}: 含控制字符"
    return None

def render(tpl, values, schema):
    used = set(PLACEHOLDER.findall(tpl))
    used.discard("c")            # c 是循环内绑定的局部变量，不是外部参数
    errs = [f"模板引用了未声明变量 {n}" for n in sorted(used - set(schema))]
    errs += [f"缺少必填变量 {n}" for n in schema if schema[n]["required"] and n not in values]
    for n, v in values.items():
        if n not in schema:
            errs.append(f"传入未声明变量 {n}")
            continue
        e = validate(n, v, schema[n])
        if e:
            errs.append(e)
    if errs:
        return None, errs
    # 先展开仅有的循环块，再单次扫描替换；re.sub 不会回头扫描替换进去的内容
    def _loop(m):
        body = m.group(1)
        return "".join(body.replace("{{c}}", str(c)) for c in values["constraints"])
    out = re.sub(r"{% for c in constraints %}(.*?){% endfor %}", _loop, tpl, flags=re.S)
    out = PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), out)
    return out, []

def naive_render(tpl, values):
    out = tpl
    for k, v in values.items():          # 顺序 replace：前一个值里的占位符会被后一个键展开
        out = out.replace("{{" + k + "}}", str(v))
    return out

cases = [
    ("正常", {"role": "运维助手", "task": "把告警归类到 5 个等级", "constraints": ["只输出等级", "不确定时输出 UNKNOWN"], "n_examples": 2}),
    ("缺字段", {"role": "运维助手", "constraints": ["只输出等级"], "n_examples": 2}),
    ("类型错", {"role": "运维助手", "task": "分类", "constraints": "只输出等级", "n_examples": 2}),
    ("超长", {"role": "运维助手", "task": "x" * 130, "constraints": ["a"], "n_examples": 2}),
    ("含注入占位符", {"role": "助手", "task": "复述用户输入：{{n_examples}}", "constraints": ["不要展开"], "n_examples": 3}),
]

print("=" * 70)
print("表 1  校验与渲染")
print("=" * 70)
for name, vals in cases:
    out, errs = render(TPL, vals, SCHEMA)
    status = "OK" if out else "ERR"
    print(f"{name:<12}{status:<5}{('；'.join(errs))[:60]}")

ok_vals = cases[0][1]
rendered, _ = render(TPL, ok_vals, SCHEMA)
print("\n渲染结果（前 6 行）：")
for line in rendered.splitlines()[:6]:
    print("  | " + line)

print("\n" + "=" * 70)
print("表 2  二次展开漏洞：用户值里带 {{...}} 时")
print("=" * 70)
inject = {"role": "助手", "task": "总结：{{n_examples}}", "constraints": ["a"], "n_examples": 3}
safe, _ = render(TPL, inject, SCHEMA)
naive = naive_render(TPL, inject)
print(f"  单次替换：任务行 = {[l for l in safe.splitlines() if l.startswith('任务')][0]}")
print(f"  顺序 replace：任务行 = {[l for l in naive.splitlines() if l.startswith('任务')][0]}")
safe_line = [l for l in safe.splitlines() if l.startswith("任务")][0]
naive_line = [l for l in naive.splitlines() if l.startswith("任务")][0]
print(f"  任务行残留占位符：单次替换 {len(PLACEHOLDER.findall(safe_line))} 个，顺序 replace {len(PLACEHOLDER.findall(naive_line))} 个")

print("\n结论：模板不是字符串拼接，是接口——类型、长度、必填、未声明变量都要在渲染前拦住；")
print("      而且必须单次替换，否则用户输入里的 {{var}} 会变成第二次模板求值。")
print("读法：把校验错误当作 4xx 返回给调用方，不要靠模型「自己理解缺了什么」。")
