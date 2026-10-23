# title: SSE 流式解析器：JSON 会被网络切成两半，按包解析必然失败
# 本地模拟 transport：把一段真实形状的 SSE 文本切成不等长 chunk 喂给解析器。
# 对照「每个 chunk 单独 json.loads」的朴素写法，量化跨包失败率。

import json

STREAM = (
    ": keep-alive\n\n"
    "event: delta\n"
    'data: {"id":"c1","choices":[{"delta":{"content":"你好"}}]}\n\n'
    'data: {"id":"c1","choices":[{"delta":{"content":"，世界"}}]}\n\n'
    "event: delta\n"
    'data: {"id":"c1",\n'
    'data: "choices":[{"delta":{"content":"跨包"}}]}\n\n'
    'data: {"id":"c1","choices":[],"usage":{"prompt_tokens":18,"completion_tokens":6}}\n\n'
    "data: [DONE]\n\n"
)

CHUNK_SIZES = [7, 11, 4, 13, 9, 3, 17, 5]


def chunks(text: str):
    out, i, k = [], 0, 0
    while i < len(text):
        n = CHUNK_SIZES[k % len(CHUNK_SIZES)]
        out.append(text[i:i + n])
        i += n
        k += 1
    return out


def parse_stream(parts):
    """标准 SSE 状态机：行缓冲 + 事件缓冲，data 多行用 \\n 连接。"""
    buf, data_lines = "", []
    events, done, bad = [], False, 0
    for chunk in parts:
        buf += chunk
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.rstrip("\r")
            if line == "":
                if data_lines:
                    payload = "\n".join(data_lines)
                    data_lines = []
                    if payload == "[DONE]":
                        done = True
                        continue
                    try:
                        events.append(json.loads(payload))
                    except json.JSONDecodeError:
                        bad += 1
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip(" "))
    return events, done, bad


def naive(parts):
    """错误示范：把每个 chunk 当成完整事件解析。"""
    fails, oks = 0, 0
    for chunk in parts:
        if "data:" not in chunk:
            continue
        body = chunk.split("data:", 1)[1].strip()
        if not body or body == "[DONE]":
            continue
        try:
            json.loads(body)
            oks += 1
        except json.JSONDecodeError:
            fails += 1
    return oks, fails


parts = chunks(STREAM)
print(f"模拟流：SSE 文本 {len(STREAM)} 字符，被切成 {len(parts)} 个 chunk（尺寸循环 {CHUNK_SIZES[:4]}…）")
print("（这是模拟 transport；真实实现还要处理 CRLF、重连 Last-Event-ID、gzip 分块）\n")

events, done, bad = parse_stream(parts)
text = "".join(e["choices"][0]["delta"]["content"] for e in events if e.get("choices"))
usage = next((e["usage"] for e in events if e.get("usage")), {})

print("[状态机解析]")
print(f"  完整事件 {len(events)} 个，拼接文本 = {text!r}")
print(f"  解析失败 {bad} 个，收到 [DONE] = {done}")
print(f"  usage = prompt {usage.get('prompt_tokens')} / completion {usage.get('completion_tokens')}")

n_ok, n_bad = naive(parts)
print("\n[逐 chunk 解析（反例）]")
print(f"  把 chunk 当完整 JSON：成功 {n_ok} 个，失败 {n_bad} 个，"
      f"失败率 {n_bad / max(1, n_ok + n_bad):.0%}")
print("  失败原因不是 JSON 写错了，而是 7~17 字符的包边界落在字符串/对象中间。")

print("\n读法：流式解析的第一原则是「按行缓冲，不按包缓冲」；")
print("      第二原则是 data 可多行，必须用 \\n 拼接后再 json.loads；")
print("      第三原则是 usage 常出现在最后一个空 choices 事件里，别只读 delta。")
print("结论：跨包不是异常而是常态，任何按 chunk 解析 JSON 的实现上线后都会随机丢字。")
