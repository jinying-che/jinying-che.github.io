---
title: "Anycast + BGP: Fast Failover Without DNS"
date: "2026-03-31T16:37:17+0800"
tags: ["network"]
description: "Anycast + BGP Overview"
---

## Background & Motivation

When disaster happens, SRE usually switches traffic by updating DNS records to point to a healthy endpoint. However, this can be slow due to **DNS caching** at multiple layers:

| Layer | Description |
| ----- | ----------- |
| Browser cache | Browsers cache DNS results (Chrome: up to 60s) |
| OS cache | OS-level DNS cache (e.g. `systemd-resolved`, `dnsmasq`) |
| DNS Resolver cache | ISP or corporate resolvers cache based on TTL |
| Application cache | Some apps/libraries cache DNS independently (e.g. JVM caches DNS indefinitely by default) |

Even after updating the DNS record, clients continue using the stale cached IP until the TTL expires. If the TTL was set to 3600s (1 hour), it could take up to 1 hour for all traffic to shift.

We need a mechanism that **doesn't change the IP address** — only changes where the traffic is routed.

## What Is Anycast

Anycast is **not a device** — it's an **IP addressing strategy**. You assign the same IP to multiple machines in different data centers. That's it.

| | Unicast | Anycast |
|---|---|---|
| Concept | 1 IP → 1 destination | 1 IP → many destinations |
| Who decides routing | IP is unique, only one place to go | **BGP routers** pick the nearest |
| Setup | Assign IP to one server | Assign **same IP** to servers in multiple DCs |

The "implementation" is literally just configuration — each DC's router announces the same IP prefix:

```
# Tokyo DC router config
router bgp 13335
  network 1.2.3.4/32    ← announce this IP

# London DC router config
router bgp 13335
  network 1.2.3.4/32    ← announce the SAME IP
```

The moment two routers announce the same IP prefix via BGP, you have anycast.

## What Is BGP

