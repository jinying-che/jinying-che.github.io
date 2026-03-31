---
title: "LVS / IPVS"
date: 2026-03-30T23:58:29+0800
tags: ["network", "load balance", "lvs"]
description: "L4 load balancing deep dive: LVS/IPVS internals — architecture, forwarding modes, packet flow, and production tuning"
draft: true
---

## Background & Motivation

**LVS (Linux Virtual Server)** is the most fundamental L4 load balancing solution. It operates as the **IPVS (IP Virtual Server)** kernel module — built directly into the Linux kernel since 2.6. Almost every production L4 LB builds on or was inspired by its concepts:

- Kubernetes `kube-proxy` IPVS mode = literally LVS
- Alibaba's L4 infra = customized LVS at massive scale
- Google Maglev, Meta Katran = same conceptual model (VIP, scheduling, forwarding modes)

Why kernel-space matters:
```
Userspace LB (e.g. HAProxy):
  Packet → NIC → kernel → copy to userspace → process → copy to kernel → NIC
                           ^^^^^^^^^^^^^^^^^^           ^^^^^^^^^^^^^^^^^^
                           context switches + memory copies = overhead

Kernel-space LB (IPVS):
  Packet → NIC → kernel (IPVS hooks, forward directly) → NIC
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                  zero copies, no context switch = fast
```

---

## Architecture

### Where IPVS Sits in Netfilter

IPVS hooks into **Netfilter** — the same framework iptables uses. It registers at specific points in the kernel's packet processing pipeline:

```
                        Incoming Packet
                              │
                              ▼
                        ┌───────────┐
                        │PRE_ROUTING │
                        └─────┬─────┘
                              │
                        ┌─────▼─────┐
                        │  Routing   │
                        │  Decision  │
                        └──┬─────┬──┘
                           │     │
                    Local? │     │ Forward?
                           ▼     ▼
                    ┌────────┐ ┌───────────┐
                    │LOCAL_IN│ │  FORWARD   │
                    └────────┘ └─────┬─────┘
                     ▲               │
                     │         ┌─────▼─────┐
              IPVS hooks      │POST_ROUTING │
              here             └─────┬─────┘
              (priority -98,         │
               before iptables       ▼
               INPUT)              OUT
```

The kernel thinks the VIP packet is "local" (VIP is configured on the director), so it routes to LOCAL_IN. IPVS intercepts at LOCAL_IN (priority -98, before iptables INPUT) and **redirects** the packet to a real server before it reaches the socket layer.

### Core Data Structures

```
┌──────────────────────────────────────────────────────┐
│                   IPVS Internals                      │
│                                                       │
│  ┌───────────────────┐                                │
│  │  ip_vs_service     │  ← one per VIP:port           │
│  │                     │                               │
│  │  - protocol (TCP/UDP/SCTP)                          │
│  │  - addr + port (VIP)                                │
│  │  - scheduler (rr/wlc/sh/...)                        │
│  │  - flags                                            │
│  │  - *destinations[]  ──────────┐                     │
│  └───────────────────┘           │                     │
│                                  ▼                     │
│                    ┌───────────────────┐               │
│                    │ ip_vs_dest (×N)    │  ← one per RS │
│                    │                    │               │
│                    │ - addr + port (RIP) │              │
│                    │ - weight            │              │
│                    │ - conn_flags (DR/NAT/TUN)         │
│                    │ - activeconns       │              │
│                    │ - inactconns        │              │
│                    │ - stats             │              │
│                    └───────────────────┘               │
│                                                        │
│  ┌───────────────────┐                                │
│  │ ip_vs_conn         │  ← one per connection         │
│  │                     │    stored in hash table       │
│  │ - client IP:port    │                               │
│  │ - VIP:port          │                               │
│  │ - dest IP:port      │                               │
│  │ - state (ESTABLISHED/FIN_WAIT/...)                  │
│  │ - timer             │                               │
│  │ - packet_xmit()    │  ← function pointer per mode  │
│  └───────────────────┘                                │
└──────────────────────────────────────────────────────┘
```

Relationship: **Service** (1) → has many → **Destinations** (N) → tracked by → **Connections** (M)

---

## Connection Table

The connection table is a **hash table** that tracks every active connection. This is what makes IPVS stateful — once a connection is mapped to a backend, all subsequent packets follow the same path.

