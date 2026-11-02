# 性能速查：把「对齐 / 缓存 / 内联」写成能跑的代码

> 这一章的三件事——**对齐**（对象怎么摆）、**缓存**（数据怎么排）、**内联**（调用怎么省）——
> 都能用几十行代码验证。本节把三者的最小可复现实验放在一起：
> 先用 `offsetof` / `sizeof` 把 padding 算出来，再用一个计数器演示**伪共享**，
> 最后用 AoS/SoA 对比说明「同样的逻辑，换个数据排布差多少」。
> 面试里被问「你怎么做性能优化」，能当场写出这三段，比背十个名词有说服力。

### 一、对齐与 padding：先把内存账算清楚

结构体的每个成员按**自身对齐要求**（`alignof`）落在合适偏移上，成员之间会插 padding，
整个结构体大小还要补齐到自身对齐的整数倍。用 `offsetof` 直接量，比推测可靠。

```cpp
#include <cstddef>
#include <cstdio>

struct Plain {          // 三个 int：连续，没有 padding
    int a, b, c;
};

struct Mixed {          // char + int：中间要补 3 字节
    char tag;
    int  value;
};

struct Reordered {      // 调整顺序后 padding 消失
    int  value;
    char tag;
};

template <class T>
void report(const char* name) {
    std::printf("%-10s size=%2zu align=%2zu\n", name, sizeof(T), alignof(T));
}

int main() {
    report<Plain>("Plain");
    report<Mixed>("Mixed");
    report<Reordered>("Reordered");
    std::printf("offset(value) in Mixed = %zu\n", offsetof(Mixed, value));
    std::printf("offset(tag)   in Mixed = %zu\n", offsetof(Mixed, tag));
    return 0;
}
```

规律一句话：**成员按对齐要求从大到小排列，padding 最少**；`sizeof` 一定是对齐的整数倍，
所以数组 `new Plain[n]` 的每一步都落在缓存行边界上，不会出现"跨行半写"。

### 二、伪共享：两个计数器共处一条缓存行

多核下缓存行（常见 64 字节）是**一致性单位**：两个线程各自改同一行里的不同变量，
核心之间仍要来回失效/转移这条缓存行，性能掉得比加锁还惨——这就是伪共享。

```cpp
#include <cstdio>
#include <thread>
#include <vector>
#include <chrono>

struct PaddedCounter {          // 独占一整条缓存行
    long long value = 0;
    char        pad[64 - sizeof(long long)];   // 典型 64B 对齐
};

struct SharedCounter {          // 与相邻计数器共享同一行
    long long value = 0;
};

template <class T>
long long hammer(int threads, int loops) {
    std::vector<T> counters(threads);
    std::vector<std::thread> pool;
    for (int i = 0; i < threads; i += 1) {
        pool.emplace_back([&, i] {
            for (int k = 0; k < loops; k += 1) counters[i].value += 1;
        });
    }
    for (auto& t : pool) t.join();
    long long sum = 0;
    for (auto& c : counters) sum += c.value;
    return sum;
}

int main() {
    constexpr int N = 4, LOOPS = 20'000'000;
    auto t0 = std::chrono::steady_clock::now();
    hammer<SharedCounter>(N, LOOPS);
    auto t1 = std::chrono::steady_clock::now();
    hammer<PaddedCounter>(N, LOOPS);
    auto t2 = std::chrono::steady_clock::now();
    auto ms = [](auto a, auto b) {
        return std::chrono::duration_cast<std::chrono::milliseconds>(b - a).count();
    };
    std::printf("shared=%lld ms, padded=%lld ms\n", ms(t0, t1), ms(t1, t2));
    return 0;
}
```

结论很直接：**热点计数器必须独占缓存行**（`alignas(64)` 或加 padding）。
这是无锁队列、计数器、状态标志位（`atomic<bool>` 挤在一起）最常见的性能陷阱。

### 三、AoS 与 SoA：同样的算法，换个排布差几倍

面向对象把"每个对象的字段排在一起"（AoS），数据分析却更吃"同一种字段排在一起"（SoA）：
后者遍历一个字段时访存是**连续的**，还能自动向量化。

