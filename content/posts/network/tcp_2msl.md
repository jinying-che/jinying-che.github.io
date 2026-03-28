---
title: "TCP 2MSL & TIME_WAIT"
date: 2024-06-01T00:00:00+08:00
tags: ["network"]
description: "Why TCP TIME_WAIT waits 2×MSL, with examples and real-world troubleshooting"
---

### What is 2MSL?

**MSL** (Maximum Segment Lifetime) = the maximum time a TCP segment can exist in the network before being discarded. Typically **30s**, so 2MSL = **60s**.

After the active closer sends the final ACK, it enters **TIME_WAIT** and waits 2MSL before fully closing.

> TIME_WAIT is on whoever **initiates the close first** (the active closer) — not specifically client or server.

```
Case 1: Client closes first → Client enters TIME_WAIT
Case 2: Server closes first → Server enters TIME_WAIT
```

---

### Why 2MSL? Two Reasons

#### Reason 1: Ensure the final ACK is delivered

```
Active Closer                       Passive Closer
  |                                    |
  |<──── FIN ──────────────────────────|
  |──── ACK ──────────────────────────>|  final ACK
  |                                    |
  | ← enters TIME_WAIT (2MSL)         |

What if the final ACK is lost?

  |──── ACK ─────── X (lost)          |
  |                                    |  didn't receive ACK
  |<──── FIN (retransmit) ────────────|  retransmits FIN
  |──── ACK ──────────────────────────>|  re-ACK (still in TIME_WAIT)
```

**Why exactly 2MSL?**

```
Timeline:
  t=0     Active closer sends ACK, enters TIME_WAIT
  t≤1MSL  ACK is either delivered or expires in network
  t≤2MSL  If lost, retransmitted FIN arrives within 1 more MSL
  t=2MSL  Safe — no retransmitted FIN means passive closer got the ACK
```

- Lost ACK travels at most **1 MSL**
- Retransmitted FIN travels at most **1 MSL**
- Worst case: **1 MSL + 1 MSL = 2MSL**

Without TIME_WAIT: server retransmits FIN → OS has no socket → sends **RST** → server sees error instead of clean shutdown.

#### Reason 2: Let old duplicate segments die

```
Connection 1:  Client:5000 <──> Server:80   (closed at t=0)
Connection 2:  Client:5000 <──> Server:80   (new, same 4-tuple)

WITHOUT TIME_WAIT:
  t=0     Connection 1 closes
  t=1     Connection 2 opens (same ports)
  t=2     Delayed packet from Connection 1 arrives
          Server accepts it as Connection 2 data → DATA CORRUPTION!

WITH TIME_WAIT:
  t=0     Connection 1 closes, enters TIME_WAIT
  t=1     Same ports? DENIED (still in TIME_WAIT)
  t=60s   TIME_WAIT expires, all old packets guaranteed dead
  t=61s   Connection 2 can now safely reuse the same ports
```

A segment sent at the last moment can live 1MSL. A response to it can live another 1MSL. After 2MSL, **every** in-flight segment from the old connection has expired.

---

### Real-World: TIME_WAIT Accumulation

High-traffic servers that actively close connections accumulate thousands of TIME_WAIT sockets:

```bash
$ ss -s
TCP:   32000 (estab 500, closed 28000, orphaned 0, timewait 27500)

# At 1000 connections/sec → up to 60,000 TIME_WAIT sockets
```

#### Mitigations

| Approach | Sysctl | Trade-off |
|----------|--------|-----------|
| Reuse TIME_WAIT sockets | `net.ipv4.tcp_tw_reuse=1` | Safe — uses TCP timestamps to reject old segments |
| Reduce wait time | Lower `net.ipv4.tcp_fin_timeout` | Risks stale packets |
| Let client close | Application design | Moves TIME_WAIT to client side, spread across many machines |

#### Troubleshooting

```bash
# Count TIME_WAIT sockets
ss -s | grep timewait

# List TIME_WAIT connections
ss -tan state time-wait

# Check current settings
sysctl net.ipv4.tcp_tw_reuse
sysctl net.ipv4.tcp_fin_timeout
```

### Reference

- [RFC 793 — Transmission Control Protocol](https://datatracker.ietf.org/doc/html/rfc793)
- [RFC 6191 — Reducing TIME-WAIT State Using TCP Timestamps](https://datatracker.ietf.org/doc/html/rfc6191)