```
Hash function: hash(client_ip, client_port, vip, vport, protocol)
                              │
                              ▼
        ┌────┬────┬────┬────┬────┬────┬────┬────┐
Bucket: │  0 │  1 │  2 │  3 │  4 │  5 │  6 │  7 │ ...
        └────┴──┬─┴────┴────┴──┬─┴────┴────┴────┘
                │              │
                ▼              ▼
          ┌──────────┐   ┌──────────┐
          │ ip_vs_conn│   │ ip_vs_conn│
          │ 1.2.3.4:  │   │ 5.6.7.8:  │
          │ 50321     │   │ 40211     │
          │ → RS2     │   │ → RS1     │
          └────┬─────┘   └──────────┘
               │
               ▼
          ┌──────────┐
          │ ip_vs_conn│   ← chained for hash collisions
          │ 1.2.3.4:  │
          │ 50322     │
          │ → RS3     │
          └──────────┘
```

- Default: **4096 buckets** (`conn_tab_bits = 12`)
- Production: set to **2^20 (~1M buckets)** for millions of concurrent connections
- Lookup: O(1) average, O(n) worst case per bucket chain

### Packet Lookup Flow

```
Incoming packet
     │
     ▼
ip_vs_conn_in_get(src_ip, src_port, dst_ip, dst_port, protocol)
     │
     ├─── Found in hash table ───▶ Use existing conn
     │                              (same RS, same xmit func)
     │
     └─── Not found ──▶ New connection
                         │
                         ▼
                    ip_vs_service_find(vip, vport, protocol)
                         │
                         ▼
                    scheduler->schedule() → pick RS
                         │
                         ▼
                    ip_vs_conn_new() → insert into hash table
```

### TCP State Machine

IPVS tracks TCP state per connection for proper timeout management:

```
         SYN received
              │
              ▼
        ┌───────────┐
        │  SYN_RECV  │  timeout: 60s
        └─────┬─────┘
              │ SYN-ACK + ACK
              ▼
        ┌────────────┐
        │ESTABLISHED  │  timeout: 900s (15 min)
        └─────┬──────┘
              │ FIN
              ▼
        ┌───────────┐
        │ FIN_WAIT   │  timeout: 120s
        └─────┬─────┘
              │ FIN+ACK
              ▼
        ┌───────────┐
        │ TIME_WAIT  │  timeout: 120s
        └─────┬─────┘
              │ expires
              ▼
         Entry removed
         from conn table
```

For **UDP** (connectionless): IPVS creates a "connection" entry on first packet, timeout defaults to 300s.

---

## Forwarding Modes

### NAT Mode

The director rewrites the destination IP. RS replies go through the director, which rewrites the source IP back to the VIP.

```
Step 1: Client → Director (SYN)

  ┌─────────────────────────────────┐
  │ src: 1.2.3.4:50321              │
  │ dst: 10.0.0.1:80    (VIP)      │
  └─────────────────────────────────┘
        │
        ▼  Routing → LOCAL_IN → IPVS intercepts
        │
        │  1. Lookup service: 10.0.0.1:80/TCP → found
        │  2. Lookup conn table → no match → NEW
        │  3. Scheduler (wlc) → selects RS2
        │  4. Create ip_vs_conn:
        │       {1.2.3.4:50321 → 10.0.0.1:80 → 192.168.1.11:80}
        │  5. xmit = ip_vs_nat_xmit
        │  6. Rewrite dst IP:
        │
  ┌─────────────────────────────────┐
  │ src: 1.2.3.4:50321              │  ← unchanged
  │ dst: 192.168.1.11:80 (RS2)     │  ← rewritten
  └─────────────────────────────────┘
        │
        ▼  Forward to RS2


Step 2: RS2 → Director → Client (SYN-ACK)

  RS2's default gateway MUST be the Director.

  ┌─────────────────────────────────┐
  │ src: 192.168.1.11:80 (RS2)     │
  │ dst: 1.2.3.4:50321              │
  └─────────────────────────────────┘
        │
        ▼  Arrives at Director → IPVS reverse lookup
        │  Rewrite src IP → VIP
        │
  ┌─────────────────────────────────┐
  │ src: 10.0.0.1:80     (VIP)     │  ← rewritten
  │ dst: 1.2.3.4:50321              │
  └─────────────────────────────────┘
        │
        ▼  Back to client
```

**Pros**: simple setup, works across subnets
**Cons**: Director sees ALL traffic (both directions) — becomes a throughput bottleneck

