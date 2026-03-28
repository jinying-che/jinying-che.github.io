---
title: "TCP"
date: 2021-02-01T23:25:26+08:00
tags: ["network"]
description: "TCP overview"
---

TCP is really complex protocol and there's a lot of tutorials online to learn TCP, however as time being, it's probably being outdated, same as my post. Hence I would recommend the official [RFC 793](https://datatracker.ietf.org/doc/html/rfc793#autoid-16) as the only true source. Here's a summary of [RFC 793](https://datatracker.ietf.org/doc/html/rfc793#autoid-16).

### TCP Header
[TCP Header Format](https://datatracker.ietf.org/doc/html/rfc793#autoid-16)
```
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |          Source Port          |       Destination Port        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                        Sequence Number                        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    Acknowledgment Number                      |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |  Data |           |U|A|P|R|S|F|                               |
   | Offset| Reserved  |R|C|S|S|Y|I|            Window             |
   |       |           |G|K|H|T|N|N|                               |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |           Checksum            |         Urgent Pointer        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    Options                    |    Padding    |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                             data                              |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### TCP Flags

| Flag | Name | Purpose |
|------|------|---------|
| **SYN** | Synchronize | Initiate connection, synchronize sequence numbers |
| **ACK** | Acknowledge | Confirm receipt — present on virtually every packet after initial SYN |
| **FIN** | Finish | Graceful close of one direction — "I'm done sending" |
| **RST** | Reset | Abort immediately — force-kill from any state to CLOSED, no handshake |
| **PSH** | Push | Deliver to application immediately, don't buffer |
| **URG** | Urgent | Process before other buffered data, uses Urgent Pointer field |

Common combinations:

| Combination | Meaning |
|-------------|---------|
| `SYN` | Connection open request |
| `SYN+ACK` | Connection open accepted |
| `ACK` | Acknowledge / data transfer |
| `PSH+ACK` | Data delivery — flush to app now |
| `FIN+ACK` | Graceful close — "I'm done sending" |
| `RST` | Abort connection |

### TCP State Machine
Be noted that 11 [TCP Connection States Diagram](https://datatracker.ietf.org/doc/html/rfc793#autoid-17) indicating state to state transformation not cliet to server communication.

```



                              +---------+ ---------\      active OPEN
                              |  CLOSED |            \    -----------
                              +---------+<---------\   \   create TCB
                                |     ^              \   \  snd SYN
                   passive OPEN |     |   CLOSE        \   \
                   ------------ |     | ----------       \   \
                    create TCB  |     | delete TCB         \   \
                                V     |                      \   \
                              +---------+            CLOSE    |    \
                              |  LISTEN |          ---------- |     |
                              +---------+          delete TCB |     |
                   rcv SYN      |     |     SEND              |     |
                  -----------   |     |    -------            |     V
 +---------+      snd SYN,ACK  /       \   snd SYN          +---------+
 |         |<-----------------           ------------------>|         |
 |   SYN   |                    rcv SYN                     |   SYN   |
 |   RCVD  |<-----------------------------------------------|   SENT  |
 |         |                    snd ACK                     |         |
 |         |------------------           -------------------|         |
 +---------+   rcv ACK of SYN  \       /  rcv SYN,ACK       +---------+
   |           --------------   |     |   -----------
   |                  x         |     |     snd ACK
   |                            V     V
   |  CLOSE                   +---------+
   | -------                  |  ESTAB  |
   | snd FIN                  +---------+
   |                   CLOSE    |     |    rcv FIN
   V                  -------   |     |    -------
 +---------+          snd FIN  /       \   snd ACK          +---------+
 |  FIN    |<-----------------           ------------------>|  CLOSE  |
 | WAIT-1  |------------------                              |   WAIT  |
 +---------+          rcv FIN  \                            +---------+
   | rcv ACK of FIN   -------   |                            CLOSE  |
   | --------------   snd ACK   |                           ------- |
   V        x                   V                           snd FIN V
 +---------+                  +---------+                   +---------+
 |FINWAIT-2|                  | CLOSING |                   | LAST-ACK|
 +---------+                  +---------+                   +---------+
   |                rcv ACK of FIN |                 rcv ACK of FIN |
   |  rcv FIN       -------------- |    Timeout=2MSL -------------- |
   |  -------              x       V    ------------        x       V
    \ snd ACK                 +---------+delete TCB         +---------+
     ------------------------>|TIME WAIT|------------------>| CLOSED  |
                              +---------+                   +---------+
```

#### 11 States by Phase

| # | State | Phase | Why it exists |
|---|-------|-------|---------------|
| 1 | **CLOSED** | - | No connection |
| 2 | **LISTEN** | Setup | Passive open, waiting for SYN |
| 3 | **SYN_SENT** | Setup | Active open, sent SYN, waiting for SYN+ACK |
| 4 | **SYN_RCVD** | Setup | Received SYN, sent SYN+ACK, waiting for final ACK |
| 5 | **ESTABLISHED** | Data transfer | Connection open, data flows freely |
| 6 | **FIN_WAIT_1** | Teardown | Active closer sent FIN, waiting for ACK |
| 7 | **FIN_WAIT_2** | Teardown | FIN ACK'd, waiting for peer's FIN (peer may still send data) |
| 8 | **CLOSE_WAIT** | Teardown | Received peer's FIN, app hasn't closed yet |
| 9 | **CLOSING** | Teardown | Simultaneous close — both sent FIN before receiving the other's |
| 10 | **LAST_ACK** | Teardown | Passive closer sent FIN, waiting for final ACK |
| 11 | **TIME_WAIT** | Teardown | Wait 2×MSL to ensure final ACK delivered and old packets expire |

> **Why 6 teardown states but only 3 setup states?** TCP is full-duplex — each side closes independently (half-close), so each direction needs its own FIN/ACK cycle. Setup is symmetric (one SYN each + one ACK), but teardown is asymmetric — one side may still have data to send after the other closes.

Here may be a more readable diagram.
![tcp state Machine](/images/tcpfsm.png)

#### TCP Open: Three-Way Handshake
![tcp open](/images/tcp_open.svg)

![tcp open](/images/tcp_open_bytebytego.png)

#### TCP Close: Four-Way Handshake
![tcp close](/images/tcp_close_bytebytego.png)


#### SYN Queue and Accept Queue

During the 3-way handshake, the server kernel maintains two queues:

```
Client                        Server (LISTEN)
  |                              |
  |--- SYN ----->  ┌─────────────────────┐
  |                │  SYN Queue           │  ← half-open connections
  |                │  (SYN_RCVD state)    │
  |<-- SYN+ACK --  └─────────────────────┘
  |                              |
  |--- ACK ----->  ┌─────────────────────┐
  |                │  Accept Queue        │  ← fully established connections
  |                │  (ESTABLISHED state) │
  |                └─────────────────────┘
  |                              |
  |                      application calls accept()
```

1. Client sends **SYN** → server creates entry in **SYN Queue** (state: `SYN_RCVD`)
2. Client sends **ACK** → entry moves to **Accept Queue** (state: `ESTABLISHED`)
3. Application calls `accept()` → entry dequeued, returns socket fd

| Queue | Controlled by | Default |
|-------|--------------|---------|
| SYN Queue | `net.ipv4.tcp_max_syn_backlog` | 128–1024 |
| Accept Queue | `min(somaxconn, backlog)` | `somaxconn` default 128 |

- `net.core.somaxconn` — system-wide cap
- `backlog` — the argument in `listen(fd, backlog)`

**Why two queues?** Separation of concerns — a SYN flood attack won't block legitimate established connections from being accepted, and a slow application (not calling `accept()`) won't prevent new handshakes.

##### Queue Overflow

**SYN Queue full:**

| `tcp_syncookies` | Behavior |
|-------------------|----------|
| 0 | DROP the SYN |
| 1 (default) | Bypass queue — encode state in SYN+ACK sequence number (defense against SYN flood) |

**Accept Queue full:**

| `tcp_abort_on_overflow` | Behavior |
|--------------------------|----------|
| 0 (default) | DROP the ACK — client retransmits, may succeed if app catches up |
| 1 | Send RST — client sees "connection reset" immediately |

##### Troubleshooting

```bash
# Check current queue usage (LISTEN sockets)
ss -lnt
# Recv-Q = current accept queue length
# Send-Q = accept queue max size

# Check for overflows
netstat -s | grep -i "listen"
#   X times the listen queue of a socket overflowed  (accept queue)
#   Y SYNs to LISTEN sockets dropped                 (syn queue)

# Tune queue sizes
sysctl net.core.somaxconn                    # accept queue cap
sysctl net.ipv4.tcp_max_syn_backlog          # syn queue cap
sysctl net.ipv4.tcp_syncookies               # syncookie on/off
sysctl net.ipv4.tcp_abort_on_overflow        # RST on accept overflow
```

### TCP Design

For deeper coverage of TCP's key mechanisms — flow control, congestion control, reliability, timers, Nagle's algorithm, and more — see [TCP Design]({{< ref "posts/network/tcp_design" >}}).

For a deep dive into TIME_WAIT and why it waits exactly 2×MSL — see [TCP 2MSL & TIME_WAIT]({{< ref "posts/network/tcp_2msl" >}}).

### Reference
- http://www.tcpipguide.com/free/t_TCPConnectionEstablishmentProcessTheThreeWayHandsh-3.htm
- http://www.tcpipguide.com/free/t_TCPConnectionTermination-2.htm
- [RFC 793](https://datatracker.ietf.org/doc/html/rfc793#autoid-16)
- https://draveness.me/whys-the-design-tcp-three-way-handshake/
- https://blog.bytebytego.com/p/everything-you-always-wanted-to-know
- [Alibaba: TCP SYN Queue and Accept Queue Overflow Explained](https://www.alibabacloud.com/blog/tcp-syn-queue-and-accept-queue-overflow-explained_599203)
