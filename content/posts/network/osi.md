---
title: "OSI Model"
date: 2026-03-28T17:32:35+0800
tags: ["network"]
description: "Understanding the 7-layer OSI model with a concrete example: a message from a phone over WiFi to a wired PC"
---

### Overview

The **OSI (Open Systems Interconnection)** model is a conceptual framework that standardizes network communication into **7 layers**. Each layer has a specific responsibility, serves the layer above, and relies on the layer below.

```
The key principle: ENCAPSULATION

  Sender (top → bottom)              Receiver (bottom → top)
  ┌─────────────────────┐            ┌─────────────────────┐
  │ 7. Application      │  ──────▶   │ 7. Application      │
  │ 6. Presentation     │            │ 6. Presentation     │
  │ 5. Session          │            │ 5. Session          │
  │ 4. Transport        │            │ 4. Transport        │
  │ 3. Network          │            │ 3. Network          │
  │ 2. Data Link        │            │ 2. Data Link        │
  │ 1. Physical         │  ──wifi──▶ │ 1. Physical         │
  └─────────────────────┘            └─────────────────────┘

  Each layer adds its own header (encapsulation) when sending,
  and strips it (decapsulation) when receiving.
```

---

### The 7 Layers

| Layer | Name | PDU | Key Protocols / Standards | Devices |
|-------|------|-----|---------------------------|---------|
| 7 | **Application** | Data | HTTP, DNS, SMTP, FTP, SSH | - |
| 6 | **Presentation** | Data | TLS/SSL, JPEG, UTF-8, gzip | - |
| 5 | **Session** | Data | Sockets, RPC, NetBIOS | - |
| 4 | **Transport** | Segment | TCP, UDP | - |
| 3 | **Network** | Packet | IP, ICMP, ARP | Router |
| 2 | **Data Link** | Frame | Ethernet (802.3), WiFi (802.11) | Switch, AP |
| 1 | **Physical** | Bits | Electrical signals, radio waves, fiber optics | Cable, NIC, Hub |

> **PDU** = Protocol Data Unit — the name for data at each layer.

---

### Network Devices by Layer

| Layer | Device | What it does |
|-------|--------|-------------|
| 1 - Physical | **Hub** | Repeats signals to all ports — no intelligence, just amplifies bits |
| 1 - Physical | **Repeater** | Extends signal range by regenerating bits |
| 1 - Physical | **Modem** | Converts digital ↔ analog signals (e.g. DSL, fiber ONT) |
| 2 - Data Link | **Switch** | Forwards frames by MAC address — learns which MAC is on which port |
| 2 - Data Link | **Access Point (AP)** | Bridges WiFi (802.11) ↔ Ethernet (802.3) at frame level |
| 2 - Data Link | **Bridge** | Connects two L2 network segments, filters by MAC |
| 3 - Network | **Router** | Forwards packets by IP address — connects different networks |
| 3 - Network | **L3 Switch** | Switch with routing capability — wire-speed IP forwarding |
| 3/4 | **Firewall (basic)** | Filters by IP and port (ACL rules) |
| 4 - Transport | **Load Balancer (L4)** | Routes by IP + port, no payload inspection |
| 7 - Application | **Load Balancer (L7)** | Routes by HTTP content (URL, headers, cookies) |
| 7 - Application | **Firewall (NGFW)** | Inspects up to L7 — deep packet inspection, app-aware filtering |
| 7 - Application | **Proxy / Reverse Proxy** | Terminates and re-initiates connections (e.g. Nginx, HAProxy) |

> **Key rule:** a device operates at layer N, meaning it reads and acts on headers up to layer N. A router (L3) reads IP headers but doesn't inspect TCP ports. A L7 load balancer reads all the way up to HTTP.

---

### Concrete Example: Phone (WiFi) → PC (Company LAN)

Scenario: You send a message "Hello" from a chat app on your **phone** (home WiFi) to a **PC** (in a company LAN) across the Internet.