```
NAT summary:

Client ──req──▶ Director ──(dst rewrite)──▶ RS
Client ◀──resp── Director ◀──(src rewrite)── RS
                 ^^^^^^^^
              bottleneck: all traffic flows through
```

### DR Mode (Direct Routing)

The director only rewrites the **L2 destination MAC** — L3/L4 headers are untouched. The RS replies **directly** to the client, bypassing the director entirely.

```
Prerequisites:
  - Director: VIP on a real interface
  - Each RS:  VIP on loopback (lo:0) + ARP suppressed
      sysctl net.ipv4.conf.lo.arp_ignore = 1
      sysctl net.ipv4.conf.lo.arp_announce = 2
  - All on the SAME L2 network (same VLAN/subnet)
```

**Why suppress ARP?** If RS responds to ARP for the VIP, the router would send traffic directly to RS, bypassing the LB entirely. ARP suppression ensures only the Director answers ARP for the VIP.

```
Step 1: Client → Director (SYN)

  Ethernet frame arrives at Director:
  ┌──────────────────────────────────────┐
  │ L2: dst_MAC = Director_MAC           │
  │ L3: src = 1.2.3.4  dst = 10.0.0.1   │  (VIP)
  │ L4: src_port = 50321  dst_port = 80  │
  └──────────────────────────────────────┘
        │
        ▼  IPVS intercepts at LOCAL_IN
        │
        │  1. Lookup service → found
        │  2. Lookup conn table → NEW
        │  3. Scheduler → RS2 (192.168.1.11)
        │  4. Create ip_vs_conn, xmit = ip_vs_dr_xmit
        │  5. ONLY rewrite L2 dst MAC → RS2's MAC
        │     L3/L4 headers UNTOUCHED
        │
  ┌──────────────────────────────────────┐
  │ L2: dst_MAC = RS2_MAC               │  ← MAC changed
  │ L3: src = 1.2.3.4  dst = 10.0.0.1   │  ← SAME
  │ L4: src_port = 50321  dst_port = 80  │  ← SAME
  └──────────────────────────────────────┘
        │
        ▼  Sent on local L2 network to RS2


Step 2: RS2 receives frame

        RS2 NIC receives (dst MAC = its own MAC) ✓
        │
        ▼  L3: dst IP = 10.0.0.1 = VIP on lo:0 → accepted!
        │  Application processes request normally
        │
        ▼  RS2 replies DIRECTLY to client (src IP = VIP)

  ┌──────────────────────────────────────┐
  │ src = 10.0.0.1 (VIP)  dst = 1.2.3.4 │
  └──────────────────────────────────────┘
        │
        ▼  Routed directly to client
           Director NEVER sees the response
```

**Pros**: highest throughput — Director only handles inbound (requests are typically 10-100x smaller than responses)
**Cons**: Director and RS must be on the same L2 segment

```
DR summary:

              request only
Client ──────▶ Director ──(MAC rewrite)──▶ RS
  ▲                                        │
  └────────────response (direct)───────────┘
         Director never sees this
```

### TUN Mode (IP Tunneling)

The director encapsulates the original packet inside a new IP header (IP-in-IP). RS decapsulates and replies directly to the client.

```
Step 1: Director encapsulates

  Original packet:
  ┌──────────────────────────────┐
  │ IP: src=1.2.3.4 dst=VIP     │
  │ TCP: 50321 → 80             │
  └──────────────────────────────┘
        │
        ▼  IPVS wraps in outer IP header

  ┌──────────────────────────────────────┐
  │ Outer IP: src=Director  dst=RS2_RIP  │  ← new header
  │ ┌──────────────────────────────┐     │
  │ │ Inner IP: src=1.2.3.4 dst=VIP│     │  ← original
  │ │ TCP: 50321 → 80              │     │
  │ └──────────────────────────────┘     │
  └──────────────────────────────────────┘
        │
        ▼  Routable across any network (RS can be anywhere)


Step 2: RS2 decapsulates

  RS2 receives, strips outer IP header
  Sees inner packet: dst = VIP (on lo) → accepted
  Replies directly to client (like DR)
```

**Pros**: RS can be in different data centers / subnets
**Cons**: RS must support IP-in-IP decapsulation (ipip kernel module), MTU overhead (~20 bytes)

### Mode Comparison

