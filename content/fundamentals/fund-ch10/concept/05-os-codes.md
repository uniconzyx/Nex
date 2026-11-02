# fund-ch10 · 内存管理、文件与 IO 实战

> 把 §1–§4 的机制落成可模拟的最小例子。OS 的题往往是「算」和「排」，下面片段都能直接跑。

### 分页地址翻译（逻辑 → 物理）

逻辑地址 = 页号 + 页内偏移；用页表把页号换成页框号，偏移原样拼接。

```python
PAGE = 4096
logical = 0x2A3F
pno, off = logical // PAGE, logical % PAGE
frame = page_table[pno]          # 查页表
physical = frame * PAGE + off
```

### 页表项与多级页表

32 位地址、4KB 页、4 字节 PTE → 单级页表需 `2^20` 项 ≈ 4MB 常驻；二级页表只展开用到的目录项，省内存。

### LRU 页面置换模拟

维护访问栈，命中则提到栈顶，缺页则淘汰栈底。

```python
def lru(pages, cap):
    mem, faults = [], 0
    for p in pages:
        if p in mem:
            mem.remove(p); mem.append(p)
        else:
            if len(mem) == cap: mem.pop(0)
            mem.append(p); faults += 1
    return faults
print(lru([1,2,3,1,4,2,3], 3))   # 5 次缺页
```

### 银行家算法安全检查

对每进程记录 `Max`、`Allocation`，计算 `Need = Max − Allocation`；找 `Need ≤ Available` 的进程放行并回收，能全放行则安全。

### 磁盘调度（SCAN / LOOK）

SCAN 像电梯：磁头沿一个方向扫描，到端点才反向；LOOK 是「无请求即反向」的优化版，少走冤枉路。

### 文件分配（连续 / 链表 / 索引）

连续分配快但易碎片；链式分配无随机访问；索引分配（如 UNIX inode 的 12 直接 + 间接块）兼顾随机访问与灵活性。

### 空闲空间管理（位示图 / 成组链接）

位示图 O(1) 查询但元数据常驻内存；成组链接把空闲块自身当存储，省额外空间但每次分配要读盘。

### IO 控制方式（轮询 / 中断 / DMA）

轮询占 CPU；中断在完成后通知；DMA 让设备直接读写内存、只在起止时打扰 CPU，大幅降开销。

### 缓冲与 spooling

缓冲平滑生产/消费速度差；spooling 把独占设备（打印机）的「作业」排队进磁盘，变独占为共享。

### 虚拟文件系统 VFS 抽象

VFS 用统一 inode/文件操作接口屏蔽底层文件系统差异，上层 open/read 无需关心是 ext4 还是 NTFS。
