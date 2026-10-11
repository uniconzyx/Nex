import re

# gcc/clang 常见错误 → 中文诊断规则库。
# 规则库优先命中，未命中才转 AI（架构文档 8.4 成本控制）。
_RULES: list[tuple[str, str, str]] = [
    (r"undeclared identifier|was not declared in this scope",
     "标识符未声明",
     "变量/函数在使用前未声明。检查：1) 拼写是否与声明一致；2) 是否漏了对应的头文件；3) 声明位置是否在使用点之前。"),
    (r"expected [';]*'?;'? before",
     "缺少分号",
     "编译器在指定位置之前期望一个分号。重点检查报错行的**上一行**末尾是否漏了 `;`，结构体/类定义结尾的 `;` 最容易漏。"),
    (r"expected ['}]*'?}'?",
     "花括号不配对",
     "存在未闭合的 `{`。用编辑器的括号匹配功能从报错位置向上查找。"),
    (r"no match for 'operator<<'|no match for 'operator>>'",
     "流运算符类型不匹配",
     "对不支持 `<<`/`>>` 的类型做了流操作。常见原因：自定义类型未重载运算符，或漏了 `<iostream>`/`<string>` 头文件。"),
    (r"cannot convert '.*' to '.*' in (initialization|assignment)",
     "类型转换失败",
     "赋值/初始化时类型不兼容。检查指针层级（如 `int*` vs `int`）、const 限定符是否被丢弃。"),
    (r"undefined reference to",
     "链接错误：符号未定义",
     "函数/变量声明了但没有定义，或定义在未被链接的源文件中。多文件项目检查 Makefile/编译命令是否包含所有 .cpp。"),
    (r"multiple definition of",
     "链接错误：重复定义",
     "同一符号被定义了多次。常见原因：在头文件中定义了非 inline 函数/变量，被多个 .cpp 包含。改用 `inline` 或把定义移到 .cpp。"),
    (r"invalid use of incomplete type|incomplete type",
     "不完整类型的使用",
     "只用了前向声明却访问了成员。在使用点之前包含完整定义（头文件）。"),
    (r"does not name a type",
     "名字不是类型",
     "通常是类型名拼写错误、命名空间未引入（如 `string` 应为 `std::string`），或循环包含导致声明不可见。"),
    (r"request for member .* in .* which is of non-class type",
     "对非类类型访问成员",
     "形如 `a.b` 但 a 不是类/结构体。常见：`obj.method()` 写成了 `obj.method` 后又取成员，或把指针 `.` 应为 `->`。"),
    (r"invalid conversion from .* to .* \[-fpermissive\]",
     "非法隐式转换",
     "如 `int` 直接赋给指针。若确实需要，显式 `reinterpret_cast`；但先确认逻辑是否正确。"),
    (r"too (few|many) arguments to function",
     "函数参数个数不匹配",
     "调用与声明的参数个数不一致。检查函数签名与调用点，注意默认参数与重载。"),
    (r"Segmentation fault|SIGSEGV",
     "段错误（运行时）",
     "访问了非法内存。高发原因：1) 空指针/野指针解引用；2) 数组越界；3) 使用已释放的内存（悬垂指针）；4) 栈溢出（递归过深）。用 `-g` 编译 + gdb/ASan 定位。"),
    (r"AddressSanitizer|heap-use-after-free",
     "使用已释放内存（ASan）",
     "对象 delete/free 后仍被访问。检查所有权：谁创建、谁释放、释放后是否置空。C++ 优先改用智能指针。"),
    (r"stack smashing detected|buffer overflow",
     "栈缓冲区溢出",
     "对局部数组写入越界。检查 strcpy/scanf 未限长，改用 strncpy/限制宽度或 std::string。"),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), title, advice) for pat, title, advice in _RULES]


def diagnose(stderr: str | None, status: str) -> str | None:
    """返回中文诊断 Markdown；无命中返回 None（交由 AI 兜底）。"""
    if not stderr:
        return None
    for rx, title, advice in _COMPILED:
        m = rx.search(stderr)
        if m:
            return (
                f"**规则库诊断：{title}**\n\n"
                f"{advice}\n\n"
                f"---\n匹配到的编译器输出：\n```\n{m.group(0)}\n```"
            )
    return None