| | NAT | DR | TUN |
|---|---|---|---|
| **Director bottleneck** | Yes (both directions) | No (request only) | No (request only) |
| **Same L2 required** | No | Yes | No |
| **RS config** | Gateway = Director | VIP on lo + ARP suppress | VIP on lo + ipip module |
| **Header changes** | L3 (IP rewrite) | L2 (MAC rewrite) | L3 (IP encapsulation) |
| **Production use** | Small scale, simple | Most common | Cross-DC |

---

## Scheduling Algorithms

| Algorithm | Code | Description |
|---|---|---|
| Round Robin | `rr` | Rotate through RS list |
| Weighted Round Robin | `wrr` | Higher-weight RS gets more turns |
| Least Connections | `lc` | Fewest active connections |
| **Weighted Least Conn** | **`wlc`** | **Default.** `active_conns / weight` — lowest wins |
| Source Hashing | `sh` | Hash(client IP) → session affinity |
| Destination Hashing | `dh` | Hash(dest IP) → cache-friendly |
| Shortest Expected Delay | `sed` | `(active_conns + 1) / weight` |
| Never Queue | `nq` | Send to idle RS first, then use SED |

### WLC Dry Run

```
Current state:
  RS1: weight = 3, active_conns = 9
  RS2: weight = 2, active_conns = 4
  RS3: weight = 1, active_conns = 3

Score = active_conns / weight:
  RS1: 9 / 3 = 3.0
  RS2: 4 / 2 = 2.0  ← lowest score, WINS
  RS3: 3 / 1 = 3.0

New connection → RS2

After assignment:
  RS1: 9/3 = 3.0
  RS2: 5/2 = 2.5
  RS3: 3/1 = 3.0

Next connection → RS2 again (still lowest)

After:
  RS2: 6/2 = 3.0 — now tied with RS1 and RS3
  Next connection → first in list (RS1) breaks tie
```

Special cases:
- `weight = 0`: RS receives NO new connections (used for graceful drain)
- All weights equal: degrades to Least Connections

---

## Kernel Code Path

Simplified call chain showing how a packet flows through IPVS:

```
ip_vs_in()                            ← NF_LOCAL_IN hook handler
  │
  ├── ip_vs_service_find()            ← lookup VIP:port in service hash
  │     hash(protocol, addr, port)
  │
  ├── ip_vs_conn_in_get()             ← lookup connection hash table
  │     │
  │     ├── Found → existing connection
  │     │   use stored dest + xmit function pointer
  │     │
  │     └── Not found → new connection
  │         │
  │         ├── svc->scheduler->schedule()
  │         │     │
  │         │     ├── ip_vs_wlc_schedule()    ← pick RS with min(conns/weight)
  │         │     ├── ip_vs_rr_schedule()     ← or round robin
  │         │     └── ip_vs_sh_schedule()     ← or source hash
  │         │
  │         └── ip_vs_conn_new()
  │               │
  │               ├── allocate ip_vs_conn struct
  │               ├── set cp->dest = chosen RS
  │               ├── set cp->packet_xmit based on mode:
  │               │     NAT → ip_vs_nat_xmit
  │               │     DR  → ip_vs_dr_xmit
  │               │     TUN → ip_vs_tunnel_xmit
  │               └── insert into conn hash table
  │
  └── cp->packet_xmit(skb, cp, pp)   ← forward the packet
        │
        ├── ip_vs_nat_xmit:
        │     ip_hdr(skb)->daddr = dest->addr    (rewrite dst IP)
        │     tcp_hdr(skb)->dest = dest->port     (rewrite dst port)
        │     recalculate IP + TCP checksums
        │     ip_forward()
        │
        ├── ip_vs_dr_xmit:
        │     eth_hdr(skb)->h_dest = dest->MAC    (rewrite dst MAC only)
        │     dev_queue_xmit()                     (send on L2)
        │
        └── ip_vs_tunnel_xmit:
              build outer IP header (src=director, dst=RS)
              encapsulate original packet as payload
              ip_local_out()
```

---

## Production Setup

### ipvsadm Commands

```shell
# Load the IPVS kernel module
modprobe ip_vs

# Create a virtual service (VIP:port with WLC scheduling)
ipvsadm -A -t 10.0.0.1:80 -s wlc

# Add real servers
# -g = DR mode, -m = NAT mode, -i = TUN mode
# -w = weight
ipvsadm -a -t 10.0.0.1:80 -r 192.168.1.10:80 -g -w 3
ipvsadm -a -t 10.0.0.1:80 -r 192.168.1.11:80 -g -w 2
ipvsadm -a -t 10.0.0.1:80 -r 192.168.1.12:80 -g -w 1

# List current config
ipvsadm -Ln

# List with stats (packets, bytes)
ipvsadm -Ln --stats

# List with connection rates
ipvsadm -Ln --rate

# Drain a server (set weight to 0, existing conns finish)
ipvsadm -e -t 10.0.0.1:80 -r 192.168.1.12:80 -g -w 0

# Remove a real server
ipvsadm -d -t 10.0.0.1:80 -r 192.168.1.12:80

# Clear all rules
ipvsadm -C
```

