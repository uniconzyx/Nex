# title: 手写 JSON Schema 校验器：类型对了，语义仍可能错
# 支持 type/required/properties/enum/min/max/minLength/maxLength/items/additionalProperties。
# 输出每个 payload 的第一条错误路径；重点演示 bool 是 int 的子类这个坑。
SCHEMA = {
    "type": "object",
    "required": ["name", "priority", "tags"],
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 20},
        "priority": {"type": "integer", "enum": [1, 2, 3]},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "score": {"type": "number", "minimum": 0, "maximum": 1},
        "meta": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"owner": {"type": "string"}},
        },
    },
}

TYPE_MAP = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}

def check(value, schema, path="$"):
    t = schema.get("type")
    if t:
        py = TYPE_MAP[t]
        if t == "integer" and isinstance(value, bool):
            return f"{path}: 期望 integer，实际 bool（bool 是 int 的子类，必须显式拒绝）"
        if t == "number" and isinstance(value, bool):
            return f"{path}: 期望 number，实际 bool"
        if not isinstance(value, py):
            return f"{path}: 期望 {t}，实际 {type(value).__name__}"
    if "enum" in schema and value not in schema["enum"]:
        return f"{path}: {value!r} 不在枚举 {schema['enum']}"
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return f"{path}: 长度 {len(value)} < minLength {schema['minLength']}"
        if len(value) > schema.get("maxLength", 10**9):
            return f"{path}: 长度 {len(value)} > maxLength {schema['maxLength']}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            return f"{path}: {value} < minimum {schema['minimum']}"
        if "maximum" in schema and value > schema["maximum"]:
            return f"{path}: {value} > maximum {schema['maximum']}"
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", 10**9):
            return f"{path}: 元素数 {len(value)} > maxItems {schema['maxItems']}"
        for i, item in enumerate(value):
            err = check(item, schema.get("items", {}), f"{path}[{i}]")
            if err:
                return err
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                return f"{path}: 缺少必填字段 {k}"
        props = schema.get("properties", {})
        for k, v in value.items():
            if k not in props:
                if schema.get("additionalProperties") is False:
                    return f"{path}.{k}: 不允许的额外字段"
                continue
            err = check(v, props[k], f"{path}.{k}")
            if err:
                return err
    return None

payloads = [
    ("合法", {"name": "告警分级", "priority": 2, "tags": ["ops"], "score": 0.8}),
    ("缺必填", {"name": "告警分级", "tags": ["ops"]}),
    ("优先级越界", {"name": "告警分级", "priority": 5, "tags": ["ops"]}),
    ("bool 冒充 int", {"name": "告警分级", "priority": True, "tags": ["ops"]}),
    ("数组元素类型错", {"name": "告警分级", "priority": 1, "tags": ["ops", 3]}),
    ("空字符串", {"name": "", "priority": 1, "tags": ["ops"]}),
    ("额外字段", {"name": "告警分级", "priority": 1, "tags": ["ops"], "debug": 1}),
    ("嵌套字段错", {"name": "告警分级", "priority": 1, "tags": ["ops"], "meta": {"owner": 7}}),
    ("分数越界", {"name": "告警分级", "priority": 1, "tags": ["ops"], "score": 1.2}),
]

print("=" * 84)
print("表 1  9 个 payload 的校验结果")
print("=" * 84)
ok = 0
for name, p in payloads:
    err = check(p, SCHEMA)
    ok += err is None
    print(f"{name:<14}{'PASS' if err is None else 'FAIL':<6}{'' if err is None else err}")
print(f"\n通过 {ok}/{len(payloads)}。")

print("\n" + "=" * 84)
print("表 2  校验器抓不到的东西（语义层）")
print("=" * 84)
semantic = [
    ("priority=2 但描述是 P0", "枚举合法，语义冲突"),
    ("tags 里是『其他』但没填说明", "结构合法，业务规则不满足"),
    ("score=0.99 但没有任何证据字段", "数值合法，无法溯源"),
]
for case, why in semantic:
    print(f"  {case:<28} → {why}")
print("\n结论：Schema 只能保证「形状」，保证不了「意义」；bool 冒充 int 这类坑必须自己写。")
print("读法：解析失败先分三层——语法（不是 JSON）、结构（Schema 不过）、语义（业务规则不过）；")
print("      前两层用校验器挡，第三层必须用规则/抽样复核，不能指望模型自觉。")
