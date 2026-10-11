# 04 · 传输层：TCP 连接管理、可靠传输与拥塞控制

## 一、TCP 首部（20 B 固定 + 可选项）

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          源端口(16)           |         目的端口(16)          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        序号 seq(32)                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      确认号 ack(32)                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| 数据偏移(4)|保留(6)|U|A|P|R|S|F|        窗口 win(16)          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         校验和(16)            |        紧急指针(16)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    选项（含 MSS、窗口扩大、SACK）              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**六个标志位（背口诀 UAPRSF）**：
- **URG**：紧急指针有效（几乎不用）
- **ACK**：确认号有效（**连接建立后所有报文都必须置 1**）
- **PSH**：接收方应立即上交应用层（而非缓存）
- **RST**：重置连接（被拒/异常终止）
- **SYN**：同步序号，用于建立连接
- **FIN**：发送方数据发完，请求关闭

**关键字段**：
- **序号 seq**：本报文段**数据第一个字节**的编号（**SYN 和 FIN 也各占一个序号**）。
- **确认号 ack**：**期望收到的下一个字节的编号**（即「已收到 `ack−1` 之前的所有字节」）。**累积确认**。
- **窗口 win**：**接收窗口 rwnd**，即「我还能收多少字节」，用于**流量控制**。

## 二、三次握手与四次挥手

**三次握手**（客户端主动）：

| # | 方向 | 标志 | seq | ack | 客户端状态 | 服务端状态 |
|---|---|---|---|---|---|---|
| 1 | C→S | **SYN=1** | `x` | — | SYN_SENT | — |
| 2 | S→C | **SYN=1, ACK=1** | `y` | `x+1` | — | SYN_RCVD |
| 3 | C→S | **ACK=1** | `x+1` | `y+1` | ESTABLISHED | ESTABLISHED |

**为什么是三次不是两次？** 因为**双向**都要确认对方的「发送能力 + 接收能力」。三次能防止**历史失效的连接请求**到达服务端后建立无用连接（若是两次，服务端单方面认为连接建立，会白白占用资源等待一个永远不会来的客户端）。

**四次挥手**（客户端主动关闭）：

| # | 方向 | 标志 | seq | ack | 说明 |
|---|---|---|---|---|---|
| 1 | C→S | **FIN=1, ACK=1** | `u` | `v` | 客户端数据发完 |
| 2 | S→C | **ACK=1** | `v` | `u+1` | 服务端确认（此时**半关闭**） |
| 3 | S→C | **FIN=1, ACK=1** | `w` | `u+1` | 服务端数据也发完了 |
| 4 | C→S | **ACK=1** | `u+1` | `w+1` | 客户端确认；等 **2MSL** 后关闭 |

**为什么挥手是四次而握手是三次？** 因为**TCP 是全双工**，一方发完数据（FIN）**不代表另一方也发完了**。服务端的 ACK 与 FIN **不能合并**（它可能还有数据要发）。**若服务端也没数据要发，第 2、3 步常合并为一次**（所以抓包有时看到三次）。

**TIME_WAIT 为什么要等 2MSL？**
1. **保证最后一个 ACK 能到达**：若 ACK 丢失，服务端会重传 FIN，客户端在 TIME_WAIT 内还能重发 ACK；
2. **让本次连接的旧报文段在网络中消亡**，避免被后续「同四元组」的新连接误收。

## 三、可靠传输与 RTT 估计

**可靠传输的四个机制**：**序号**（标记字节流位置）、**确认（累积）**、**超时重传**、**校验和**。

**RTT 估计（Jacobson/Karels，必考）**：
$$
\text{RTT}_S \leftarrow (1-\alpha)\,\text{RTT}_S + \alpha \cdot \text{RTT}_{\text{new}}, \quad \alpha = 1/8
$$
$$
\text{RTT}_D \leftarrow (1-\beta)\,\text{RTT}_D + \beta \cdot |\text{RTT}_{\text{new}} - \text{RTT}_S|, \quad \beta = 1/4
$$
$$
\text{RTO} = \text{RTT}_S + 4\,\text{RTT}_D
$$