### RS Configuration (DR Mode)

```shell
# On each Real Server — configure VIP on loopback + suppress ARP

# Add VIP to loopback
ip addr add 10.0.0.1/32 dev lo label lo:0

# Suppress ARP for VIP (critical for DR mode)
sysctl -w net.ipv4.conf.lo.arp_ignore=1
sysctl -w net.ipv4.conf.lo.arp_announce=2
sysctl -w net.ipv4.conf.all.arp_ignore=1
sysctl -w net.ipv4.conf.all.arp_announce=2
```

### Tuning Parameters

```shell
# Connection table size: 2^20 = ~1M buckets (set before loading module)
# Default is 2^12 = 4096
echo 20 > /sys/module/ip_vs/parameters/conn_tab_bits

# TCP timeouts: established / fin_wait / udp
ipvsadm --set 900 120 300

# Expire connections to removed destinations
echo 1 > /proc/sys/net/ipv4/vs/expire_nodest_conn

# Enable connection reuse for short-lived HTTP
echo 1 > /proc/sys/net/ipv4/vs/conntrack

# Check current connection count
ipvsadm -Ln --stats | head
cat /proc/net/ip_vs_conn | wc -l
```

### High Availability with Keepalived

In production, LVS is always paired with **Keepalived** for failover and health checks:

```
         ┌─────────────┐  VRRP heartbeat  ┌─────────────┐
         │  LVS Master  │ ◄──────────────▶ │  LVS Backup  │
         │ + Keepalived  │                  │ + Keepalived  │
         │  VIP: active  │                  │  VIP: standby │
         └──────┬───────┘                  └──────────────┘
                │              (on Master failure:
         ┌──────┼──────┐       Backup takes VIP via VRRP)
         ▼      ▼      ▼
        RS1    RS2    RS3
```

Keepalived provides:
- **VRRP (Virtual Router Redundancy Protocol)**: VIP failover between Master/Backup directors
- **Health checks**: TCP connect, HTTP GET, or custom script — auto-remove unhealthy RS
- **LVS management**: configures ipvsadm rules declaratively

### Connection Sync for HA

When the Master fails over to Backup, existing connections would break because the Backup has no connection table. The **sync daemon** solves this:

```
┌───────────────┐   multicast (224.0.0.81)   ┌───────────────┐
│    Master      │ ────conn table updates────▶ │    Backup      │
│  ip_vs_sync    │    (batched, async)         │  ip_vs_sync    │
│  (master mode) │                             │  (backup mode) │
└───────────────┘                             └───────────────┘

On failover:
  Backup takes VIP → already has conn table
  → existing TCP connections survive the failover
```

```shell
# On Master
ipvsadm --start-daemon master --mcast-interface eth0

# On Backup
ipvsadm --start-daemon backup --mcast-interface eth0
```

---

## Scaling: From Single Director to Cluster

### The Problem

A single LVS director with Keepalived provides **high availability** (active-passive failover), but only one director handles traffic at a time — the backup sits idle. This limits throughput to what a single machine can handle.

```
Keepalived (active-passive):

  ┌──────────┐     ┌──────────┐
  │  Master   │     │  Backup   │
  │  (active) │     │  (idle)   │  ← wasted capacity
  └─────┬────┘     └──────────┘
        │
   ┌────┼────┐
   ▼    ▼    ▼
  RS1  RS2  RS3
```

To scale beyond one director, we need **multiple active directors** sharing the traffic.

### Key Concepts

| Concept | What it is | Role in LVS cluster |
|---|---|---|
| **BGP** | Border Gateway Protocol — a routing protocol where routers exchange reachability info: "I can reach this IP prefix, send traffic to me." It's how the Internet's routing tables are built. | Each LVS director runs a BGP daemon to **announce the VIP** to the upstream router — telling it "I can handle traffic for this VIP" |
| **ECMP** | Equal-Cost Multi-Path — a **router feature** that distributes traffic across multiple equal-cost paths to the same destination, using a hash of the packet's 5-tuple (src IP, dst IP, src port, dst port, protocol) | The upstream router sees multiple directors announcing the same VIP via BGP → ECMP **spreads flows** across all of them |
| **Consistent Hashing** | A hash algorithm designed so that adding/removing a node only remaps ~1/N of the keys (instead of reshuffling everything) | Minimizes connection disruption when a director is added/removed from the ECMP group |

