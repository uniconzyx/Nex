"""给编程题补「真可判」的 test_cases（本地实跑生成期望输出，不手抄）。

为什么要重写参考代码
--------------------------------------------------------------------
go-judge 的判题方式是 **完整程序 + stdin → 比对 stdout**（见
`server/app/services/judge0.py:62`）。但题库里绝大多数 `reference_code`
是「函数 + 硬编码 main」，没有 stdin 接口，所以过去那批 test_cases 里
大量是 `input: "nums=[2,7,11,15], target=9"` 这种**人类可读但程序没法吃**
的自由文本 —— 名义可判、实际判不了。

本脚本对每道题做三件事：
  1. 在题面追加统一的「判题 I/O 约定」段落（带 `<!-- judge-io -->` 标记，幂等）；
  2. 把 `answer.reference_code` 换成**读 stdin / 写 stdout 的完整程序**；
  3. 用本机解释器/编译器**真实运行**这份参考程序，用它的输出作为
     `expected_output` —— 期望值不是人写的，是跑出来的，天然不会错。

不适合判题的题（计时对比、内存观测、并发调度、依赖外部文件系统）
不在此表内，它们保持「对照参考答案自评」，绝不硬塞假用例。

用法
--------------------------------------------------------------------
    python scripts/add_judge_cases.py            # dry-run：只跑验证，不写
    python scripts/add_judge_cases.py --apply    # 写入
    python scripts/add_judge_cases.py --restore  # 还原
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
BACKUP = CONTENT / "_backup_judge_cases"
MARKER = "<!-- judge-io -->"

PY = sys.executable
GPP = "g++"
GCC = "gcc"
JAVAC = "javac"
JAVA = "java"


# ---------------------------------------------------------------- 题解与用例
# 每项：file / title（前缀匹配）/ io（题面 I/O 说明）/ code（stdin 版参考实现）/ cases
PY_PACK: list[dict] = [
    {
        "file": "python/py-ch01/exercises.json",
        "title": "实现字符串反转函数",
        "io": ("输入：一行字符串 `s`（可能含空格，不含换行）。\n"
               "输出：反转后的字符串，占一行。"),
        "code": (
            "import sys\n\n\n"
            "def reverse_str(s):\n"
            "    return s[::-1]\n\n\n"
            "if __name__ == '__main__':\n"
            "    s = sys.stdin.readline().rstrip('\\n')\n"
            "    print(reverse_str(s))\n"
        ),
        "cases": ["cat", "hello world", "CppMind 2026"],
    },
    {
        "file": "python/py-ch01/exercises.json",
        "title": "LeetCode 704",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个严格升序整数（空格分隔）。\n"
               "输出：`target` 的下标，未找到输出 `-1`。"),
        "code": (
            "import sys\n\n\n"
            "def binary_search(nums, target):\n"
            "    lo, hi = 0, len(nums) - 1\n"
            "    while lo <= hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if nums[mid] == target:\n"
            "            return mid\n"
            "        elif nums[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1\n\n\n"
            "if __name__ == '__main__':\n"
            "    data = sys.stdin.read().split()\n"
            "    n, target = int(data[0]), int(data[1])\n"
            "    nums = [int(x) for x in data[2:2 + n]]\n"
            "    print(binary_search(nums, target))\n"
        ),
        "cases": ["6 9\n-1 0 3 5 9 12", "6 2\n-1 0 3 5 9 12", "1 5\n5"],
    },
    {
        "file": "python/py-ch01/exercises.json",
        "title": "牛客 BM21",
        "io": ("输入：第一行两个整数 `n k`；第二行 `n` 个整数（空格分隔）。\n"
               "输出：向右旋转 `k` 位后的数组，空格分隔，占一行。"),
        "code": (
            "import sys\n\n\n"
            "def rotate(nums, k):\n"
            "    n = len(nums)\n"
            "    if n == 0:\n"
            "        return nums\n"
            "    k %= n\n"
            "    return nums[-k:] + nums[:-k] if k else nums\n\n\n"
            "if __name__ == '__main__':\n"
            "    data = sys.stdin.read().split()\n"
            "    n, k = int(data[0]), int(data[1])\n"
            "    nums = [int(x) for x in data[2:2 + n]]\n"
            "    print(' '.join(map(str, rotate(nums, k))))\n"
        ),
        "cases": ["5 2\n1 2 3 4 5", "3 4\n1 2 3", "1 0\n7"],
    },
    {
        "file": "python/py-ch02/exercises.json",
        "title": "用函数封装解决 two-sum",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个整数（空格分隔），保证恰有一组解。\n"
               "输出：两个下标（较小的在前），空格分隔。"),
        "code": (
            "import sys\n\n\n"
            "def make_checker(target):\n"
            "    def check(seen, v):\n"
            "        return (target - v) in seen\n"
            "    return check\n\n\n"
            "def two_sum(nums, target):\n"
            "    check = make_checker(target)\n"
            "    seen = {}\n"
            "    for i, v in enumerate(nums):\n"
            "        if check(seen, v):\n"
            "            return [seen[target - v], i]\n"
            "        seen[v] = i\n"
            "    return []\n\n\n"
            "if __name__ == '__main__':\n"
            "    data = sys.stdin.read().split()\n"
            "    n, target = int(data[0]), int(data[1])\n"
            "    nums = [int(x) for x in data[2:2 + n]]\n"
            "    res = two_sum(nums, target)\n"
            "    print(' '.join(map(str, sorted(res))))\n"
        ),
        "cases": ["4 9\n2 7 11 15", "3 6\n3 2 4", "2 6\n3 3"],
    },
    {
        "file": "python/py-ch03/exercises.json",
        "title": "用 dict 计数判断字母异位词",
        "io": ("输入：两行，分别为字符串 `s` 与 `t`（只含小写字母，不含空格）。\n"
               "输出：`True` 或 `False`。"),
        "code": (
            "import sys\n\n\n"
            "def is_anagram(s, t):\n"
            "    if len(s) != len(t):\n"
            "        return False\n"
            "    cnt = {}\n"
            "    for ch in s:\n"
            "        cnt[ch] = cnt.get(ch, 0) + 1\n"
            "    for ch in t:\n"
            "        if ch not in cnt:\n"
            "            return False\n"
            "        cnt[ch] -= 1\n"
            "        if cnt[ch] == 0:\n"
            "            del cnt[ch]\n"
            "    return not cnt\n\n\n"
            "if __name__ == '__main__':\n"
            "    lines = sys.stdin.read().split('\\n')\n"
            "    s = lines[0].strip()\n"
            "    t = lines[1].strip() if len(lines) > 1 else ''\n"
            "    print(is_anagram(s, t))\n"
        ),
        "cases": ["anagram\nnagaram", "rat\ncar", "a\nab"],
    },
    {
        "file": "python/py-ch03/exercises.json",
        "title": "用 set 求交集并保序",
        "io": ("输入：两行，每行为若干个整数（空格分隔），分别表示 `nums1`、`nums2`。\n"
               "输出：交集元素（去重，按 `nums1` 中首次出现的顺序），空格分隔，占一行。"),
        "code": (
            "import sys\n\n\n"
            "def intersection_ordered(nums1, nums2):\n"
            "    s2 = set(nums2)\n"
            "    return [x for x in dict.fromkeys(nums1) if x in s2]\n\n\n"
            "if __name__ == '__main__':\n"
            "    lines = sys.stdin.read().split('\\n')\n"
            "    a = [int(x) for x in lines[0].split()] if lines else []\n"
            "    b = [int(x) for x in lines[1].split()] if len(lines) > 1 else []\n"
            "    print(' '.join(map(str, intersection_ordered(a, b))))\n"
        ),
        "cases": ["1 2 2 1\n2 2", "4 9 5 9\n9 4 9 8 4", "1 1 2\n1"],
    },
]


PY_PACK2: list[dict] = [
    {
        "file": "python/py-ch04/exercises.json",
        "title": "简化 Unix 风格路径",
        "io": ("输入：一行 Unix 风格绝对路径（不含换行）。\n"
               "输出：简化后的规范路径，占一行。"),
        "code": (
            "import sys\n\n\n"
            "def simplify_path(path):\n"
            "    stack = []\n"
            "    for part in path.split('/'):\n"
            "        if part == '' or part == '.':\n"
            "            continue\n"
            "        if part == '..':\n"
            "            if stack:\n"
            "                stack.pop()\n"
            "        else:\n"
            "            stack.append(part)\n"
            "    return '/' + '/'.join(stack)\n\n\n"
            "if __name__ == '__main__':\n"
            "    print(simplify_path(sys.stdin.readline().strip()))\n"
        ),
        "cases": ["/home/", "/../", "/home//foo/", "/a/./b/../../c/"],
    },
    {
        "file": "python/py-ch05/exercises.json",
        "title": "手写 CSV 行解析器",
        "io": ("输入：一行 CSV 文本（字段可能被双引号包裹，内部 `\"\"` 表示一个引号）。\n"
               "输出：解析出的字段个数，随后逐行输出每个字段（用 `[字段]` 包裹，便于看出空字段）。"),
        "code": (
            "import sys\n\n\n"
            "def parse_csv_line(line):\n"
            "    fields, buf, i, n, in_quotes = [], [], 0, len(line), False\n"
            "    while i < n:\n"
            "        c = line[i]\n"
            "        if in_quotes:\n"
            "            if c == '\"':\n"
            "                if i + 1 < n and line[i + 1] == '\"':\n"
            "                    buf.append('\"')\n"
            "                    i += 2\n"
            "                    continue\n"
            "                in_quotes = False\n"
            "            else:\n"
            "                buf.append(c)\n"
            "        else:\n"
            "            if c == '\"':\n"
            "                in_quotes = True\n"
            "            elif c == ',':\n"
            "                fields.append(''.join(buf))\n"
            "                buf = []\n"
            "            else:\n"
            "                buf.append(c)\n"
            "        i += 1\n"
            "    fields.append(''.join(buf))\n"
            "    return fields\n\n\n"
            "if __name__ == '__main__':\n"
            "    fs = parse_csv_line(sys.stdin.readline().rstrip('\\n'))\n"
            "    print(len(fs))\n"
            "    for f in fs:\n"
            "        print('[' + f + ']')\n"
        ),
        "cases": ['a,b,c', 'a,"b,c",d', '"he said ""hi""",2'],
    },
    {
        "file": "python/py-ch06/exercises.json",
        "title": "实现支持 . 与 * 的正则匹配",
        "io": ("输入：两行，第一行字符串 `s`，第二行模式 `p`（只含小写字母、`.`、`*`）。\n"
               "输出：`True` 或 `False`（整串匹配结果）。"),
        "code": (
            "import sys\n\n\n"
            "def is_match(s, p):\n"
            "    n, m = len(s), len(p)\n"
            "    dp = [[False] * (m + 1) for _ in range(n + 1)]\n"
            "    dp[0][0] = True\n"
            "    for j in range(2, m + 1):\n"
            "        if p[j - 1] == '*':\n"
            "            dp[0][j] = dp[0][j - 2]\n"
            "    for i in range(1, n + 1):\n"
            "        for j in range(1, m + 1):\n"
            "            if p[j - 1] == '*':\n"
            "                dp[i][j] = dp[i][j - 2]\n"
            "                if p[j - 2] == '.' or p[j - 2] == s[i - 1]:\n"
            "                    dp[i][j] = dp[i][j] or dp[i - 1][j]\n"
            "            elif p[j - 1] == '.' or p[j - 1] == s[i - 1]:\n"
            "                dp[i][j] = dp[i - 1][j - 1]\n"
            "    return dp[n][m]\n\n\n"
            "if __name__ == '__main__':\n"
            "    lines = sys.stdin.read().split('\\n')\n"
            "    s = lines[0].strip()\n"
            "    p = lines[1].strip() if len(lines) > 1 else ''\n"
            "    print(is_match(s, p))\n"
        ),
        "cases": ["aa\na", "aa\na*", "ab\n.*", "mississippi\nmis*is*p*."],
    },
    {
        "file": "python/py-ch06/exercises.json",
        "title": "把连续空白压缩为单个空格",
        "io": ("输入：一行文本（可能含多余空格/制表符）。\n"
               "输出：压缩并去首尾后的文本，用 `[文本]` 包裹输出，便于看出空结果。"),
        "code": (
            "import re\n"
            "import sys\n\n\n"
            "_WS = re.compile(r'\\s+')\n\n\n"
            "def squash(text):\n"
            "    return _WS.sub(' ', text).strip()\n\n\n"
            "if __name__ == '__main__':\n"
            "    print('[' + squash(sys.stdin.readline().rstrip('\\n')) + ']')\n"
        ),
        "cases": ["  a   b ", "a\t\tb", "   "],
    },
]

