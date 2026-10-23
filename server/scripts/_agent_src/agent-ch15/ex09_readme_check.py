# title: README 完整性自检：四件套标记、陌生人 10 分钟复现测试与缺口清单
# 纯标准库实现：按标记词检测 README 必备节，加权评分 + 复现步骤计数与缺口清单。


def dw(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)


def pad(s, w):
    return s + " " * max(1, w - dw(s))


# 必备节 -> (检测标记词列表[任一命中即存在], 权重, 缺了会发生什么)
CHECKLIST = [
    ("一键复现步骤", (["docker compose up", "一条命令", "快速开始"], 30, "观众跑不起来，demo 不存在")),
    ("架构图", (["架构图", "数据流", "```mermaid"], 20, "答辩时讲不清数据怎么流")),
    ("已知限制", (["已知限制", "不做", "限制"], 20, "用户撞到边界当成 bug 投诉")),
    ("演示入口", (["演示", "demo", "视频"], 15, "观众找不到看什么")),
    ("环境要求", (["环境要求", "系统要求", "依赖"], 10, "复现失败归因不到环境")),
    ("常见失败排法", (["常见失败", "排错", "FAQ", "troubleshoot"], 5, "演示日现场卡住无人救场")),
]

README_GOOD = """# 周报助手 Agent
## 快速开始
git clone <repo> && cd weekly-report-agent
docker compose up  # 一条命令启动，30 秒后 http://localhost:8000 出现 demo 页面即成功
## 环境要求
Python 3.13 / Docker 24+ / 4GB 内存
## 架构
架构图见 docs/arch.mermaid：上传 -> 归类 -> 生成 -> 标注，数据流与外部依赖齐全
## 演示
演示入口：demo 页面 + 3 分钟演示视频（video/demo.mp4）
## 已知限制
不做多语言；知识库上限 100 篇；单次输入 <5000 字
## 常见失败
FAQ：端口占用改 APP_PORT；密钥缺失见 .env.example
"""

README_BAD = """# 周报助手 Agent
一个能自动写周报的 Agent 项目。
## 使用方法
python app.py
（更多功能开发中）
"""


def check_readme(text):
    """按标记词检测必备节，返回 (得分, 命中表, 缺口清单)。"""
    hits, missing = [], []
    score = 0
    for name, (markers, weight, cost) in CHECKLIST:
        ok = any(m in text for m in markers)
        hits.append((name, ok, weight, cost))
        score += weight if ok else 0
    missing = [h[0] for h in hits if not h[1]]
    return score, hits, missing


def stranger_test(text):
    """陌生人复现测试：数「快速开始」里的命令步数，按每步 2 分钟估复现耗时。"""
    steps = 0
    for kw in ("git clone", "docker compose up", "pip install", "python app.py", "export "):
        steps += text.count(kw)
    return steps, steps * 2  # 每步按 2 分钟计（含排错）


for label, text in [("README-A（自称写完）", README_BAD), ("README-B（按清单写）", README_GOOD)]:
    score, hits, missing = check_readme(text)
    steps, minutes = stranger_test(text)
    verdict = "可交付" if score >= 90 and minutes <= 10 else "需补写"
    print(f"== {label}: {score}/100 分，复现约 {minutes} 分钟（{steps} 步），判定：{verdict} ==")
    print("  " + pad("必备节", 16) + pad("权重", 6) + pad("命中", 6) + "缺了的代价")
    for name, ok, weight, cost in hits:
        print("  " + pad(name, 16) + pad(str(weight), 6) + pad("是" if ok else "否", 6) + cost)
    if missing:
        print(f"  缺口清单: {missing}")
    print()

print("== 判定口径 ==")
print("  1. 得分 >=90 且陌生人复现 <=10 分钟 -> 可交付；缺「一键复现」一票否决（权重 30 且是观众第一眼）")
print("  2. README-A 反例：只有标题和一句简介，「python app.py」不算复现步骤（没讲前置条件与验证方式）")
print("  3. 复现步骤要写验证方式：『看到什么算成功』——没有验证语的步骤等于没写")
print("  4. 「已知限制」是最被低估的一节：它把用户的意外变成你的预期管理")

print("\n结论：README 的第一读者不是维护者，是 10 分钟后要跑起来的陌生人——自检表按这个视角写；")
print("读法：1. 六节必备（复现/架构/限制/演示/环境/排错）按权重打分，缺一键复现一票否决；2. 复现步骤要含前置条件与验证方式，『看到什么算成功』；3. 陌生人在干净环境实测一次，比自查十遍都可靠；4. 本示例用标记词模拟检测，真实自检就是拿这份清单过一遍自己的 README。")