**Karn 算法**：**重传的报文段不用于 RTT 采样**（否则无法判断 ACK 对应的是哪次发送，会导致 RTT 估计混乱）。

**快速重传（Fast Retransmit）**：收到**三个重复 ACK**（duplicate ACK）即认为该段丢失，**不等超时**立即重传。这比等 RTO 快得多。

## 四、流量控制与拥塞控制

**流量控制**：由接收方的 `rwnd` 限制发送方。
- **零窗口**：`rwnd = 0` 时发送方停止发送，并启动**持续计时器（persist timer）**周期性发**零窗口探测**，避免「双方互等死锁」。
- **糊涂窗口综合征（SWS）**：接收方每次只腾出一点点空间就通告，导致发送方发**极小的报文段**。**对策**：接收方等窗口 ≥ `min(MSS, 缓冲区一半)` 再通告（**Clark 算法**）；发送方用 **Nagle 算法**合并小数据。

**拥塞控制**：由发送方根据网络状况调整 **cwnd**（拥塞窗口）。实际发送窗口：
$$
\text{swnd} = \min(\text{cwnd}, \text{rwnd})
$$

**四个阶段（Reno）**：

| 阶段 | 条件 | cwnd 变化 |
|---|---|---|
| **慢启动** | `cwnd < ssthresh` | **每收到一个 ACK，cwnd += 1 MSS** ⇒ **每 RTT 翻一倍**（指数增长） |
| **拥塞避免** | `cwnd ≥ ssthresh` | **每 RTT，cwnd += 1 MSS**（线性增长，加法增大 AI） |
| **快重传** | 收到 3 个重复 ACK | 立即重传丢失段 |
| **快恢复** | 快重传后 | `ssthresh = cwnd/2`，`cwnd = ssthresh`，**直接进拥塞避免**（不回慢启动） |

**超时 vs 三个重复 ACK 的区别（关键）**：
- **超时**：`ssthresh = cwnd/2`，`cwnd = 1`，**回到慢启动**（最严厉的惩罚，因为超时意味着网络可能严重拥塞）；
- **三个重复 ACK**：`ssthresh = cwnd/2`，`cwnd = ssthresh`，**进入快恢复/拥塞避免**（较轻，因为还能收到 ACK 说明网络没完全瘫痪）。

**这就是「AIMD（加法增大、乘法减小）」**：加法增大保证公平共享带宽，乘法减小时快速退让。

**现代算法**：**CUBIC**（用三次函数代替线性增长，高带宽长时延网络下更激进）、**BBR**（基于**带宽与最小 RTT 的测量**建模，不把丢包当唯一拥塞信号，在有一定丢包的链路上显著优于 CUBIC）。

## 五、UDP 与 QUIC

**UDP 首部只有 8 B**：源端口、目的端口、长度、校验和。**无连接、不可靠、无序、无流量/拥塞控制**。

**适用场景**：DNS（短查询，一次往返搞定）、DHCP、SNMP、RIP、实时音视频（**宁丢不缓**）、QUIC/HTTP3、游戏。

**QUIC 为什么在用户态重建可靠传输**：
1. **绕过内核升级**：QUIC 跑在 **UDP 之上**，协议更新只需改用户态程序，不必升级操作系统内核；
2. **消除队头阻塞**：TCP 是单一字节流，一个包丢失会阻塞后续所有数据；QUIC 的**流是独立的**，一个流失序不影响其他流；
3. **0-RTT 建连**：把 TLS 1.3 握手与连接建立合并，重复连接可 0-RTT 发数据；
4. **连接迁移**：用 **Connection ID** 而非四元组标识连接，切换网络（WiFi→4G）不断连。

