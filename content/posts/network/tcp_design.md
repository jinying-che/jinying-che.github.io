---
title: "TCP Design"
date: 2024-06-01T00:00:00+08:00
tags: ["network"]
description: "TCP key design mechanisms: congestion control, flow control, reliability, and more"
---

### 1. Flow Control — "Don't overwhelm the receiver"

The **Window** field in the TCP header controls this.

```
Sender                          Receiver
  |                               |
  |--- 1000 bytes --------------->|  window = 3000
  |--- 1000 bytes --------------->|  window = 2000
  |--- 1000 bytes --------------->|  window = 1000
  |--- 1000 bytes ---X (blocked)  |  window = 0 (buffer full!)
  |                               |  app reads data...
  |<------------ ACK, window=2000 |  buffer freed
  |--- 1000 bytes --------------->|  resume sending
```

**Sliding Window** — the sender maintains a window of bytes it's allowed to send without waiting for ACK:

```
        Already ACK'd    |  Sent, not ACK'd  |  Can send  |  Can't send yet
  ──────────────────────┼───────────────────┼───────────┼─────────────────
  [  1  2  3  4  5  6  ] [  7   8   9  10  ] [ 11  12  ] [ 13  14  15 ... ]
                          └──────── window ──────────┘
```

**Window Scaling** (RFC 1323): original Window field is 16 bits (max 65535 bytes) — too small for modern networks. Window scale option multiplies it by 2^n, supporting up to ~1GB windows.

---

### 2. Congestion Control — "Don't overwhelm the network"

Flow control protects the **receiver**. Congestion control protects the **network**.

The sender maintains a **congestion window (cwnd)** — the actual send rate is:

```
effective_window = min(cwnd, receiver_window)
```

#### Four Algorithms (RFC 5681)

```
cwnd
 |        Slow Start          Congestion Avoidance
 |       (exponential)            (linear)
 |                    ┌──────────────────────
 |                   /
 |                  /
 |                /         ← ssthresh (threshold)
 |              /
 |            /
 |          /
 |        /
 |      /
 |    /
 |  /
 | /
 |/
 └──────────────────────────────────────── time
```

| Algorithm | When | Behavior |
|-----------|------|----------|
| **Slow Start** | cwnd < ssthresh | cwnd doubles each RTT (exponential) |
| **Congestion Avoidance** | cwnd >= ssthresh | cwnd += 1 MSS per RTT (linear) |
| **Fast Retransmit** | 3 duplicate ACKs | Retransmit lost segment immediately, don't wait for timeout |
| **Fast Recovery** | After fast retransmit | Set ssthresh = cwnd/2, cwnd = ssthresh + 3, then linear growth |

#### On Packet Loss

```
                        Packet loss detected
                               |
                 ┌─────────────┴─────────────┐
                 |                             |
          3 duplicate ACKs               Timeout (RTO)
          (mild congestion)            (severe congestion)
                 |                             |
          Fast Retransmit              ssthresh = cwnd/2
          ssthresh = cwnd/2            cwnd = 1 MSS
          cwnd = ssthresh              Back to Slow Start
          (Fast Recovery)
```

#### Modern Variants

| Variant | Approach | Use case |
|---------|----------|----------|
| **Reno** | Classic (above) | Legacy |
| **Cubic** | Cubic function for cwnd growth | Linux default |
| **BBR** (Google) | Measures bottleneck bandwidth & RTT, not loss-based | High bandwidth, lossy networks |

---

### 3. Reliability — "Every byte delivered, in order"

#### Retransmission

```
Sender                        Receiver
  |--- Seq 1 ───────────────>|
  |--- Seq 2 ──── X (lost)   |
  |--- Seq 3 ───────────────>|  out of order, buffer it
  |--- Seq 4 ───────────────>|  still missing Seq 2
  |<──── ACK 2 (dup) ────────|
  |<──── ACK 2 (dup) ────────|
  |<──── ACK 2 (dup) ────────|  3 dup ACKs → fast retransmit!
  |--- Seq 2 (retransmit) ──>|
  |<──── ACK 5 ──────────────|  cumulative ACK for 2,3,4
```

**Two retransmission triggers:**
- **Timeout (RTO)** — no ACK received within timeout
- **3 Duplicate ACKs** — fast retransmit (faster than waiting for timeout)

#### Selective ACK (SACK) — RFC 2018

Without SACK, the sender only knows "everything before byte X received." With SACK:

```
"I got bytes 1-100, 300-500, 700-800"
→ sender only retransmits 101-299 and 501-699
```

---

### 4. Ordering — "Bytes arrive in sequence"

