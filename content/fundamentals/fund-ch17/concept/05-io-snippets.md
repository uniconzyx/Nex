# I/O 系统代码速查：凯喵的七段可直接对照的片段

> 这一篇是配套速查。前四篇讲清了 I/O 接口、四种控制方式、中断响应与 DMA，这一篇把它们落成「能算出来、能看到现象」的代码。凯喵的用法是：先看公式，再跑模拟，最后对照真实系统的数字。

## 一、四种 I/O 方式的耗时对比模型

同一个 I/O 请求，在四种方式下的 CPU 时间差别是数量级的。

```python
def query_io(dev_ms, check_us=1.0):
    """程序查询：CPU 全程轮询"""
    return dev_ms * 1000.0          # 返回 CPU 占用微秒

def interrupt_io(dev_ms, isr_us=5.0):
    """中断：CPU 只在搬运时介入"""
    return isr_us

def dma_io(dev_ms, setup_us=10.0, blocks=1):
    """DMA：只在启动与结束时介入"""
    return setup_us + 2.0           # 启动 + 中断收尾

def compare(dev_ms=5.0):
    print(f"查询 {query_io(dev_ms):.0f}us | 中断 {interrupt_io(dev_ms):.0f}us | "
          f"DMA {dma_io(dev_ms):.0f}us")
```

以磁盘一次 5ms 的读为例：查询方式要占满 5000us 的 CPU，中断方式只要 5us，DMA 约 12us。这个对比就是「为什么大数据量传输必须用 DMA」的量化依据。

## 二、中断响应时间的分解

中断响应时间不是「一个数字」，而是四段之和。

```python
def interrupt_latency(close_us, save_us, vector_us, isr_entry_us):
    return close_us + save_us + vector_us + isr_entry_us

print(interrupt_latency(0.02, 0.10, 0.30, 0.50))   # 约 0.92us
```

四段分别是：**关中断时间**（当前指令执行完才能响应）、**保存现场**（PSW/PC 入栈）、**取中断向量**（查表跳到 ISR）、**ISR 前导**（保存寄存器）。答题时把这四段写出来，比笼统说「很短」更得分。

## 三、DMA 与 CPU 争用总线的三种模式

```text
停止 CPU 访存：DMA 独占总线，CPU 完全停下    ← 快但 CPU 停滞
周期挪用：DMA 只在需要时抢一个周期          ← 主流
交替访问：CPU 与 DMA 分时使用总线            ← 硬件成本高
```

周期挪用的代价可以量化：如果 DMA 每传一个字要走一次总线，而 CPU 的访存需求是每 5 个周期一次，那么 DMA 最多占用 20% 的总线带宽，CPU 性能下降约 20%。这就是「DMA 也有代价」的具体数字。

## 四、I/O 端口的编址方式对照

```text
统一编址（内存映射 I/O）：I/O 寄存器占内存地址空间
  优点：可用全部访存指令，寻址方式多
  缺点：占用内存地址空间，指令无法区分是访存还是 I/O

独立编址（I/O 映射 I/O）：单独的 I/O 地址空间 + 专用指令
  优点：不占内存空间，程序易区分
  缺点：指令少（只能 load/store 到端口），寻址方式受限
```

x86 是独立编址（`in`/`out` 指令），ARM 是统一编址（像访问内存一样访问外设寄存器）。这个差异会体现在「写驱动时的寄存器访问方式」上。

## 五、用 Python 模拟轮询与中断的 CPU 占用

```python
import time

def poll_until(ready_fn, timeout=1.0):
    t0 = time.perf_counter()
    while not ready_fn():
        if time.perf_counter() - t0 > timeout:
            raise TimeoutError
    return time.perf_counter() - t0

def check_after(delay, ready_fn):
    time.sleep(delay)          # 相当于 CPU 去干别的事
    return ready_fn()
```

第一版把 CPU 时间全花在检查上，第二版把等待时间让出去。这个对比在小脚本里不明显，但在「每秒要处理上千个请求」的服务里就是吞吐量的差别——这就是 epoll/kqueue 相对轮询的价值。

## 六、磁盘 I/O 的排队模型（Little 定律）

```python
def avg_queue_len(arrival_rate, service_time):
    """L = λW；服务时间均匀分布时 W = Q/(1-ρ)"""
    rho = arrival_rate * service_time
    if rho >= 1:
        return float("inf")     # 队列不稳定
    w = service_time / (1 - rho)
    return arrival_rate * w
```

`ρ`（利用率）趋近 1 时队列长度爆炸——这就是「磁盘利用率到 90% 就慢得不像话」的数学原因。工程上的经验阈值是「利用率不超过 70%」，超过就该考虑扩容或分片。

## 七、中断嵌套与中断屏蔽字

```text
四级中断 A(高) > B > C > D(低)，屏蔽字决定谁能打断谁
A 的屏蔽字：1 1 1 1   （全屏蔽，不被打断）
B 的屏蔽字：0 1 1 1   （只允许 A 打断）
C 的屏蔽字：0 0 1 1   （允许 A、B 打断）
D 的屏蔽字：0 0 0 1   （允许 A、B、C 打断）
```

注意「屏蔽」的方向：某级中断的屏蔽字里，1 表示屏蔽（不允许它打断我），0 表示开放。写反了整道题就废。凯喵的记法是：**屏蔽字是「我允许谁打断我」的否定**。

## 收尾

这七段内容覆盖了 I/O 系统里最能拉开分差的几处：四种方式的量化对比、中断响应时间的四段分解、DMA 的总线争用代价、编址方式的取舍、轮询与事件驱动的本质差别、排队模型的容量判断、以及中断屏蔽字的方向。凯喵的体会是，这一章的知识点本身不难，难在「把定性描述变成定量判断」——一旦你能算出「查询方式要占 5000us、DMA 只要 12us」，很多选择题就不用背了，因为它变成了常识。