## 六、可运行代码：握手序号演算与拥塞窗口演化

```python
print("=== three-way handshake sequence arithmetic ===")
c_seq, s_seq = 1000, 5000
print(f"  client ISN x = {c_seq}, server ISN y = {s_seq}")
print(f"  1) C -> S  SYN=1        seq={c_seq}            (SYN consumes 1 seq)")
print(f"  2) S -> C  SYN=1,ACK=1  seq={s_seq}  ack={c_seq+1}")
print(f"  3) C -> S  ACK=1        seq={c_seq+1}  ack={s_seq+1}")
print(f"  both ESTABLISHED; next data seq: client={c_seq+1}, server={s_seq+1}")
print("  SYN and FIN each consume one sequence number")

print()
print("=== four-way teardown ===")
u, v, w = 2000, 6000, 9000
print(f"  1) C -> S  FIN=1,ACK=1  seq={u}   ack={v}")
print(f"  2) S -> C  ACK=1               ack={u+1}   (half-closed: C cannot send)")
print(f"  3) S -> C  FIN=1,ACK=1  seq={w}   ack={u+1}")
print(f"  4) C -> S  ACK=1               ack={w+1}   then TIME_WAIT 2*MSL")

print()
print("=== Reno congestion control (cwnd in MSS) ===")
cwnd, ssthresh = 1.0, 8.0
print(f"  initial: cwnd={cwnd:g} ssthresh={ssthresh:g}")
round_no = 0
history = []
while round_no < 12:
    round_no += 1
    if cwnd < ssthresh:
        phase = "slow-start (x2)"
        cwnd = min(cwnd * 2, ssthresh) if cwnd * 2 > ssthresh else cwnd * 2
    else:
        phase = "congestion-avoid (+1)"
        cwnd = cwnd + 1
    history.append((round_no, cwnd, phase))
    print(f"  RTT {round_no:>2}: cwnd={cwnd:>5.0f}  [{phase}]")
    if cwnd >= 12 and phase.startswith("congestion"):
        print(f"  --- packet loss at cwnd={cwnd:g} ---")
        ssthresh = cwnd / 2
        print(f"  triple duplicate ACK -> fast recovery: ssthresh={ssthresh:g}, cwnd={ssthresh:g} (NO slow-start)")
        cwnd = ssthresh
        break

print()
print("=== timeout vs 3-dup-ACK punishment ===")
for c in (16.0,):
    print(f"  cwnd={c:g}: timeout  -> ssthresh={c/2:g}, cwnd=1   (back to slow-start)")
    print(f"  cwnd={c:g}: 3 dupACK -> ssthresh={c/2:g}, cwnd={c/2:g} (fast recovery, avoid)")
```

## 三视角解析

### 🧑‍💻 程序员视角
- **`TIME_WAIT` 堆积是线上最常见的「端口耗尽」原因**：短连接服务（HTTP/1.0、大量 RPC）会把本机端口用光，报 `Cannot assign requested address`。**对策**：① 改用长连接/连接池；② `net.ipv4.tcp_tw_reuse=1`（**仅对出向连接安全**）；③ 扩大 `ip_local_port_range`。**绝不建议开 `tcp_tw_recycle`**（在 NAT 环境下会丢包，Linux 4.12 已移除）。
- **`CLOSE_WAIT` 堆积是代码 bug**：说明**本进程没调用 `close()`**。看到大量 `CLOSE_WAIT` 先查代码里是不是有分支忘了关流（常见于异常路径）。**`TIME_WAIT` 多通常是设计问题，`CLOSE_WAIT` 多一定是代码问题。**
- **Nagle + 延迟 ACK 的经典互等**：Nagle 等 ACK 才发下一个包，延迟 ACK 等数据才发 ACK ⇒ **最多 40 ms 的延迟**。Redis、RPC 框架默认开 `TCP_NODELAY` 就是为了避开这个坑。
- **`ss -s` / `ss -tan state time-wait`** 是最快的排查姿势；`netstat` 在大连接数下会很慢（要遍历 `/proc`）。