### Architecture

```
ECMP cluster (all directors active):

                        Upstream Router
                       (ECMP to same VIP)
                      ┌────┬────┬────┬────┐
                      │    │    │    │    │
                      ▼    ▼    ▼    ▼    ▼
                    LVS1  LVS2  LVS3  LVS4   ← all active
                    (BGP)  (BGP)  (BGP)  (BGP)   all announce VIP
                      │    │    │    │    │
                      └────┴──┬─┴────┴────┘
                         ┌────┼────┐
                         ▼    ▼    ▼
                        RS1  RS2  RS3
```

### How It Works

```
1. Each director runs a BGP daemon (e.g. BIRD, ExaBGP)
   and announces the VIP to the upstream router:

   LVS1 → Router: "I can reach 10.0.0.1/32"
   LVS2 → Router: "I can reach 10.0.0.1/32"
   LVS3 → Router: "I can reach 10.0.0.1/32"

2. Router sees 3 equal-cost paths → enables ECMP:

   Routing table:
   10.0.0.1/32
     → next-hop: LVS1 (cost 10)
     → next-hop: LVS2 (cost 10)  ← all equal cost
     → next-hop: LVS3 (cost 10)

3. For each incoming packet, router hashes the 5-tuple:

   hash(src_ip, dst_ip, src_port, dst_port, proto) % 3
     → 0: send to LVS1
     → 1: send to LVS2
     → 2: send to LVS3

   All packets of the SAME flow (same 5-tuple) → same director

4. Each director runs IPVS independently:
   receives packet → conn table lookup → schedule → forward to RS

5. If LVS2 dies → BGP withdraws route → router removes it from ECMP
   Remaining traffic splits between LVS1 and LVS3 automatically
```

### The Connection Consistency Problem

When a director is added or removed, the ECMP hash changes — some flows get remapped to a different director that has **no conn table entry** for them.

```
Before (3 directors):
  Flow A: hash % 3 = 1 → LVS2 (conn table has entry)

After LVS3 dies (2 directors):
  Flow A: hash % 2 = 0 → LVS1 (NO conn table entry!)
  → LVS1 treats it as a NEW connection
  → schedules to a possibly different RS
  → existing TCP connection breaks
```

### Solutions

| Approach | How it works | Trade-off |
|---|---|---|
| **Consistent hashing** | Use consistent hashing instead of modulo — adding/removing a node only remaps ~1/N flows | Most flows survive, but some still break |
| **Connection sync** | Replicate conn tables across all directors (multicast) | All flows survive, but high overhead at scale |
| **Stateless design** | Make the application stateless — hitting a different RS is fine | Best scalability, but app must support it |

This is exactly the problem that **Google Maglev** and **Meta Katran** solved — they use consistent hashing across multiple active LB nodes with no shared connection state, accepting that a small fraction of flows may be disrupted during scaling events.

### Single Director vs Cluster

| | Keepalived (Active-Passive) | ECMP + BGP (Active-Active) |
|---|---|---|
| **Active directors** | 1 (backup is idle) | All |
| **Throughput** | Limited to 1 machine | Scales horizontally |
| **Failover** | VRRP — seconds | BGP withdrawal — seconds |
| **Conn table** | Synced via multicast | Independent per director (or synced) |
| **Complexity** | Simple | Requires BGP daemon + ECMP-capable router |
| **Use case** | Small/medium traffic | Large scale |

---

## Reference

- [The Linux Virtual Server Project](http://www.linuxvirtualserver.org/)
- [IPVS kernel source (net/netfilter/ipvs/)](https://github.com/torvalds/linux/tree/master/net/netfilter/ipvs)
- [Keepalived](https://www.keepalived.org/)
- [LVS HOWTO](http://www.austintek.com/LVS/LVS-HOWTO/HOWTO/)
- [ipvsadm man page](https://linux.die.net/man/8/ipvsadm)
- [Kubernetes IPVS mode](https://kubernetes.io/blog/2018/07/09/ipvs-based-in-cluster-load-balancing-deep-dive/)