```cpp
#include <cstdio>
#include <vector>
#include <chrono>

struct ParticleAoS { float x, y, z; float charge; };

struct ParticleSoA {
    std::vector<float> x, y, z, charge;
};

float sumZ_AoS(const std::vector<ParticleAoS>& p) {
    float s = 0;
    for (const auto& q : p) s += q.z;      // 每 16 字节才取 4 字节
    return s;
}

float sumZ_SoA(const ParticleSoA& p) {
    float s = 0;
    for (std::size_t i = 0; i < p.z.size(); i += 1) s += p.z[i];  // 连续访问
    return s;
}

int main() {
    constexpr int N = 2'000'000;
    std::vector<ParticleAoS> aos(N);
    ParticleSoA soa;
    soa.x.resize(N); soa.y.resize(N); soa.z.resize(N); soa.charge.resize(N);
    for (int i = 0; i < N; i += 1) { aos[i] = {1, 2, 3, 4}; soa.z[i] = 3; }

    auto t0 = std::chrono::steady_clock::now();
    float a = sumZ_AoS(aos);
    auto t1 = std::chrono::steady_clock::now();
    float b = sumZ_SoA(soa);
    auto t2 = std::chrono::steady_clock::now();
    auto ms = [](auto x, auto y) {
        return std::chrono::duration_cast<std::chrono::milliseconds>(y - x).count();
    };
    std::printf("sum=%.0f/%.0f  AoS=%lld ms  SoA=%lld ms\n",
                a, b, ms(t0, t1), ms(t1, t2));
    return 0;
}
```

```text
AoS 布局（每 16B 一颗粒子，取 z 要跨 3 次）
┌──────────┬──────────┬──────────┬──────────┐
│ x y z q  │ x y z q  │ x y z q  │ x y z q  │   ← 扫描 z 时 75% 的带宽被浪费
└──────────┴──────────┴──────────┴──────────┘
SoA 布局（同字段连成一条线，取 z 连续命中）
┌──────────┬──────────┬──────────┬──────────┐
│ z z z z  │ q q q q  │ y y y y  │ x x x x  │   ← 一条 cache line 全是 z
└──────────┴──────────┴──────────┴──────────┘
```

### 四、内联与去虚拟化：让「调用」不再是一笔开销

`inline` 只是给编译器的**建议**：它把调用点直接展开成函数体，省掉压栈/跳转；
若函数体太大反而更慢（代码膨胀、指令缓存失效）。虚函数的调用则**必然**经过一次间接跳转，
热点路径上可以用**去虚拟化**（把最终类型已知的多态对象换成具体类型调用）省掉它。

```cpp
#include <cstdio>
#include <vector>

struct Shape {
    virtual ~Shape() = default;
    virtual double area() const = 0;
};
struct Circle : Shape {
    double r;
    explicit Circle(double radius) : r(radius) {}
    double area() const override { return 3.14159265358979 * r * r; }
};
struct Square : Shape {
    double s;
    explicit Square(double side) : s(side) {}
    double area() const override { return s * s; }
};

double totalVirtual(const std::vector<Shape*>& shapes) {
    double s = 0;
    for (const auto* sh : shapes) s += sh->area();   // 每次一次间接跳转
    return s;
}

double totalDevirtualized(const std::vector<Shape*>& shapes) {
    double s = 0;
    for (const auto* sh : shapes) {
        if (const auto* c = dynamic_cast<const Circle*>(sh)) s += c->area();  // 已知具体类型
        else s += sh->area();
    }
    return s;
}

int main() {
    std::vector<Shape*> shapes{ new Circle(2.0), new Square(3.0), new Circle(1.5) };
    std::printf("virtual=%.3f devirtualized=%.3f\n",
                totalVirtual(shapes), totalDevirtualized(shapes));
    return 0;
}
```

工程结论：**先量再优化**。`perf stat` 看分支/缓存未命中，用真实负载的耗时差说话；
凭直觉改布局，十次里有九次是白忙。

## 三视角解析
### 🧑‍💻 程序员视角
两个线程各自频繁写一个计数器，即使它们毫无逻辑关系，只要这两个计数器落在同一条 64 字节缓存行上，就会因为缓存一致性协议反复失效对方的行——这叫伪共享，实测能差 5~10 倍。解法是加 `alignas(64)` 或用填充把二者分开。AoS（结构体数组）与 SoA（数组结构体）的差别也是实测级的：只遍历其中一个字段时，SoA 的缓存利用率高得多。`inline` 与去虚拟化同样有前提——虚函数调用要能被证明「目标唯一」才可能内联。

### 🎓 博士生视角
伪共享的根因是「缓存一致性以行为单位」：MESI 协议下，一个核写某行会让其他核的副本失效，哪怕只改了一个字节。这使「逻辑上独立」的变量在物理上耦合。对齐（alignment/padding）是编译器按「最大成员对齐数」插入填充的结果，理解它才能算清结构体大小（`sizeof` 不等于成员之和）。SoA 的优势来自「按访问模式组织内存」，这也是列式数据库（Parquet/Arrow）与 GPU 编程的基本设计原则。

### 📚 考研者视角
面试与实战：
1. **结构体大小计算**：按最大成员对齐、每个成员偏移是其对齐数的倍数、总大小是最大对齐数的倍数。
2. **`#pragma pack` 与 `alignas`**：前者压缩对齐（牺牲访问效率），后者提高对齐（用于 SIMD/Cache）。
3. **伪共享的识别与消除**：per-thread 计数器 + padding。
4. **AoS vs SoA**：按「访问是否只涉及部分字段」选择。
