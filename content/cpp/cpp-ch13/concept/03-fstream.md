# 03 · 文件流 fstream：打开模式、文件位置与文本/二进制

## 一、理论根基：fstream 是「流 + 文件缓冲区」的组合

`std::fstream` 继承自 `iostream`，底层绑定一个 `filebuf`（文件缓冲区）。它同时具备 `istream` 与 `ostream` 能力，打开模式决定其行为：

| 模式标志 | 含义 |
|---|---|
| `std::ios::in` | 读打开 |
| `std::ios::out` | 写打开 |
| `std::ios::app` | 每次写追加到末尾（不受 `seekp` 影响） |
| `std::ios::trunc` | 打开即清空（与 `out` 组合时默认隐含 trunc） |
| `std::ios::binary` | 二进制模式（禁用换行转换） |
| `std::ios::ate` | 打开后定位到末尾（可随后 `seekp` 回头写） |

> 关键陷阱：`fstream f("x", ios::out)` **默认 trunc**——会直接清空已有文件！若要「打开已有文件追加」必须显式 `ios::app`；若要「读写已有文件不破坏」用 `ios::in | ios::out` 且**不要**加 `trunc`。

## 二、实现机制：文件位置指针与文本/二进制差异

每个文件流有两个独立的**位置指针**：

- `tellg()` / `seekg(off, whence)`：读指针（get）。
- `tellp()` / `seekp(off, whence)`：写指针（put）。

在**纯输入或纯输出**流中二者通常合一；但在同时读写的 `fstream` 中，标准规定**在读转写或写转读之前必须做一次 seek 或 flush**，否则行为未定义——这是文件流随机读写的隐藏坑。

**文本 vs 二进制模式**的本质差异在换行符：
- 文本模式：Windows 上写入 `'\n'` 会被翻译成 `'\r\n'`（回车+换行），读出时反向翻译。这是为了兼容 C 文本文件约定。
- 二进制模式：字节原样读写，不做任何翻译。

> 第一性原理：**二进制模式保证「写进去的字节 == 读出来的字节」**。若用文本模式读写 `struct`（含 `'\n'`、`'\r'` 或值为 26 的字节），会发生翻译导致数据损坏——所以「存结构体」必须二进制模式。

## 三、工程实践：健壮的文件读写

1. **永远先 `is_open()` 再操作**：打开失败（权限/路径不存在）时流进入 `fail` 状态，盲目操作会静默失败。
2. **读写混合必须 seek 隔断**：见上文。
3. **`ifstream` 读文本逐行**：`std::getline(ifile, line)` 是最稳的逐行方式。
4. **二进制读写 struct**：用 `write(reinterpret_cast<const char*>(&obj), sizeof obj)` 与 `read(...)`；注意对齐/填充与跨平台字节序问题（仅同平台存档可接受）。

## 四、边界与陷阱

1. 忘记 `is_open()` 检查 → 打开失败后程序继续跑，得到空/错误结果。
2. 文本模式读写二进制数据 → 换行/EOF 字符被篡改，文件损坏。
3. `fstream` 同时读写未 seek 就换向 → 未定义行为。
4. `ofstream` 默认截断，误以为「打开即追加」。
5. 文件位置 `tellg()` 在文本模式下返回的是「抽象位置」，**不可用于计算字节偏移**（二进制模式才可靠）。

## 五、可运行示例：文本与二进制对比

```cpp
#include <iostream>
#include <fstream>
#include <string>
int main() {
    // 文本写读
    {
        std::ofstream out("demo.txt");
        out << "hello\nworld\n";           // 文本模式
    }
    std::ifstream in("demo.txt");
    std::string line;
    int n = 0;
    while (std::getline(in, line)) ++n;     // 正确：读到 EOF 自然结束
    std::cout << "文本行数=" << n << '\n';

    // 二进制写读一个 int 数组
    {
        std::ofstream bout("demo.bin", std::ios::binary);
        int a[3] = {10, 20, 30};
        bout.write(reinterpret_cast<const char*>(a), sizeof(a));
    }
    std::ifstream bin("demo.bin", std::ios::binary);
    int b[3];
    bin.read(reinterpret_cast<char*>(b), sizeof(b));
    std::cout << "二进制: " << b[0] << ' ' << b[1] << ' ' << b[2] << '\n';
}
```

**输出**：
```
文本行数=2
二进制: 10 20 30
```
> 观察点：① `getline` 循环以「提取失败（EOF）」为自然结束，不要写成 `while(!in.eof())`；② 二进制模式 `write`/`read` 保证字节一致，适合存档结构化数据。

---

## 三视角解析

### 🧑‍💻 程序员视角
- **打开文件后必判 `is_open()`**（或直接判流状态），否则后续操作静默失败、白忙一场。
- 文本模式 vs 二进制模式：Windows 下文本模式会把 `\n` 转成 `\r\n`，**读写二进制数据必须加 `ios::binary`**，否则文件损坏。
- RAII 优势：`fstream` 析构自动 `close` 并 `flush`；但仍要**显式检查关闭/写入状态**，因为写入失败可能延迟到 flush 时才可见。

### 🎓 博士生视角
- fstream 建立在 `filebuf` 上，`filebuf` 又封装了底层的 `open/read/write/lseek` 系统调用；流的 seek 是**逻辑位置**，缓冲的存在使「逻辑位置」与「内核文件偏移」可能不同步（需要 flush 或 seek 触发同步）。
- 文本模式的换行转换发生在**缓冲层**（filebuf 的 codecvt），因此是**逐字节重写**，不是解析——这也解释了它为什么在二进制数据上会造成损坏。
- 打开模式是**位掩码组合**（`in|out|app|trunc|binary|ate`），其中 `app` 强制每次写入定位到末尾（原子语义），`trunc` 会**清空**已有内容——误用 `out` 单独打不开会隐式创建。

### 📚 考研者视角
- 记忆锚点：**二进制读写必须 `ios::binary`**（Windows 换行转换会破坏数据）。
- 常考辨析：`ios::out` 单独使用会**截断文件**；要「追加」需 `ios::app`；要「既要读又要写」需 `in|out`。
- 与 OS 对照：文件位置指针（逻辑）vs 内核文件偏移（物理）——与 `lseek`、文件描述符的「当前偏移」是同一概念。

---
