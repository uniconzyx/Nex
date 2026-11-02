# fund-ch11 · 网络分层与 TCP/IP 实战

> 把 §1–§4 的机制落成可计算/可模拟的片段。计网题重在「状态机」与「数」。

### 帧封装与 CRC 校验

发送方在帧尾补 `除数` 阶数的 0，模 2 除法得余数作 FCS；接收方整帧除以同一除数，余数为 0 则无错。

```python
def crc(data: int, poly: int) -> int:
    d = data << (poly.bit_length() - 1)
    while d.bit_length() >= poly.bit_length():
        shift = d.bit_length() - poly.bit_length()
        d ^= poly << shift
    return d
```

### 滑动窗口（GBN / SR）

GBN 只重传最早的未确认帧（累计确认），错误时整窗重传；SR 逐帧确认、只重传真正丢失的，带宽利用率高但接收方需缓存乱序帧。

### IP 分片与重组

总长度超 MTU 时按「片偏移（单位 8 字节）+ MF 标志」切分；重组在目的端按偏移拼回，任一片丢失则整包丢弃。

### 子网划分与 CIDR

`/26` 借 2 位主机位，每子网 62 可用地址；CIDR 用前缀聚合路由（`192.168.0.0/22` 覆盖 4 个 C 段）。

### TCP 三次握手状态迁移

`CLOSED → SYN_SENT → ESTABLISHED`（客户端）；`CLOSED → LISTEN → SYN_RCVD → ESTABLISHED`（服务端）。三次握手防历史连接请求建链。

### TCP 拥塞控制（慢启动 / 拥塞避免）

慢启动 `cwnd` 指数涨到 `ssthresh` 后转线性加性增；丢包（超时）则 `ssthresh=cwnd/2, cwnd=1`；快重传/快恢复只在重复 ACK 时降窗不归零。

### RTT 估计与 RTO 计算

`SRTT = (1−α)SRTT + α·Sample`（α=1/8），`RTTVAR = (1−β)RTTVAR + β·|SRTT−Sample|`（β=1/4），`RTO = SRTT + 4·RTTVAR`。重传段不采样（Karn 算法）。

### DNS 递归与迭代查询

主机→本地 DNS 是**递归**（本地必须给最终答案）；本地→根/TLD/权威是**迭代**（每级只给下一步线索）。

### HTTP 连接管理（keep-alive）

`Connection: keep-alive` 复用 TCP 省握手；`HTTP/2` 多路复用单连接并发流，进一步降延迟。

### 拥塞控制 vs 流量控制区别

流量控制是**接收方**防发送方压垮自己（滑动窗口/ rwnd）；拥塞控制是**网络**防 sender 压垮整网（cwnd）。二者乘起来是发送窗口上限。

### 真实场景：滑动窗口到底该设多大

凯喵在做文件传输，带宽 100Mbps、RTT 50ms。窗口太小吞吐上不去，太大则丢一帧重传整窗。经验下限是带宽时延积：

```python
bw = 100e6 / 8             # 12.5 MB/s
rtt = 0.05
print(round(bw * rtt, 4), "MB")   # 窗口至少这么大才填不满管道
```

### 真实场景：子网划分现场算

公司要切 4 个子网、每个 ≥ 50 台。借 2 位主机位得 `/26`，每子网 62 可用，用库一算就知道边界：

```python
import ipaddress
net = ipaddress.ip_network('192.168.1.0/24')
for s in net.subnets(prefixlen_diff=2):
    print(s, '可用', s.num_addresses - 2)
```