[BGP (Border Gateway Protocol)](https://en.wikipedia.org/wiki/Border_Gateway_Protocol) is the routing protocol that glues the internet together. Each ISP, cloud provider, or large company is an **Autonomous System (AS)** with a unique **AS Number (ASN)**.

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Google       │         │  Comcast      │         │  Cloudflare  │
│  ASN: 15169   │◄──BGP──►│  ASN: 7922    │◄──BGP──►│  ASN: 13335  │
└──────────────┘         └──────────────┘         └──────────────┘
```

### ASN vs Router ID

| Term | Scope | Example |
|------|-------|---------|
| **ASN** (AS Number) | Per **organization** | Google = 15169, Cloudflare = 13335 |
| **Router ID** | Per **router** within an AS | Usually set to the router's loopback IP (e.g. 10.0.1.1) |
| **ASN range** | 1-64511 = public, 65001-65534 = private | Similar to public vs private IPs |

ASN is assigned by [IANA](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml).

### How BGP Routes Traffic

BGP routers exchange **route advertisements** to build a routing table. Each router picks the best path based on:

```
Internet router's BGP table:

Prefix        Next-Hop       AS Path       Metric   Preferred
─────────────────────────────────────────────────────────────
1.2.3.4/32    203.0.1.1      13335         10       ✓ (shortest)
1.2.3.4/32    198.51.1.1     7922 13335    50
1.2.3.4/32    192.0.1.1      3356 13335    30
```

Same ASN, same IP prefix — but BGP differentiates them by **next-hop IP** and **AS path length**, and picks the best one.

## How They Work Together

Anycast is the **idea** (assign same IP to multiple locations), BGP is the **engine** (advertises routes and picks the shortest path).

```
Organization: Cloudflare (ASN 13335)
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Tokyo DC                London DC              Virginia DC  │
│  Router ID: 10.0.1.1    Router ID: 10.0.2.1    Router ID: 10.0.3.1
│  Next-hop:  203.0.1.1   Next-hop:  198.51.1.1  Next-hop:  192.0.1.1
│  Announces: 1.2.3.4/32  Announces: 1.2.3.4/32  Announces: 1.2.3.4/32
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Each DC announces the same IP. Internet routers see multiple paths and pick the nearest one.

### Where Anycast Sits in the Load Balancing Stack

Anycast + BGP works **between the client and the L4 LB** — it's the network-level routing that decides **which data center** receives the traffic before any load balancer sees the packet.

```
Client
  │
  │  ① DNS resolves to Anycast IP (e.g. 1.2.3.4)
  ▼
┌─────────────────┐
│   DNS (GSLB)    │  ← Returns the same Anycast IP (not per-region IPs)
└────────┬────────┘
         │
         │  ② BGP routes packet to nearest DC announcing 1.2.3.4
         │
         ▼
  ┌── BGP/Anycast ──┐
  │  Network Layer   │  ← Anycast works HERE
  │  (Internet       │    Routers pick the nearest DC based on
  │   Routers)       │    BGP shortest AS path
  └───────┬──────────┘
          │
          ▼  (packet arrives at nearest DC)
  ┌─────────────────┐
  │   L4 LB         │  ← The Anycast IP is the VIP of L4 LB
  │  (NLB / LVS)    │    Distributes TCP connections across L7 LBs
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │   L7 LB         │  ← Path routing, rate limiting, canary, headers
  │ (Nginx / Envoy) │    TLS termination, request manipulation
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  App Servers     │
  │  (RS pool)       │
  └─────────────────┘
```

Key insight: **the Anycast IP is the L4 LB's VIP**. Every DC has an L4 LB listening on `1.2.3.4`, and BGP decides which DC gets the packet.

### With vs Without Anycast

| | Without Anycast | With Anycast |
|---|---|---|
| DNS returns | Different IPs per region (`1.1.1.1` for US, `2.2.2.2` for EU) | Same IP everywhere (`1.2.3.4`) |
| DC selection | DNS (GSLB) picks the DC | BGP picks the DC |
| Failover | Update DNS → wait for TTL | BGP withdraws route → ~30-90s |
| GSLB role | **Critical** — decides DC routing | **Optional** — can layer on top for finer control |

In practice, big providers often combine both: Anycast for fast failover + GSLB for fine-grained traffic shaping (e.g. weighted routing, canary by region).

## Failover Flow

```
Normal state:
  Tokyo  ──announces 1.2.3.4──►  BGP peers
  London ──announces 1.2.3.4──►  BGP peers

Tokyo goes down:
  Tokyo  ──withdraws 1.2.3.4──►  BGP peers  (or peers detect link failure)
  London ──still announces────►  BGP peers

BGP convergence: ~30-90 seconds
```

No DNS record changes. No TTL waiting. The IP stays the same — only the **route** changes.

### Anycast + BGP vs DNS Failover

| | Anycast + BGP | DNS Failover |
|---|---|---|
| Failover speed | ~30-90s (BGP convergence) | Minutes to hours (TTL dependent) |
| Client change needed | None | Must re-resolve DNS |
| IP address | Stays the same | Changes to new IP |
| Granularity | Network-level (per packet) | Per DNS query |
| Limitation | Stateful connections (TCP) may break on route change | Cached entries serve stale IPs |

## Caveats & Solutions

BGP route changes can shift traffic mid-connection, breaking **TCP sessions** (since TCP is bound to a specific src/dst IP pair and port).

| Solution | How it helps |
|----------|-------------|
| **ECMP pinning** | Consistent hashing on flow (src IP + dst IP + ports) to keep flows on the same path |
| **Connection draining** | Gracefully drain existing connections before withdrawing the BGP route |
| **QUIC / HTTP3** | Connection ID-based (not IP-based), naturally survives route changes |

## Reference
- [RFC 4786 - Operation of Anycast Services](https://datatracker.ietf.org/doc/html/rfc4786)
- [RFC 4271 - A Border Gateway Protocol 4 (BGP-4)](https://datatracker.ietf.org/doc/html/rfc4271)
- [Cloudflare - What is Anycast?](https://www.cloudflare.com/learning/cdn/glossary/anycast-network/)
- [Cloudflare - What is BGP?](https://www.cloudflare.com/learning/security/glossary/what-is-bgp/)
- [IANA AS Numbers](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml)
