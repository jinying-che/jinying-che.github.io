---
title: "Load Balancing"
date: 2026-03-30T23:58:29+0800
tags: ["network", "load balance"]
description: "Load balancing overview: L4 vs L7 — how they work, trade-offs, and production solutions"
draft: true
---

## Overview

A **load balancer** distributes incoming network traffic across multiple backend servers to improve availability, reliability, and performance. Without it, a single server becomes a bottleneck and a single point of failure.

```
                  Without LB                          With LB

  Client ──────▶ [Server]            Client ──────▶ [Load Balancer]
                  (SPOF)                               │   │   │
                                                       ▼   ▼   ▼
                                                     RS1  RS2  RS3
```

Load balancers operate at different layers of the OSI model, most commonly **Layer 4 (Transport)** and **Layer 7 (Application)**:

| | Layer 4 | Layer 7 |
|---|---|---|
| **OSI Layer** | Transport (TCP/UDP) | Application (HTTP/gRPC) |
| **Sees** | IP addresses + ports | Full request (URL, headers, cookies, body) |
| **Routes by** | Connection-level info | Content-level info |
| **Example** | NLB, LVS/IPVS, HAProxy (TCP) | Nginx, Envoy, ALB, HAProxy (HTTP) |

## Terminology

| Term | Meaning |
|---|---|
| **VIP** | Virtual IP — the single IP address clients connect to |
| **RS (Real Server)** | The actual backend server that processes requests |
| **Director** | The LB machine that receives traffic on the VIP and forwards to RS |
| **NAT** | Network Address Translation — rewriting IP addresses in packet headers |
| **DNAT / SNAT** | Destination / Source NAT — rewriting dst or src IP specifically |
| **DR** | Direct Routing — RS replies directly to client, bypassing the LB |

---

## L4 Load Balancing

L4 load balancers operate on **TCP/UDP connections**. They see only IP addresses and port numbers — no payload inspection. This makes them fast but limited in routing intelligence. The most fundamental L4 LB is **[LVS/IPVS]({{< ref "lvs" >}})** — a kernel module built into Linux that nearly every production L4 solution builds on or was inspired by.

### How It Works

```
Client: 1.2.3.4:50321
     │
     ▼  SYN to VIP:80
┌──────────────────┐
│   L4 LB          │
│                   │
│  1. Read: src IP, │
│     dst IP, ports │
│  2. Lookup conn   │
│     table         │
│  3. Schedule →    │
│     pick RS       │
│  4. Forward       │
│     (NAT/DR/TUN) │
└──┬────┬────┬─────┘
   │    │    │
   ▼    ▼    ▼
  RS1  RS2  RS3
```

Key points:
- **Connection-based**: once a connection is mapped to a backend, ALL packets in that connection go to the same RS
- **Protocol-agnostic**: works for any TCP/UDP traffic (HTTP, MySQL, Redis, gRPC, game servers)
- **No payload inspection**: cannot route based on URL path, HTTP headers, or cookies
- **No TLS termination required**: can passthrough encrypted traffic as-is

### Forwarding Modes

| Mode | Mechanism | LB sees return traffic? | Cross-subnet? | Throughput |
|---|---|---|---|---|
| **NAT** | Rewrite dst IP (+ src IP for SNAT) | Yes (bottleneck) | Yes | Low |
| **DR (Direct Routing)** | Rewrite dst MAC only | No (RS replies direct) | No (same L2) | High |
| **TUN (IP Tunneling)** | Encapsulate in outer IP header | No (RS replies direct) | Yes | High |

**DR** is the most common in production — the LB only handles inbound traffic (typically 10-100x smaller than responses), so throughput is maximized.

```
DR Mode:
                     request only
Client ──────▶ LB ──(MAC rewrite)──▶ RS
  ▲                                   │
  └──────────response (direct)────────┘
         LB never sees this
```

### Scheduling Algorithms

| Algorithm | How it picks a backend |
|---|---|
| Round Robin (rr) | Rotate through RS list in order |
| Weighted Round Robin (wrr) | Like rr, but higher-weight RS gets more turns |
| Least Connections (lc) | Pick the RS with fewest active connections |
| Weighted Least Conn (wlc) | `active_conns / weight` — lowest score wins (default in LVS) |
| Source Hash (sh) | Hash(client IP) → always same RS (session affinity) |
| Consistent Hashing | Minimize remapping when RS added/removed |

---

## L7 Load Balancing

L7 load balancers operate at the **application layer**. They fully parse the request (HTTP, gRPC, WebSocket) and can make routing decisions based on any part of the request content.

### How It Works

```
Client                        L7 LB                         Backends
  │                             │
  │── TCP connect ──▶           │
  │── TLS handshake ──▶        │   (TLS termination)
  │── HTTP request ──▶         │
  │   GET /api/users           │
  │   Host: api.example.com    │
  │   Cookie: session=abc      │
  │                             │
  │                  ┌──────────┴──────────┐
  │                  │ Parse request:       │
  │                  │  path = /api/users   │
  │                  │  host = api.example  │
  │                  │  cookie = abc        │
  │                  │                      │
  │                  │ Route rules:         │
  │                  │  /api/* → API pool   │
  │                  │  /static/* → CDN     │
  │                  │  header:canary → v2  │
  │                  └──────────┬──────────┘
  │                             │
  │                             │── new TCP + HTTP ──▶ [API Server 2]
  │◀── response ───────────────│◀── response ────────
```