CPP_PACK: list[dict] = [
    {
        "file": "cpp/cpp-ch02/exercises.json",
        "title": "实现字符串反转函数",
        "io": ("输入：一行字符串 `s`（可能含空格，不含换行）。\n"
               "输出：反转后的字符串，占一行。"),
        "code": (
            "#include <algorithm>\n#include <iostream>\n#include <string>\n\n"
            "std::string reverse_str(const std::string& s) {\n"
            "    std::string r(s);\n"
            "    std::reverse(r.begin(), r.end());\n"
            "    return r;\n"
            "}\n\n"
            "int main() {\n"
            "    std::string s;\n"
            "    std::getline(std::cin, s);\n"
            "    std::cout << reverse_str(s) << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["cat", "hello world", "CppMind"],
    },
    {
        "file": "cpp/cpp-ch02/exercises.json",
        "title": "LeetCode 20",
        "io": ("输入：一行只含 `()[]{}` 的字符串（可能为空行）。\n"
               "输出：`true` 或 `false`。"),
        "code": (
            "#include <iostream>\n#include <stack>\n#include <string>\n\n"
            "bool isValid(const std::string& s) {\n"
            "    std::stack<char> st;\n"
            "    for (char c : s) {\n"
            "        if (c == '(' || c == '[' || c == '{') {\n"
            "            st.push(c);\n"
            "        } else {\n"
            "            if (st.empty()) return false;\n"
            "            char t = st.top(); st.pop();\n"
            "            if ((c == ')' && t != '(') || (c == ']' && t != '[') ||\n"
            "                (c == '}' && t != '{')) return false;\n"
            "        }\n"
            "    }\n"
            "    return st.empty();\n"
            "}\n\n"
            "int main() {\n"
            "    std::string s;\n"
            "    std::getline(std::cin, s);\n"
            "    std::cout << (isValid(s) ? \"true\" : \"false\") << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["()[]{}", "(]", "([)]", "{[()]}"],
    },
    {
        "file": "cpp/cpp-ch03/exercises.json",
        "title": "LeetCode 344",
        "io": ("输入：一行字符串 `s`。\n"
               "输出：原地反转后的字符串，占一行。"),
        "code": (
            "#include <algorithm>\n#include <iostream>\n#include <string>\n\n"
            "void reverseString(std::string& s) {\n"
            "    std::reverse(s.begin(), s.end());\n"
            "}\n\n"
            "int main() {\n"
            "    std::string s;\n"
            "    std::getline(std::cin, s);\n"
            "    reverseString(s);\n"
            "    std::cout << s << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["hello", "Hannah", "a"],
    },
    {
        "file": "cpp/cpp-ch03/exercises.json",
        "title": "LeetCode 415",
        "io": ("输入：两行，分别为非负整数字符串 `num1`、`num2`。\n"
               "输出：两者之和的字符串表示。"),
        "code": (
            "#include <algorithm>\n#include <iostream>\n#include <string>\n\n"
            "std::string addStrings(std::string a, std::string b) {\n"
            "    std::string r;\n"
            "    int i = (int)a.size() - 1, j = (int)b.size() - 1, carry = 0;\n"
            "    while (i >= 0 || j >= 0 || carry) {\n"
            "        int s = carry;\n"
            "        if (i >= 0) s += a[i--] - '0';\n"
            "        if (j >= 0) s += b[j--] - '0';\n"
            "        r.push_back(char('0' + s % 10));\n"
            "        carry = s / 10;\n"
            "    }\n"
            "    std::reverse(r.begin(), r.end());\n"
            "    return r;\n"
            "}\n\n"
            "int main() {\n"
            "    std::string a, b;\n"
            "    std::getline(std::cin, a);\n"
            "    std::getline(std::cin, b);\n"
            "    std::cout << addStrings(a, b) << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["11\n123", "456\n77", "0\n0", "9999\n1"],
    },
    {
        "file": "cpp/cpp-ch09/exercises.json",
        "title": "用 STL 算法统计并输出词频 Top3",
        "io": ("输入：第一行整数 `n`；第二行 `n` 个以空格分隔的单词。\n"
               "输出：频次最高的 3 个单词，每行 `word:count`（频次相同按词典序，不足 3 个则全部输出）。"),
        "code": (
            "#include <algorithm>\n#include <iostream>\n#include <string>\n"
            "#include <unordered_map>\n#include <vector>\n\n"
            "int main() {\n"
            "    int n = 0;\n"
            "    if (!(std::cin >> n)) return 0;\n"
            "    std::unordered_map<std::string, int> cnt;\n"
            "    for (int i = 0; i < n; ++i) {\n"
            "        std::string w;\n"
            "        std::cin >> w;\n"
            "        ++cnt[w];\n"
            "    }\n"
            "    std::vector<std::pair<std::string, int>> v(cnt.begin(), cnt.end());\n"
            "    std::sort(v.begin(), v.end(), [](const auto& a, const auto& b) {\n"
            "        if (a.second != b.second) return a.second > b.second;\n"
            "        return a.first < b.first;\n"
            "    });\n"
            "    int k = std::min<int>(3, (int)v.size());\n"
            "    for (int i = 0; i < k; ++i)\n"
            "        std::cout << v[i].first << \":\" << v[i].second << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": [
            "5\napple banana apple cherry banana",
            "7\na b c a b a",
            "4\nz y x w",
        ],
    },
    {
        "file": "cpp/cpp-ch13/exercises.json",
        "title": "用 stringstream 解析一行逗号分隔的数据",
        "io": ("输入：一行形如 `名字,年龄,分数` 的文本。\n"
               "输出：`name age score`（空格分隔，占一行）。"),
        "code": (
            "#include <iostream>\n#include <sstream>\n#include <string>\n\n"
            "int main() {\n"
            "    std::string line;\n"
            "    std::getline(std::cin, line);\n"
            "    std::istringstream iss(line);\n"
            "    std::string name, age_s, score_s;\n"
            "    std::getline(iss, name, ',');\n"
            "    std::getline(iss, age_s, ',');\n"
            "    std::getline(iss, score_s);\n"
            "    int age = std::stoi(age_s);\n"
            "    double score = std::stod(score_s);\n"
            "    std::cout << name << \" \" << age << \" \" << score << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["Tom,20,95.5", "Jerry,19,88", "Ann,0,0"],
    },
    {
        "file": "cpp/cpp-ch14/exercises.json",
        "title": "用 inline 函数替代宏实现 square",
        "io": ("输入：一行一个整数 `x`。\n"
               "输出三行：第一行 `square(x)`；第二行 `square(y++)` 的结果；第三行自增后的 `y`"
               "（第二、三行用于验证参数只求值一次、无宏副作用）。"),
        "code": (
            "#include <iostream>\n\n"
            "template <typename T>\n"
            "inline T square(T x) {\n"
            "    return x * x;\n"
            "}\n\n"
            "int main() {\n"
            "    long long x;\n"
            "    std::cin >> x;\n"
            "    std::cout << square(x) << \"\\n\";\n"
            "    long long y = x;\n"
            "    std::cout << square(y++) << \"\\n\";\n"
            "    std::cout << y << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["5", "-3", "0"],
    },
    {
        "file": "cpp/cpp-ch19/exercises.json",
        "title": "为开源算法实现补一套参数化",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个升序整数（空格分隔）。\n"
               "输出：`target` 的下标；找不到输出 `-1`。"),
        "code": (
            "#include <iostream>\n#include <vector>\n\n"
            "int binary_search_idx(const std::vector<int>& a, int target) {\n"
            "    int lo = 0, hi = (int)a.size() - 1;\n"
            "    while (lo <= hi) {\n"
            "        int mid = lo + (hi - lo) / 2;\n"
            "        if (a[mid] == target) return mid;\n"
            "        if (a[mid] < target) lo = mid + 1;\n"
            "        else hi = mid - 1;\n"
            "    }\n"
            "    return -1;\n"
            "}\n\n"
            "int main() {\n"
            "    int n, target;\n"
            "    if (!(std::cin >> n >> target)) return 0;\n"
            "    std::vector<int> a(n);\n"
            "    for (int& v : a) std::cin >> v;\n"
            "    std::cout << binary_search_idx(a, target) << \"\\n\";\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["6 9\n-1 0 3 5 9 12", "6 2\n-1 0 3 5 9 12", "1 5\n5"],
    },
]


C_PACK: list[dict] = [
    {
        "file": "fundamentals/fund-ch01/exercises.json",
        "title": "原地删除有序数组中的重复元素",
        "io": ("输入：第一行整数 `n`；第二行 `n` 个非递减整数（空格分隔）。\n"
               "输出：第一行新长度 `k`；第二行去重后的前 `k` 个元素（空格分隔）。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int remove_duplicates(int *a, int n) {\n"
            "    if (n == 0) return 0;\n"
            "    int k = 1;\n"
            "    for (int i = 1; i < n; i++)\n"
            "        if (a[i] != a[k - 1]) a[k++] = a[i];\n"
            "    return k;\n"
            "}\n\n"
            "int main(void) {\n"
            "    int n;\n"
            "    if (scanf(\"%d\", &n) != 1) return 0;\n"
            "    static int a[100005];\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
            "    int k = remove_duplicates(a, n);\n"
            "    printf(\"%d\\n\", k);\n"
            "    for (int i = 0; i < k; i++) printf(i ? \" %d\" : \"%d\", a[i]);\n"
            "    printf(\"\\n\");\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["8\n0 0 1 1 1 2 2 3", "5\n1 1 2 3 3", "1\n7"],
    },
    {
        "file": "fundamentals/fund-ch02/exercises.json",
        "title": "有效的括号",
        "io": ("输入：一行只含 `()[]{}` 的字符串（可能为空行）。\n"
               "输出：`true` 或 `false`。"),
        "code": (
            "#include <stdio.h>\n#include <string.h>\n\n"
            "int isValid(const char *s) {\n"
            "    char st[10000];\n"
            "    int top = 0;\n"
            "    for (int i = 0; s[i]; i++) {\n"
            "        char c = s[i];\n"
            "        if (c == '(' || c == '[' || c == '{') {\n"
            "            st[top++] = c;\n"
            "        } else {\n"
            "            if (!top) return 0;\n"
            "            char t = st[--top];\n"
            "            if ((c == ')' && t != '(') || (c == ']' && t != '[') ||\n"
            "                (c == '}' && t != '{')) return 0;\n"
            "        }\n"
            "    }\n"
            "    return top == 0;\n"
            "}\n\n"
            "int main(void) {\n"
            "    static char s[10005];\n"
            "    if (!fgets(s, sizeof s, stdin)) return 0;\n"
            "    size_t L = strlen(s);\n"
            "    while (L && (s[L - 1] == '\\n' || s[L - 1] == '\\r')) s[--L] = 0;\n"
            "    printf(\"%s\\n\", isValid(s) ? \"true\" : \"false\");\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["()[]{}", "(]", "([)]", "{[()]}"],
    },
    {
        "file": "fundamentals/fund-ch02/exercises.json",
        "title": "每日温度",
        "io": ("输入：第一行整数 `n`；第二行 `n` 个整数（空格分隔）。\n"
               "输出：`n` 个整数，第 i 个表示还需要等几天才出现更高温度（没有则为 0），空格分隔。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    int n;\n"
            "    if (scanf(\"%d\", &n) != 1) return 0;\n"
            "    static int t[100005], res[100005], stk[100005];\n"
            "    int top = 0;\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &t[i]);\n"
            "    for (int i = 0; i < n; i++) {\n"
            "        while (top && t[stk[top - 1]] < t[i]) {\n"
            "            int j = stk[--top];\n"
            "            res[j] = i - j;\n"
            "        }\n"
            "        stk[top++] = i;\n"
            "    }\n"
            "    while (top) res[stk[--top]] = 0;\n"
            "    for (int i = 0; i < n; i++) printf(i ? \" %d\" : \"%d\", res[i]);\n"
            "    printf(\"\\n\");\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["8\n73 74 75 71 69 72 76 73", "4\n30 40 50 60", "3\n5 5 5"],
    },
    {
        "file": "fundamentals/fund-ch05/exercises.json",
        "title": "二分查找（Binary Search）",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个升序整数（空格分隔）。\n"
               "输出：`target` 的下标，未找到输出 `-1`。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int search(int *nums, int numsSize, int target) {\n"
            "    int lo = 0, hi = numsSize - 1;\n"
            "    while (lo <= hi) {\n"
            "        int mid = lo + (hi - lo) / 2;\n"
            "        if (nums[mid] == target) return mid;\n"
            "        if (nums[mid] < target) lo = mid + 1;\n"
            "        else hi = mid - 1;\n"
            "    }\n"
            "    return -1;\n"
            "}\n\n"
            "int main(void) {\n"
            "    int n, target;\n"
            "    if (scanf(\"%d %d\", &n, &target) != 2) return 0;\n"
            "    static int a[100005];\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
            "    printf(\"%d\\n\", search(a, n, target));\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["6 9\n-1 0 3 5 9 12", "6 2\n-1 0 3 5 9 12", "1 5\n5"],
    },
    {
        "file": "fundamentals/fund-ch05/exercises.json",
        "title": "在排序数组中查找元素的第一个和最后一个位置",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个非递减整数（空格分隔）。\n"
               "输出：`target` 的起始与结束下标（空格分隔）；不存在则输出 `-1 -1`。"),
        "code": (
            "#include <stdio.h>\n\n"
            "static int lower_bound(int *a, int n, int t) {\n"
            "    int lo = 0, hi = n;\n"
            "    while (lo < hi) {\n"
            "        int mid = lo + (hi - lo) / 2;\n"
            "        if (a[mid] < t) lo = mid + 1;\n"
            "        else hi = mid;\n"
            "    }\n"
            "    return lo;\n"
            "}\n\n"
            "int main(void) {\n"
            "    int n, target;\n"
            "    if (scanf(\"%d %d\", &n, &target) != 2) return 0;\n"
            "    static int a[100005];\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
            "    int lo = lower_bound(a, n, target);\n"
            "    int hi = lower_bound(a, n, target + 1) - 1;\n"
            "    if (lo <= hi && lo < n && a[lo] == target) printf(\"%d %d\\n\", lo, hi);\n"
            "    else printf(\"-1 -1\\n\");\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["6 8\n5 7 7 8 8 10", "6 6\n5 7 7 8 8 10", "1 1\n1"],
    },
    {
        "file": "fundamentals/fund-ch05/exercises.json",
        "title": "两数之和（哈希表）",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个整数（空格分隔），保证恰有一组解。\n"
               "输出：两个下标（较小的在前），空格分隔。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    int n, target;\n"
            "    if (scanf(\"%d %d\", &n, &target) != 2) return 0;\n"
            "    static int a[100005];\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
            "    /* O(n^2) 暴力版：本题核心是哈希思路，判题只看结果正确 */\n"
            "    for (int i = 0; i < n; i++)\n"
            "        for (int j = i + 1; j < n; j++)\n"
            "            if (a[i] + a[j] == target) {\n"
            "                printf(\"%d %d\\n\", i, j);\n"
            "                return 0;\n"
            "            }\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["4 9\n2 7 11 15", "3 6\n3 2 4", "2 6\n3 3"],
    },
    {
        "file": "fundamentals/fund-ch05/exercises.json",
        "title": "搜索旋转排序数组",
        "io": ("输入：第一行两个整数 `n target`；第二行 `n` 个旋转后的升序整数（空格分隔）。\n"
               "输出：`target` 的下标，未找到输出 `-1`。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int search_rotated(int *a, int n, int target) {\n"
            "    int lo = 0, hi = n - 1;\n"
            "    while (lo <= hi) {\n"
            "        int mid = lo + (hi - lo) / 2;\n"
            "        if (a[mid] == target) return mid;\n"
            "        if (a[lo] <= a[mid]) {\n"
            "            if (a[lo] <= target && target < a[mid]) hi = mid - 1;\n"
            "            else lo = mid + 1;\n"
            "        } else {\n"
            "            if (a[mid] < target && target <= a[hi]) lo = mid + 1;\n"
            "            else hi = mid - 1;\n"
            "        }\n"
            "    }\n"
            "    return -1;\n"
            "}\n\n"
            "int main(void) {\n"
            "    int n, target;\n"
            "    if (scanf(\"%d %d\", &n, &target) != 2) return 0;\n"
            "    static int a[100005];\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &a[i]);\n"
            "    printf(\"%d\\n\", search_rotated(a, n, target));\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["7 0\n4 5 6 7 0 1 2", "7 3\n4 5 6 7 0 1 2", "1 0\n1"],
    },
    {
        "file": "fundamentals/fund-ch07/exercises.json",
        "title": "位 1 的个数",
        "io": ("输入：一行一个非负整数 `n`（32 位范围内）。\n"
               "输出：其二进制表示中 `1` 的个数。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int hammingWeight(unsigned int n) {\n"
            "    int c = 0;\n"
            "    while (n) {\n"
            "        n &= n - 1;\n"
            "        ++c;\n"
            "    }\n"
            "    return c;\n"
            "}\n\n"
            "int main(void) {\n"
            "    unsigned int n;\n"
            "    if (scanf(\"%u\", &n) != 1) return 0;\n"
            "    printf(\"%d\\n\", hammingWeight(n));\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": ["11", "128", "0", "4294967295"],
    },
    {
        "file": "fundamentals/fund-ch08/exercises.json",
        "title": "矩阵置零",
        "io": ("输入：第一行两个整数 `m n`；随后 `m` 行，每行 `n` 个整数。\n"
               "输出：置零后的矩阵，共 `m` 行，每行 `n` 个整数（空格分隔）。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    int m, n;\n"
            "    if (scanf(\"%d %d\", &m, &n) != 2) return 0;\n"
            "    static int a[205][205];\n"
            "    for (int i = 0; i < m; i++)\n"
            "        for (int j = 0; j < n; j++) scanf(\"%d\", &a[i][j]);\n"
            "    static int rz[205], cz[205];\n"
            "    for (int i = 0; i < m; i++)\n"
            "        for (int j = 0; j < n; j++)\n"
            "            if (a[i][j] == 0) { rz[i] = 1; cz[j] = 1; }\n"
            "    for (int i = 0; i < m; i++) {\n"
            "        for (int j = 0; j < n; j++) {\n"
            "            int v = (rz[i] || cz[j]) ? 0 : a[i][j];\n"
            "            printf(j ? \" %d\" : \"%d\", v);\n"
            "        }\n"
            "        printf(\"\\n\");\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": [
            "3 3\n1 1 1\n1 0 1\n1 1 1",
            "2 2\n1 2\n3 4",
            "2 3\n0 1 2\n3 4 5",
        ],
    },
    {
        "file": "fundamentals/fund-ch10/exercises.json",
        "title": "实现 LRU 页面置换并统计缺页次数",
        "io": ("输入：第一行两个整数 `capacity n`；第二行 `n` 个页面号（空格分隔）。\n"
               "输出：缺页（page fault）次数。"),
        "code": (
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            "    int cap, n;\n"
            "    if (scanf(\"%d %d\", &cap, &n) != 2) return 0;\n"
            "    static int pages[100005];\n"
            "    for (int i = 0; i < n; i++) scanf(\"%d\", &pages[i]);\n"
            "    int frame[1024], last[1024], used = 0, faults = 0;\n"
            "    for (int i = 0; i < n; i++) {\n"
            "        int p = pages[i], hit = -1;\n"
            "        for (int j = 0; j < used; j++)\n"
            "            if (frame[j] == p) { hit = j; break; }\n"
            "        if (hit >= 0) { last[hit] = i; continue; }\n"
            "        faults++;\n"
            "        if (used < cap) { frame[used] = p; last[used] = i; used++; }\n"
            "        else {\n"
            "            int victim = 0;\n"
            "            for (int j = 1; j < used; j++)\n"
            "                if (last[j] < last[victim]) victim = j;\n"
            "            frame[victim] = p; last[victim] = i;\n"
            "        }\n"
            "    }\n"
            "    printf(\"%d\\n\", faults);\n"
            "    return 0;\n"
            "}\n"
        ),
        "cases": [
            "3 20\n7 0 1 2 0 3 0 4 2 3 0 3 2 1 2 0 1 7 0 1",
            "3 5\n1 2 3 1 4",
            "1 4\n1 1 1 1",
        ],
    },
]


def _norm(t) -> str:
    return "".join(str(t or "").split())


def _find(items: list[dict], title: str) -> dict | None:
    key = _norm(title)
    for it in items:
        if _norm(it.get("title", "")).startswith(key):
            return it
    return None


def run_py(code: str, stdin: str) -> tuple[str, str | None]:
    """跑参考程序，返回 (stdout, 错误)。"""
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "sol.py"
        f.write_text(code, encoding="utf-8")
        try:
            p = subprocess.run(
                [PY, str(f)], input=stdin, capture_output=True, text=True,
                timeout=20, encoding="utf-8",
            )
        except subprocess.TimeoutExpired:
            return "", "超时"
    if p.returncode != 0:
        return p.stdout, (p.stderr or "").strip().split("\n")[-1][:200]
    return p.stdout, None


def run_cpp(code: str, stdin: str) -> tuple[str, str | None]:
    """编译并运行 C++ 参考程序，返回 (stdout, 错误)。"""
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / "sol.cpp"
        exe = pathlib.Path(td) / "sol.exe"
        src.write_text(code, encoding="utf-8")
        c = subprocess.run(
            [GPP, "-O2", "-std=c++17", "-o", str(exe), str(src)],
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace",
        )
        if c.returncode != 0:
            tail = (c.stderr or "").strip().split("\n")[-3:]
            return "", "编译失败: " + " | ".join(tail)[:300]
        try:
            p = subprocess.run(
                [str(exe)], input=stdin, capture_output=True, text=True,
                timeout=20, encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return "", "运行超时"
    if p.returncode != 0:
        return p.stdout, f"退出码 {p.returncode}"
    return p.stdout, None


def run_c(code: str, stdin: str) -> tuple[str, str | None]:
    """编译并运行 C 参考程序（gcc，C11），返回 (stdout, 错误)。"""
    with tempfile.TemporaryDirectory() as td:
        src = pathlib.Path(td) / "sol.c"
        exe = pathlib.Path(td) / "sol.exe"
        src.write_text(code, encoding="utf-8")
        c = subprocess.run(
            [GCC, "-O2", "-std=c11", "-o", str(exe), str(src)],
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace",
        )
        if c.returncode != 0:
            tail = (c.stderr or "").strip().split("\n")[-3:]
            return "", "编译失败: " + " | ".join(tail)[:300]
        try:
            p = subprocess.run(
                [str(exe)], input=stdin, capture_output=True, text=True,
                timeout=20, encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return "", "运行超时"
    if p.returncode != 0:
        return p.stdout, f"退出码 {p.returncode}"
    return p.stdout, None


ALL_PACK: list[tuple[dict, str]] = (
    [(p, "python") for p in PY_PACK + PY_PACK2]
    + [(p, "cpp") for p in CPP_PACK]
    + [(p, "c") for p in C_PACK]
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if args.restore:
        if not BACKUP.exists():
            print("无备份")
            return 1
        snaps = sorted(p for p in BACKUP.iterdir() if p.is_dir())
        if not snaps:
            print("备份为空")
            return 1
        snap = snaps[-1]
        n = 0
        for src in snap.rglob("exercises.json"):
            dst = CONTENT / src.relative_to(snap)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
        print(f"已从 {snap.name} 还原 {n} 个文件")
        return 0

    snap_dir = BACKUP / datetime.now().strftime("%Y%m%d-%H%M%S")
    touched: dict[pathlib.Path, dict] = {}
    ok, failed, missing = 0, [], []

    for p, lang in ALL_PACK:
        fp = CONTENT / p["file"]
        if not fp.exists():
            missing.append((p["file"], p["title"], "文件不存在"))
            continue
        data = touched.get(fp)
        if data is None:
            data = json.loads(fp.read_text(encoding="utf-8"))
            touched[fp] = data
        it = _find(data.get("items") or [], p["title"])
        if it is None:
            missing.append((p["file"], p["title"], "未匹配"))
            continue

        # ---- 1. 实跑生成期望值（先验证，再决定要不要写） ----
        runner = {"cpp": run_cpp, "c": run_c}.get(lang, run_py)
        cases, bad = [], None
        for i, cin in enumerate(p["cases"]):
            out, err = runner(p["code"], cin)
            if err:
                bad = f"case{i + 1} 运行失败: {err}"
                break
            if not out.strip():
                bad = f"case{i + 1} 输出为空"
                break
            cases.append({
                "input": cin,
                "expected_output": out.rstrip("\n"),
                "is_sample": i < 2,
            })
        if bad:
            failed.append((p["file"], p["title"], bad))
            continue

        # ---- 2. 写题面 I/O 约定（幂等） ----
        field = "stem_md" if it.get("stem_md") else "content_md"
        body = it.get(field) or ""
        if MARKER not in body:
            body = body.rstrip() + f"\n\n{MARKER}\n**判题 I/O 约定**（提交完整程序：从 stdin 读、向 stdout 写）\n\n{p['io']}"
            it[field] = body

        # ---- 3. 换参考实现 + 写用例 ----
        ans = it.setdefault("answer", {})
        ans["reference_code"] = p["code"]
        it["test_cases"] = cases
        ok += 1
        if args.verbose:
            print(f"  [ok] {p['file']} {p['title'][:26]} cases={len(cases)} first_out={cases[0]['expected_output'][:40]!r}")

    if args.apply:
        for fp, data in touched.items():
            snap_dir.mkdir(parents=True, exist_ok=True)
            bak = snap_dir / fp.relative_to(CONTENT)
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bak)
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n==== 统计 ====")
    print(f"  成功    {ok}")
    print(f"  失败    {len(failed)}")
    print(f"  未匹配  {len(missing)}")
    for f, t, why in failed + missing:
        print(f"    ! {f} {t} — {why}")
    if args.apply and ok:
        print(f"\n已写入。备份：{snap_dir}")
    elif not args.apply:
        print("\n(dry-run，未写入)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
