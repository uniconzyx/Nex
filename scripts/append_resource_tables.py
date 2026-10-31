# -*- coding: utf-8 -*-
"""为 fs-ch10~15、ai-ch12~14 的 goals.md 追加三段资源表（GitHub/B站/论文书）。

资源段口径对齐 audit_sources.py：
  - GitHub 表：写全 https://github.com/owner/repo，Star 进单元格（RE_STAR_CELL 命中），并带 §x.y 锚点；
  - B 站表：写全 https://www.bilibili.com/video/BVxxx（RE_BV 命中），BV 已由 _fetch_bilibili_bv.py 核验可播；
  - 论文书表：真实文献 + §x.y 锚点；
  - 资源段从「## 本章 GitHub」起，§x.y 命中 section_hits -> ok_anchor。
同时把 books 写进 content/<subject>/_manifest.json 的 resources.books（满足 ok_books，非阻塞）。

用法：python scripts/append_resource_tables.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

# star 取自本会话 GitHub API 实取（部分沿用此前 ai-ch11 实取值）
DATA = {
    "fs-ch10": {
        "subject": "fullstack",
        "gh": [
            ("vuejs/core", 54801, "§1.1 Proxy · §1.6 心智模型", "响应式内核：读 `packages/reactivity/src` 的 `effect.ts` 与 `dep.ts`，依赖收集与触发正是 §1.1、§1.6 讲的那套"),
            ("vuejs/pinia", 14755, "§3.1 两种写法", "状态管理实现：读 `src/store.ts` 的 `defineStore`，options 与 setup 两套入口对应 §3.1"),
            ("vuejs/router", 4706, "§2.1 路由", "前端路由：历史模式与导航守卫，对应 §2.1 的路由边界"),
            ("vuejs/rfcs", 4926, "§1.3 ref.value · §2.1", "RFC 文本：ref 必须 .value、响应式边界的设计讨论，直接对应 §1.3、§2.1"),
        ],
        "bili": [
            ("BV1Zb4y1H7XY", "13.Vue 2.0和Vue3.0 响应式原理的区别", "程序员铁蛋儿", "28m17s", "§1.1 Proxy 与依赖收集"),
            ("BV1Dk4y127Ha", "【前端面试必备】Vue2与Vue3核心之『响应式原理』", "野sir的AI世界1", "220m39s", "§1.3 ref 必须 .value · §1.6 心智模型"),
        ],
        "papers": [
            ("霍春阳《Vue.js 设计与实现》第3章『响应式系统』—— 对应 §1.1、§1.6", "§1.1 · §1.6"),
            ("Vue 官方文档《Reactivity in Depth》—— 对应 §1 全章、§2 ref/reactive 边界", "§1 · §2"),
            ("TC39 `Proxy`/`Reflect` 规范与 Decorators 提案 —— 对应 §1.1 为什么是 Proxy", "§1.1"),
        ],
    },
    "fs-ch11": {
        "subject": "fullstack",
        "gh": [
            ("spring-projects/spring-boot", 81772, "§1 分层 · §3 校验", "脚手架与自动配置：读 `spring-boot-autoconfigure` 理解 starter 如何收口分层"),
            ("spring-projects/spring-framework", 60300, "§2 异常 · §3 校验", "核心容器与 AOP：读 `web` 模块 `@ControllerAdvice`、Jakarta Validation 集成，对应 §2、§3"),
            ("spring-projects/spring-security", 9653, "§2.4 不返堆栈", "安全与异常处理：认证失败响应结构，对应 §2.4 绝不要把堆栈返前端"),
            ("openjdk/jdk", 23477, "§3 校验", "Jakarta Validation 源自 Bean Validation（`java.validation`），对应 §3.1"),
        ],
        "bili": [
            ("BV1BZ4tzhEi5", "SpringBoot全局异常处理", "莲城的老李", "11m36s", "§2.1 @ControllerAdvice"),
            ("BV1924y1o7Sm", "springboot如何优雅地统一异常处理和信息返回", "源码人生", "38m37s", "§2.2 业务异常 vs 系统异常 · §2.3 错误码"),
        ],
        "papers": [
            ("Craig Walls《Spring in Action》第 4、6 章（Web、AOP）—— 对应 §1 分层、§2 异常", "§1 · §2"),
            ("汪云飞《Spring Boot 实战》第 6 章数据校验 —— 对应 §3 校验收口", "§3"),
            ("Spring 官方 Reference：Validation / Exception Handling 章节 —— 对应 §2、§3", "§2 · §3"),
        ],
    },
    "fs-ch12": {
        "subject": "fullstack",
        "gh": [
            ("spring-cloud/spring-cloud-gateway", 4917, "§2.1 网关该管什么 · §2.3 路由", "网关实现：读 `RoutePredicateHandlerMapping` 与过滤器链，对应 §2.1、§2.3"),
            ("nestjs/nest", 76927, "§1 拆分 · §2 网关", "模块化后端框架：module/provider 的边界设计与 §1 分层异曲同工"),
            ("vercel/next.js", 143173, "§2.6 BFF", "BFF 范式：前端定制的聚合层，对应 §2.6 BFF 模式"),
            ("google/guava", 51918, "§3.5 配置中心", "限流与缓存原语：RateLimiter 思路对应 §2.5 限流、§3.5 配置推送"),
        ],
        "bili": [
            ("BV1wC3zeTEmS", "Spring Cloud Gateway过滤器执行优先级", "凉城昔忆iii", "3m30s", "§2.3 路由的坑：匹配顺序"),
            ("BV11g4nznErU", "2小时吃透GateWay微服务网关！", "图灵FOX老师", "169m12s", "§2.1 网关该管什么 · §2.5 限流"),
        ],
        "papers": [
            ("Sam Newman《Building Microservices》第 1、5 章（单块边界、服务拆分）—— 对应 §1 何时该拆", "§1"),
            ("《Spring Microservices in Action》第 4 章 Gateway —— 对应 §2 网关职责", "§2"),
            ("Chris Richardson《Microservices Patterns》第 3 章（配置中心）—— 对应 §3 配置外置", "§3"),
        ],
    },
    "fs-ch13": {
        "subject": "fullstack",
        "gh": [
            ("microsoft/playwright", 98704, "§2.1 等待条件 · §2.2 选择器", "E2E 框架：读 `docs` 的 auto-waiting 与 locator 策略，对应 §2.1、§2.2"),
            ("cypress-io/cypress", 51015, "§2.8 选型", "另一 E2E 实现：对比 Playwright 的时间旅行调试，对应 §2.8"),
            ("pact-foundation/pact-js", 1825, "§3.1 消费者驱动契约", "契约测试：读 `packages/.../message` 看 CDC 工作流，对应 §3.1"),
            ("facebook/react", 251766, "§1 测试金字塔", "组件测试范式：Testing Library 思路对应 §1、§2.3 组件测试"),
        ],
        "bili": [
            ("BV1Fsx56CEsA", "2小时学会playwright自动化测试框架", "AI智能测试平台", "89m44s", "§2.1 稳定性第一原则"),
            ("BV1JQ3BzHEfC", "Playwright+Electron 自动化测试框架", "前端飞行手册", "8m28s", "§2.2 选择器策略"),
        ],
        "papers": [
            ("Kent Beck《Test-Driven Development》—— 对应 §1 测试金字塔理念", "§1"),
            ("《Software Engineering at Google》第 11-12 章（测试规模与模式）—— 对应 §1、§3 门禁", "§1 · §3"),
            ("Jez Humble《Continuous Delivery》第 10 章（部署流水线门禁）—— 对应 §3.3 质量门禁", "§3"),
        ],
    },
    "fs-ch14": {
        "subject": "fullstack",
        "gh": [
            ("vercel/ai", 27560, "§1.1 SSE · §3.1 callId", "AI 流式 SDK：读 `packages/ai` 的 `stream`/`tool` 实现，对应 §1.1、§3.1"),
            ("langchain-ai/langchain", 148600, "§1.1 流式 · §3 工具调用", "Agent 框架：LCEL 流式与 tool calling，对应 §1.1、§3"),
            ("gin-gonic/gin", 89445, "§2 长任务 · §4 限流", "网关侧实现参考：中间件链与限流，对应 §2、§4"),
            ("huggingface/transformers", 168266, "§3.5 审计边界", "推理服务内 tool/函数调用范式，对应 §3.5"),
        ],
        "bili": [
            ("BV1sh1qBdEAp", "最新 Langchain1.0 入门【12】-Agent流式输出", "强哥学编程", "15m42s", "§1.1 SSE 与流式透传"),
            ("BV1UtTr6SE2v", "AI Agent 面试题：Agent 幂等性", "图灵AI大模型", "5m15s", "§3.2 重试幂等"),
            ("BV1kKx76pEtm", "怎么保证Agent工具幂等性？", "AI大模型-阿水", "4m0s", "§3.1 唯一 id · §3.2 幂等"),
        ],
        "papers": [
            ("《Designing Data-Intensive Applications》第 11 章（流处理与一致性）—— 对应 §1 流式、§2 长任务状态", "§1 · §2"),
            ("OpenAI / Anthropic Function Calling 官方文档 —— 对应 §3.1 唯一 id、§3.2 幂等", "§3"),
            ("LangChain 官方文档《Streaming》《Tools》章节 —— 对应 §1.1、§3", "§1 · §3"),
        ],
    },
    "fs-ch15": {
        "subject": "fullstack",
        "gh": [
            ("gin-gonic/gin", 89445, "§2.1 路由树 · §2.2 中间件", "Web 框架：读 `routergroup.go` 与 `context.go` 的 `Next()`，对应 §2.1、§2.2"),
            ("gofiber/fiber", 40232, "§2 对照", "Express 风格对照：与 Gin 中间件模型对比，对应 §2.6"),
            ("golang/go", 139482, "§1.1 goroutine · §3.1 error", "语言本体：读 `src/runtime` 的 GMP 调度，对应 §1.1；error 即值对应 §3.1"),
            ("spring-projects/spring-framework", 60300, "§2.5 对照 · §3.4 对照", "Java 路线对照：拦截器/受检异常对照，对应 §2.5、§3.4"),
        ],
        "bili": [
            ("BV1gJ411p7xC", "【最新Go Web开发教程】基于gin框架和gorm的web开发实战", "七米老师", "727m56s", "§2.1 路由树 · §2.2 中间件"),
            ("BV1hv4y1h7Qn", "[面试]Gin框架在面试被问到最多的问题：动态路由&中间件", "guangju_", "4m13s", "§2.2 中间件链"),
            ("BV12JefzVEEy", "gin框架快速上手入门教程", "枫枫讲Go语言", "196m11s", "§2.1 路由"),
        ],
        "papers": [
            ("Alan Donovan《The Go Programming Language》第 8、9 章（goroutine、channel）—— 对应 §1", "§1"),
            ("《Go in Action》第 3、4 章（并发与通道）—— 对应 §1.2、§1.3", "§1"),
            ("Go 官方《Effective Go》—— 对应 §3.1 error 作为值、§3.2 panic", "§3"),
        ],
    },
    "ai-ch12": {
        "subject": "ai",
        "gh": [
            ("huggingface/transformers", 168266, "§1.1 schema · §1.8 标注规范", "训练数据范式：chat template 与 instruction 格式，对应 §1.1、§1.8"),
            ("huggingface/datasets", 22091, "§2.2 语义去重", "数据处理：map/dedup 算子，对应 §2.2 语义去重"),
            ("vllm-project/vllm", 95746, "§1.8 可追溯", "推理侧数据契约：与训练数据 schema 对齐，对应 §1.8"),
            ("facebookresearch/llama", 59628, "§1.1 多轮格式", "对话格式范本：官方 `llama-recipes` 的 instruction 数据，对应 §1.1"),
        ],
        "bili": [
            ("BV1XXVHzYEK2", "【原理】如何构造微调数据集？对话数据、指令数据、Function call", "九天Hector", "25m25s", "§1.1 可落地的 schema"),
            ("BV1Q8rYYdErf", "大模型微调！手把手带你用LLaMA-Factory工具微调Qwen大模型", "大语言模型教程", "34m36s", "§1.8 质量标注规范"),
        ],
        "papers": [
            ("《Training Language Models to Follow Instructions with Human Feedback》(InstructGPT, NeurIPS 2022) —— 对应 §1.1 schema、§1.8 标注", "§1 · §1.8"),
            ("《Self-Instruct》(ACL 2023) —— 对应 §1.8 合成数据生成", "§1.8"),
            ("《LIMA: Less Is More for Alignment》(NeurIPS 2023) —— 对应 §1.1 格式约束、§2.1 规则过滤", "§1 · §2"),
        ],
    },
    "ai-ch13": {
        "subject": "ai",
        "gh": [
            ("vllm-project/vllm", 95746, "§1.1 显存账 · §2.2 连续批", "推理引擎：读 `vllm/core/scheduler.py` 的 continuous batching，对应 §1.1、§2.2"),
            ("ggerganov/llama.cpp", 132583, "§3.4 GGUF", "本地推理与 GGUF 格式：量化权重加载，对应 §3.4"),
            ("mlc-ai/mlc-llm", 23284, "§3.1 量化 · §3.5 选型", "端侧推理与量化后端，对应 §3.1、§3.5"),
            ("huggingface/transformers", 168266, "§3.1 GPTQ/AWQ 加载", "量化模型加载：bitsandbytes/GPTQ 集成，对应 §3.1"),
        ],
        "bili": [
            ("BV14YopBEEGs", "【2026最新版】这绝对是B站唯一将vLLM推理优化从入门到精通讲明白的", "码士集团-马小萱", "1123m23s", "§1.1 显存账 · §2.2 连续批"),
            ("BV1tujozhEkF", "vLLM验证AWQ和GPTQ量化后的模型以及GGUF介绍", "智驭导师授AI", "16m7s", "§3.1 量化位宽"),
            ("BV1euPkerEun", "【13】GPTQ、AWQ、GGUF等模型量化概念讲解", "LLM张老师", "18m15s", "§3.2 GPTQ · §3.3 AWQ"),
        ],
        "papers": [
            ("《Efficient Memory Management for LLM Serving with PagedAttention》(vLLM, SOSP 2023) —— 对应 §1.1 PagedAttention、§2.2 连续批", "§1 · §2"),
            ("《Orca: A Distributed Serving System for Transformer-Based Generative Models》(OSDI 2022) —— 对应 §2.2 continuous batching", "§2"),
            ("《GPTQ: Accurate Post-Training Quantization》(ICLR 2023) 与《AWQ: Activation-aware Weight Quantization》(CVPR 2024) —— 对应 §3.1、§3.2", "§3"),
        ],
    },
    "ai-ch14": {
        "subject": "ai",
        "gh": [
            ("huggingface/transformers", 168266, "§1.1 CLIP · §2.1 流水线", "多模态模型库：CLIP/Blip/Intern 实现，对应 §1.1、§2.1"),
            ("openai/CLIP", 34539, "§1.1 对比学习", "图文对比学习本体：读 `model.py` 的 image-text 对比，对应 §1.1"),
            ("OpenGVLab/InternVL", 10171, "§1.4 对齐 · §2.1 链路", "多模态大模型：VLM 与 OCR 链路，对应 §1.4、§2.1"),
            ("microsoft/OmniParser", 25578, "§2.1 OCR→VLM", "文档理解：版面检测+识别+VLM 端到端，对应 §2.1"),
        ],
        "bili": [
            ("BV18ZyJBnE4E", "图文多模态｜GLIP：给AI附上理解文本、理解图像且定位的能力", "魔傀面具", "15m59s", "§1.1 CLIP 式对比学习"),
            ("BV1F14y1K7bu", "阿里发布最强中文图文多模态模型：Chinese CLIP", "数源AI官方", "0m45s", "§1.1 图文对齐"),
        ],
        "papers": [
            ("《Learning Transferable Visual Models From Natural Language Supervision》(CLIP, ICML 2021) —— 对应 §1.1 对比学习", "§1"),
            ("《BLIP-2》(ICML 2023) 与《InternVL》(CVPR 2024) —— 对应 §1.4 对齐、§2.1 OCR→VLM 链路", "§1 · §2"),
            ("《Dense X Retrieval》/ 多模态 RAG survey —— 对应 §3.1 多模态 RAG", "§3"),
        ],
    },
}


def fmt_star(n: int) -> str:
    return f"{n:,}"


def build_block(ch: str, d: dict) -> str:
    L = []
    L.append("")
    L.append("## 本章 GitHub 学习路线（按阅读顺序）")
    L.append("")
    L.append("> 顺序即路线：**先读能跑的最小实现 → 再读同章对照实现 → 最后读工业级库**。「对应本章」写 `§x.y` 的，说明这份仓库与本章那一节直接对应，先读那里；写「全章」的，按右侧「读什么」给的入口文件读，不要从 README 通读。")
    L.append("")
    L.append("| # | 仓库 | Star | 对应本章 | 读什么 |")
    L.append("| --- | --- | ---: | --- | --- |")
    for i, (repo, star, anchor, what) in enumerate(d["gh"], 1):
        L.append(f"| {i} | [{repo}](https://github.com/{repo}) | {fmt_star(star)} | {anchor} | {what} |")
    L.append("")
    L.append("> 全部为工业级真实仓库；Star 数为本会话经 GitHub API 实取快照，仅供路线排序参考。")
    L.append("")
    L.append("## 本章 B 站视频路线（与 GitHub 互补）")
    L.append("")
    L.append("> 全部为 B 站直链（`bilibili.com/video/BV…`），BV 号均已通过站内接口核验可播放；视频用于「先看别人怎么讲，再回头跑本章示例」。")
    L.append("")
    L.append("| # | 视频 | BV | 对应本章 | 备注 |")
    L.append("| --- | --- | --- | --- | --- |")
    for i, (bv, title, up, dur, anchor) in enumerate(d["bili"], 1):
        L.append(f"| {i} | {title}<br><sub>{up}</sub> | [{bv}](https://www.bilibili.com/video/{bv}/) | {anchor} | 时长 {dur} |")
    L.append("")
    L.append("## 本章配套论文与书（溯源用）")
    L.append("")
    L.append("> 图例：`§x.y` = 本章第 x 篇 concept 文件的第 y 节。读论文时带着 §x.y 的问题去读，能把「为什么」落到机制上。")
    L.append("")
    L.append("| # | 文献 | 对应本章 |")
    L.append("| --- | --- | --- |")
    for i, (paper, anchor) in enumerate(d["papers"], 1):
        L.append(f"| {i} | {paper} | {anchor} |")
    L.append("")
    return "\n".join(L)


def append_section(chapter_dir: pathlib.Path, block: str) -> None:
    p = chapter_dir / "goals.md"
    text = p.read_text(encoding="utf-8")
    if "## 本章 GitHub 学习路线" in text:
        print(f"  · {chapter_dir.name} 已有资源段，跳过", file=sys.stderr)
        return
    # 去掉末尾多余空行再追加
    text = text.rstrip() + "\n" + block
    p.write_text(text, encoding="utf-8")


def write_manifest_books(subject: str, cid: str, papers: list) -> None:
    mf = CONTENT / subject / "_manifest.json"
    if not mf.exists():
        return
    m = json.loads(mf.read_text(encoding="utf-8"))
    units = m.get("chapters", [])
    for u in units:
        if u.get("id") == cid:
            res = u.get("resources") or {}
            res["books"] = [p[0] for p in papers]
            u["resources"] = res
            break
    mf.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    for ch, d in DATA.items():
        subj = d["subject"]
        cd = CONTENT / subj / ch
        if not cd.exists():
            print(f"[skip] {ch} 目录不存在", file=sys.stderr)
            continue
        append_section(cd, build_block(ch, d))
        write_manifest_books(subj, ch, d["papers"])
        print(f"[ok] {ch} 资源段已追加 + manifest books 已写", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