Key points:
- **Content-aware routing**: route by URL path, hostname, headers, cookies, HTTP method, query params
- **TLS termination**: must decrypt to inspect content — then optionally re-encrypt to backend
- **Two TCP connections**: client↔LB and LB↔backend (the LB is a full reverse proxy)
- **Request manipulation**: can inject/modify headers (X-Forwarded-For, X-Request-Id), rewrite URLs

### Routing Capabilities

| Capability | Example |
|---|---|
| **Path-based** | `/api/*` → API servers, `/static/*` → CDN |
| **Host-based** | `api.example.com` → API pool, `web.example.com` → web pool |
| **Header-based** | `X-Canary: true` → canary deployment |
| **Cookie-based** | `session=abc` → sticky to specific backend |
| **Method-based** | `GET` → read replicas, `POST` → primary |
| **Weight-based** | 90% traffic → v1, 10% → v2 (canary/blue-green) |

### Advanced Features

- **Rate limiting**: per-client or per-path request rate control
- **Circuit breaking**: stop sending to unhealthy backends
- **Retry & timeout**: retry failed requests on a different backend
- **A/B testing**: split traffic by percentage or user attributes
- **Compression**: gzip/brotli responses before sending to client
- **WAF integration**: inspect request body for attacks (SQL injection, XSS)

---

## L4 vs L7 Comparison

| | L4 Load Balancing | L7 Load Balancing |
|---|---|---|
| **Performance** | Faster — no payload parsing, kernel-space possible | Slower — full request parsing in userspace |
| **Latency** | Lower — packet forwarding | Higher — proxy with two TCP connections |
| **Routing intelligence** | IP + port only | Full content (URL, headers, cookies) |
| **TLS** | Passthrough (no termination needed) | Must terminate to inspect |
| **Protocol support** | Any TCP/UDP | HTTP, gRPC, WebSocket (protocol-specific) |
| **Connection model** | Forwarding (same connection) | Proxying (two connections) |
| **Scalability** | Higher (less CPU per connection) | Lower (more CPU per request) |
| **Health checks** | TCP connect / port check | HTTP endpoint (`/healthz`) |
| **Visibility** | Blind to request content | Full request/response observability |
| **Use cases** | TCP services, databases, high-throughput, TLS passthrough | HTTP APIs, microservices, canary, A/B testing |

---

## Production Solutions

Large-scale systems typically **stack both layers**: L4 in front for raw throughput, L7 behind for intelligent routing.

```
Client
  │
  ▼
┌─────────────────┐
│   DNS (GSLB)    │  ← Geographic routing (Route53, Cloudflare DNS)
└────────┬────────┘
         ▼
┌─────────────────┐
│   L4 LB         │  ← High throughput, distribute TCP connections
│  (NLB / LVS)    │     TLS passthrough or termination
└────────┬────────┘
         ▼
┌─────────────────┐
│   L7 LB         │  ← Path routing, rate limiting, canary, headers
│ (Nginx / Envoy) │     TLS termination, request manipulation
└────────┬────────┘
         ▼
┌─────────────────┐
│  App Servers     │
│  (RS pool)       │
└─────────────────┘
```

### L4 Solutions

| Solution | Type | Throughput | Key Feature | Used By |
|---|---|---|---|---|
| **[LVS/IPVS]({{< ref "lvs" >}})** | Kernel module | Very high | In-kernel, DR mode, foundation of all L4 LB | Alibaba, Kubernetes (kube-proxy IPVS mode) |
| **AWS NLB** | Cloud | Very high | Static IP, millions RPS, TLS passthrough | AWS, Netflix |
| **HAProxy** (TCP mode) | Software | High | Battle-tested, rich ACL rules | GitHub, Stack Overflow |
| **Maglev** (Google) | Software (DPDK) | Extreme | Consistent hashing, kernel bypass | Google |
| **Katran** (Meta) | Software (XDP/BPF) | Extreme | eBPF-based, open source | Meta |
| **Unimog** | Software (DPDK/XDP) | Extreme | L4 LB for edge network | Cloudflare |
| **F5 BIG-IP** | Hardware/Software | Very high | Enterprise, hardware acceleration | Enterprise |

### L7 Solutions

| Solution | Type | Key Feature | Used By |
|---|---|---|---|
| **Nginx** | Software | Most widely deployed reverse proxy | Widely used |
| **Tengine** | Software | Nginx fork, enhanced for large scale | Alibaba |
| **Envoy** | Software | Cloud-native, sidecar in Istio service mesh | Lyft, K8s Ingress |
| **HAProxy** (HTTP mode) | Software | High perf, rich ACL rules | GitHub, Stack Overflow |
| **AWS ALB** | Cloud | Path/host routing, native AWS integration | AWS |
| **Zuul** | Software | Edge proxy with filters | Netflix |
| **Traefik** | Software | Auto-discovery with K8s, Docker | K8s environments |
| **Caddy** | Software | Auto HTTPS, simple config | Small/medium deployments |
| **Cloudflare / Akamai** | CDN/Edge | Global L7 LB + DDoS + WAF | Edge networks |

---

## Reference

- [Introduction to modern network load balancing and proxying](https://blog.envoyproxy.io/introduction-to-modern-network-load-balancing-and-proxying-a57f6ff80236) — Matt Klein (Envoy creator)
- [The Linux Virtual Server Project](http://www.linuxvirtualserver.org/)
- [Google Maglev Paper](https://research.google/pubs/pub44824/)
- [Meta Katran](https://github.com/facebookincubator/katran)
- [HAProxy Documentation](https://docs.haproxy.org/)
- [Nginx Load Balancing](https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/)