```
Home Network               Internet              Company Network
─────────────              ────────              ─────────────────────────────────────────────────────────
[Phone] ))) [Home Router/AP] ═══ [ISP] ═══ [Gateway] ═══ [Firewall] ═══ [L4 LB] ═══ [LAN Router] ═══ [Switch] ═══ [PC]
10.0.0.2     10.0.0.1                       203.0.113.1   192.168.1.1    192.168.1.2  10.10.1.1        10.10.1.x    10.10.1.100
MAC:AA:AA    NAT: 98.51.100.7               (public)      (DMZ)          (DMZ)        (LAN gateway)                MAC:CC:CC
```

---

#### Sender Side (Phone) — Encapsulation

Each layer wraps the data with its own header, top to bottom:

**Layer 7 — Application**

The chat app constructs an HTTP POST request:
```
POST /send HTTP/1.1
Host: 203.0.113.1:8080
Content-Type: text/plain

Hello
```

**Layer 6 — Presentation**

Encodes the data for transmission:
- Text encoded as UTF-8
- If using HTTPS, TLS encrypts the payload here

**Layer 5 — Session**

Manages the communication session:
- Establishes/maintains the TCP socket session
- Tracks which conversation this data belongs to

**Layer 4 — Transport (TCP)**

Breaks data into segments, adds port numbers for process-to-process delivery:
```
┌──────────────────────────────────────────┐
│ TCP Header                               │
│  Src Port: 52000  Dst Port: 8080         │
│  Seq: 1000        Ack: 1                 │
│  Flags: PSH+ACK   Window: 65535          │
├──────────────────────────────────────────┤
│ Payload: "POST /send ... Hello"          │
└──────────────────────────────────────────┘
```

**Layer 3 — Network (IP)**

Adds IP addresses for host-to-host delivery across networks:
```
┌──────────────────────────────────────────┐
│ IP Header                                │
│  Src IP: 10.0.0.2   Dst IP: 203.0.113.1 │
│  TTL: 64            Protocol: TCP (6)    │
├──────────────────────────────────────────┤
│ TCP Header + Payload                     │
└──────────────────────────────────────────┘
```

**Layer 2 — Data Link (WiFi 802.11)**

Adds MAC addresses for hop-to-hop delivery on the local network. Since the phone is on WiFi, it uses 802.11 frame format:
```
┌──────────────────────────────────────────┐
│ 802.11 WiFi Frame Header                 │
│  Src MAC: AA:AA (phone)                  │
│  Dst MAC: BB:BB (router/AP)              │
│  BSSID:   BB:BB                          │
├──────────────────────────────────────────┤
│ IP Packet (IP Header + TCP + Payload)    │
├──────────────────────────────────────────┤
│ FCS (Frame Check Sequence)               │
└──────────────────────────────────────────┘
```

> Note: Dst MAC is the **Home Router/AP** (BB:BB), NOT the PC. The phone sends to its default gateway as the next hop.

**Layer 1 — Physical (Radio)**

The WiFi NIC converts the frame into **radio waves** (2.4GHz or 5GHz) and transmits over the air.

---

#### The Network Path

Each device processes up to its operating layer, then forwards:

```
Device              Layer   What it does
──────────────────────────────────────────────────────────────────────────

[Home Router/AP]    L2-L3   Receives radio waves (L1)
                            Strips WiFi 802.11 → Ethernet 802.3 (L2)
                            ★ SNAT (L3+L4):
                              Src IP:   10.0.0.2  → 98.51.100.7 (public IP)
                              Src Port: 52000     → 39000 (remapped)
                              Records in NAT table:
                              {39000 → 10.0.0.2:52000} for return traffic
                            Forwards to ISP (L1)
                                  │
                                  ▼
[ISP / Internet]    L1-L3   Multiple routers, each:
                            - Strips L2 header
                            - Reads Dst IP: 203.0.113.1 (L3)
                            - Looks up routing table → next hop
                            - Decrements TTL
                            - Re-encapsulates with new L2 header
                            - Forwards
                            MAC changes at EVERY hop, IP stays the same
                                  │
                                  ▼
[Gateway Router]    L3      Company's edge router
                            Receives from ISP link (L1→L2)
                            Reads Dst IP: 203.0.113.1 — that's me (L3)
                            Routes to DMZ: next hop → Firewall
                            Re-encapsulates: Dst MAC → Firewall MAC
                                  │
                                  ▼
[Firewall]          L3/L4   Reads IP header (L3): Src 98.51.100.7
                            Reads TCP header (L4): Dst port 8080
                            Checks rules:
                              ✓ Port 8080 allowed from external
                              ✓ Src IP not in blocklist
                              ✓ Stateful: new connection, create entry
                            Forwards with new L2 header → L4 LB
                                  │
                                  ▼
[L4 Load Balancer]  L4      Reads TCP header (L4): Dst port 8080
                            Has pool: [10.10.1.100, 10.10.1.101, 10.10.1.102]
                            Picks backend (round-robin, least-conn...)
                            ★ DNAT (L3):
                              Dst IP: 203.0.113.1 → 10.10.1.100 (chosen PC)
                            Forwards → LAN Router
                                  │
                                  ▼
[LAN Router]        L3      Reads Dst IP: 10.10.1.100 (L3)
                            Looks up routing table → 10.10.1.0/24 is local
                            ARP lookup: 10.10.1.100 → MAC CC:CC
                            Re-encapsulates with Ethernet header (L2)
                            Dst MAC → CC:CC (PC)
                            Forwards to Switch
                                  │
                                  ▼
[Switch]            L2      Reads Dst MAC: CC:CC (L2)
                            Looks up MAC table → port 7
                            Forwards frame out port 7
                            NO header changes
                                  │
                                  ▼
[PC]                L1-L7   Decapsulation (see below)
```

---

#### Receiver Side (PC) — Decapsulation

Each layer strips its header, bottom to top:

**Layer 1 — Physical (Electrical)**

The PC's Ethernet NIC receives electrical signals on the cable and converts them to a stream of bits.

**Layer 2 — Data Link (Ethernet 802.3)**

```
┌────────────────────────┐
│ Ethernet Header        │ ← strip this
│  Dst MAC: CC:CC (me!)  │   verify FCS, check MAC matches
├────────────────────────┤
│ IP Packet              │ ← pass up to Layer 3
└────────────────────────┘
```

**Layer 3 — Network (IP)**

```
┌─────────────────────────────┐
│ IP Header                   │ ← strip this
│  Dst IP: 10.10.1.100 (me!) │   verify IP matches
│  Protocol: TCP (6)          │   → pass to TCP handler
├─────────────────────────────┤
│ TCP Segment                 │ ← pass up to Layer 4
└─────────────────────────────┘
```

**Layer 4 — Transport (TCP)**

```
┌────────────────────────┐
│ TCP Header             │ ← strip this
│  Dst Port: 8080        │   → deliver to process on port 8080
│  Seq: 1000             │   verify ordering, send ACK
├────────────────────────┤
│ Application Data       │ ← pass up to Layer 5+
└────────────────────────┘
```

**Layer 5 — Session**

Maps the segment to the correct socket/session.

**Layer 6 — Presentation**

Decrypts (if TLS), decompresses, decodes UTF-8 → readable text.

**Layer 7 — Application**

The chat app receives the HTTP request, extracts "Hello", and displays it.

---

#### Full Encapsulation Stack

**Sender (Phone) — Encapsulation (top → bottom)**

```
Layer 7 (Application):  [         "Hello"          ]
                         ↓ add HTTP header
Layer 6 (Presentation): [      HTTP + "Hello"      ]
                         ↓ TLS encrypt
Layer 5 (Session):      [   session + encrypted    ]
                         ↓ add TCP header (Src:52000 Dst:8080)
Layer 4 (Transport):    [  TCP |    payload        ]
                         ↓ add IP header (Src:10.0.0.2 Dst:203.0.113.1)
Layer 3 (Network):      [ IP | TCP |   payload     ]
                         ↓ add WiFi frame (Src MAC:AA:AA Dst MAC:BB:BB)
Layer 2 (Data Link):    [WiFi| IP | TCP | payload |FCS]
                         ↓ convert to radio waves
Layer 1 (Physical):     ))))))) radio waves )))))))
```