Each byte has a **sequence number**. The receiver reorders out-of-order segments:

```
Arrive: [Seq 300] [Seq 100] [Seq 200]
Buffer: [Seq 100] [Seq 200] [Seq 300]  → deliver to app in order
```

---

### 5. Timer Management

| Timer | Purpose | Details |
|-------|---------|---------|
| **RTO (Retransmission Timeout)** | When to retransmit | Dynamically calculated from RTT samples |
| **TIME_WAIT (2MSL)** | Prevent stale packets | Typically 60s |
| **Keepalive** | Detect dead connections | Default 2 hours, then probes |
| **Persist** | Probe zero-window receiver | Prevents deadlock when window = 0 |

#### RTO Calculation (RFC 6298)

```
SRTT     = (1 - α) × SRTT + α × RTT_sample        (α = 1/8)
RTTVAR   = (1 - β) × RTTVAR + β × |SRTT - RTT|    (β = 1/4)
RTO      = SRTT + 4 × RTTVAR
```

Adaptive — fast networks get short timeouts, slow networks get longer ones.

---

### 6. Nagle's Algorithm — "Don't send tiny packets"

Problem: interactive apps (SSH) send 1 byte at a time → 40 bytes header for 1 byte payload.

```
Without Nagle:
  [H|1byte] [H|1byte] [H|1byte]    ← 41 bytes × 3 = 123 bytes

With Nagle:
  [H|1byte]  ... wait for ACK or buffer full ...  [H|3bytes]
                                                    ← 41 + 43 = 84 bytes
```

**Rule:** if there's unACK'd data in flight, buffer small segments until either:
- Previous data is ACK'd, or
- Buffer fills to MSS

**Disable with `TCP_NODELAY`** — common for latency-sensitive apps (games, trading).

---

### 7. Delayed ACK — "Don't ACK every single packet"

Instead of ACKing immediately, wait up to **40ms** hoping to:
- Piggyback ACK on a response data packet
- Combine multiple ACKs into one

```
Without delayed ACK:        With delayed ACK:
  Data →                      Data →
  ← ACK                      Data →
  Data →                      ← ACK (for both)
  ← ACK
```

> **Note:** Nagle + Delayed ACK together can cause latency issues — one waits for ACK, the other delays ACK. This is why `TCP_NODELAY` matters.

---

### 8. MSS Negotiation — "Agree on max segment size"

Exchanged during the SYN handshake via TCP options:

```
Client --- SYN (MSS=1460) --->
       <-- SYN+ACK (MSS=1400) ---

Both sides use min = 1400
```

**Why it matters:** avoids IP fragmentation. MSS = MTU (1500 typically) - IP header (20) - TCP header (20) = **1460**.

---

### Summary

```
TCP Key Designs
├── Connection Management
│   ├── 3-way handshake (SYN/ACK)
│   ├── 4-way close (FIN/ACK)
│   └── State machine (11 states)
├── Reliability
│   ├── Sequence numbers & ACKs
│   ├── Retransmission (RTO + Fast Retransmit)
│   └── SACK
├── Flow Control
│   ├── Sliding window
│   └── Window scaling
├── Congestion Control
│   ├── Slow start / Congestion avoidance
│   ├── Fast retransmit / Fast recovery
│   └── Modern: Cubic, BBR
├── Efficiency
│   ├── Nagle's algorithm
│   ├── Delayed ACK
│   └── MSS negotiation
└── Timers
    ├── RTO (adaptive)
    ├── TIME_WAIT (2MSL)
    ├── Keepalive
    └── Persist
```

### Reference

- [RFC 793 — Transmission Control Protocol](https://datatracker.ietf.org/doc/html/rfc793)
- [RFC 1323 — TCP Extensions for High Performance (Window Scaling)](https://datatracker.ietf.org/doc/html/rfc1323)
- [RFC 2018 — TCP Selective Acknowledgment Options (SACK)](https://datatracker.ietf.org/doc/html/rfc2018)
- [RFC 5681 — TCP Congestion Control](https://datatracker.ietf.org/doc/html/rfc5681)
- [RFC 6298 — Computing TCP's Retransmission Timer](https://datatracker.ietf.org/doc/html/rfc6298)
- [RFC 896 — Congestion Control in IP/TCP Internetworks (Nagle's Algorithm)](https://datatracker.ietf.org/doc/html/rfc896)
- [BBR: Congestion-Based Congestion Control — Google](https://research.google/pubs/bbr-congestion-based-congestion-control/)
- [CUBIC for Fast Long-Distance Networks](https://datatracker.ietf.org/doc/html/rfc8312)