### 🎓 博士生视角
- **拥塞控制的本质是「分布式资源分配的在线优化」**：`AIMD` 是**唯一被证明能收敛到公平且高效的**（Chiu & Jain 1989）控制律——加法增大保证效率，乘法减小保证公平。**它的稳态是锯齿形（sawtooth）**，因为必须持续探测带宽上限。
- **RTT 估计是「在线参数估计」**：`RTT_S` 是一阶低通滤波（指数加权移动平均），`RTT_D` 是平均绝对偏差（近似标准差）。`RTO = RTT_S + 4·RTT_D` 相当于**均值 + 4σ 的上分位点**，使超时概率很低。**这是统计学直接嵌入协议设计的典范。**
- **BBR 的范式转变**：CUBIC/Reno 把**丢包**当拥塞信号（loss-based），在**浅缓冲区（shallow buffer）**网络里会过早降速，而在**深缓冲区**网络里会造成 **bufferbloat**（排队时延爆炸）。BBR 改为测量 **BtlBw（瓶颈带宽）与 RTprop（最小 RTT）**，用二者的乘积估计 **BDP**，本质上是把「拥塞控制」重写为「**带宽-时延积的在线估计**」。**代价是与 loss-based 流量共存时的公平性问题**（BBR 会挤占 CUBIC 的带宽）。
- **QUIC 的「用户态传输」是对「分层与端到端」原则的重新权衡**：传统上传输层在内核（OSI 的传输层职责），但内核更新周期以年计，而 Web 协议以月计。QUIC 把可靠性、拥塞控制、加密**全部搬到用户态**，代价是**重复实现 + 用户态开销**，收益是**可快速演进 + 消除队头阻塞**。**这是「架构分层」与「演进速度」冲突时的实际选择。**

### 📚 考研者视角
- **408 传输层必考**：① **三次握手/四次挥手**（画报文序列、写 `seq`/`ack`、标明状态迁移）② **`TIME_WAIT` 等 2MSL 的两个理由** ③ **可靠传输**（序号、累积确认、超时重传、**快速重传的三个重复 ACK**）④ **流量控制**（`rwnd`、零窗口、SWS）⑤ **拥塞控制**（**慢启动指数、拥塞避免线性、AIMD、超时 vs 三重复 ACK 的不同处置**）⑥ **RTT 估计公式与 Karn 算法**。
- **序号演算题的规范**：记清 **`seq` 是本报文段第一个数据字节的编号**，**`ack` 是期望收到的下一个字节编号**。**SYN 和 FIN 各消耗一个序号**（这是最容易错的细节）。
- **「超时」与「三个重复 ACK」的处置差异是必考**：超时 → `ssthresh = cwnd/2`，`cwnd = 1`，**回慢启动**；三个重复 ACK → `ssthresh = cwnd/2`，`cwnd = ssthresh`，**快恢复（不回慢启动）**。**写反了就是 0 分。**
- **流量控制 vs 拥塞控制的区别（标准问法）**：流量控制是**端到端**的（接收方能力），用 `rwnd`；拥塞控制是**面向网络**的（链路与路由器），用 `cwnd`。**实际窗口取两者较小值**。
- **常考数值**：TCP 首部最少 **20 B**，UDP 首部 **8 B**；`RTO = RTT_S + 4·RTT_D`；初始 `ssthresh` 常见为 16（或考生自己按题目给）。
- 记忆锚点：**「三次握手为双向确认、四次挥手因半关闭」**、**「TIME_WAIT 2MSL：保 ACK 送达 + 让旧包消亡」**、**「AIMD：加法增大、乘法减小」**、**「超时回慢启动、三个重复 ACK 进快恢复」**、**「UDP 首部 8 字节」**。