**Receiver (PC) — Decapsulation (bottom → top)**

```
Layer 1 (Physical):     Electrical signals → bits
                         ↑
Layer 2 (Data Link):    [Eth | IP | TCP | payload |FCS]
                         ↑ strip Ethernet header, verify Dst MAC=CC:CC ✓
Layer 3 (Network):      [ IP | TCP |   payload     ]
                         ↑ strip IP header, verify Dst IP=10.10.1.100 ✓
Layer 4 (Transport):    [  TCP |    payload        ]
                         ↑ strip TCP header, deliver to port 8080
Layer 5 (Session):      [   session + encrypted    ]
                         ↑ map to socket
Layer 6 (Presentation): [      HTTP + "Hello"      ]
                         ↑ TLS decrypt, decode
Layer 7 (Application):  [         "Hello"          ]
```

**What changes at each hop:**

```
              Phone    Home Router   ISP Routers   Gateway   Firewall   L4 LB          LAN Router   Switch   PC
              ──────────────────────────────────────────────────────────────────────────────────────────────────────
Layer 2 (MAC): AA→BB   BB→ISP       ✓ changes     ✓ new     ✓ new     ✓ new           ✓ →CC:CC     CC→CC    ← CHANGES every hop
Layer 3 (IP):  10.0.0.2 ★98.51.100.7 (same)       (same)    (same)    ★10.10.1.100    (same)       (same)   ← CHANGES at NAT
Layer 4 (Port): 52000   ★39000       (same)        (same)    (same)    (same)          (same)       (same)   ← CHANGES at SNAT
Payload:       "Hello"  (same)       (same)        (same)    (same)    (same)          (same)       (same)   ← ALWAYS same
```

> ★ = modified by NAT. Without NAT, L3/L4 stay the same end-to-end.
> NAT is necessary because private IPs (10.x, 192.168.x) are not routable on the public Internet.

---

### OSI vs TCP/IP Model

In practice, the **TCP/IP model** (4 layers) is what the Internet actually uses. OSI is a teaching/reference model.

```
       OSI Model              TCP/IP Model
  ┌─────────────────┐    ┌─────────────────┐
  │ 7. Application  │    │                 │
  │ 6. Presentation │ ──▶│   Application   │
  │ 5. Session      │    │                 │
  ├─────────────────┤    ├─────────────────┤
  │ 4. Transport    │ ──▶│   Transport     │
  ├─────────────────┤    ├─────────────────┤
  │ 3. Network      │ ──▶│   Internet      │
  ├─────────────────┤    ├─────────────────┤
  │ 2. Data Link    │ ──▶│   Network       │
  │ 1. Physical     │    │   Access        │
  └─────────────────┘    └─────────────────┘
```

| | OSI | TCP/IP |
|---|-----|--------|
| Layers | 7 | 4 |
| Origin | ISO standard (theoretical) | DARPA (practical, built for the Internet) |
| L5-L7 | Separate layers | Merged into Application |
| L1-L2 | Separate layers | Merged into Network Access |
| Usage | Reference model, troubleshooting framework | Actual protocol stack in use |

> **Why does OSI still matter?** It's the universal vocabulary for troubleshooting — "this is a Layer 2 problem" or "the issue is at Layer 7" is how network engineers communicate, regardless of which model the actual protocols follow.

---

### Reference

- [ISO/IEC 7498-1 — OSI Basic Reference Model](https://www.iso.org/standard/20269.html)
- [RFC 1122 — Requirements for Internet Hosts (TCP/IP layers)](https://datatracker.ietf.org/doc/html/rfc1122)
- Computer Networking: A Top-Down Approach — Kurose & Ross
