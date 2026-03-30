---
title: "HTTP: The Evolution from 0.9 to 3"
date: "2026-03-28T10:00:00+08:00"
tags: ["network", "http"]
description: "A comprehensive overview of HTTP protocol evolution — from the one-line HTTP/0.9 to HTTP/3 over QUIC"
---

## Background & Motivation

In 1989, Tim Berners-Lee proposed a hypertext system at CERN. By 1991, the first version of HTTP was born — a protocol so simple it fit in a few hundred words. Over the next three decades, HTTP evolved through five major versions, each solving the limitations of its predecessor:

```
1991        1996        1997           2015        2022
 │           │           │              │           │
 ▼           ▼           ▼              ▼           ▼
HTTP/0.9 → HTTP/1.0 → HTTP/1.1 ────→ HTTP/2 ──→ HTTP/3
 │           │           │              │           │
 GET only    Headers     Persistent     Binary      QUIC
 HTML only   Status      Connections    Multiplex   over UDP
             Codes       Pipelining     HPACK       0-RTT
```

## HTTP/0.9 — The One-Line Protocol (1991)

The simplest possible protocol for fetching hypertext.

- Only one method: `GET`
- No headers, no status codes, no version number
- Server responds with HTML only, then closes the connection

```
Request:   GET /index.html

Response:  <html>Hello World</html>
           [connection closed]
```

## HTTP/1.0 — Building Extensibility (1996)

RFC 1945 introduced the building blocks we still use today.

- Version info appended to request line (`GET /page HTTP/1.0`)
- **Headers** for both request and response — metadata becomes first-class
- **Status codes** (`200 OK`, `404 Not Found`, etc.)
- `Content-Type` header — not just HTML anymore (images, CSS, etc.)
- New methods: `POST`, `HEAD`

```
Request:
  GET /page.html HTTP/1.0
  User-Agent: NCSA_Mosaic/2.0
  Accept: text/html

Response:
  HTTP/1.0 200 OK
  Content-Type: text/html
  Content-Length: 137

  <html>...</html>
  [connection closed]
```

**Problem:** One TCP connection per request. Fetching a page with 10 images = 11 TCP handshakes.

```
Client                  Server
  │──── TCP SYN ──────────▶│
  │◀─── SYN-ACK ───────────│
  │──── ACK ──────────────▶│  Request 1: GET /index.html
  │──── GET /index.html ──▶│
  │◀─── 200 OK ────────────│
  │──── FIN ──────────────▶│  [connection closed]
  │                         │
  │──── TCP SYN ──────────▶│
  │◀─── SYN-ACK ───────────│
  │──── ACK ──────────────▶│  Request 2: GET /style.css
  │──── GET /style.css ───▶│
  │◀─── 200 OK ────────────│
  │──── FIN ──────────────▶│  [connection closed]
  ...                      ...
```

Non-standard workaround: `Connection: keep-alive` header to reuse TCP connections.

## HTTP/1.1 — The Workhorse (1997)

RFC 2068 (1997), refined in RFC 2616 (1999), then RFC 9110-9112 (2022). The protocol that powered the web for nearly 20 years.

### Key Features

- **Persistent connections by default** — no more `Connection: keep-alive` hack
- **Pipelining** — send multiple requests without waiting for responses
- **Chunked transfer encoding** — stream responses via `Transfer-Encoding: chunked`
- **Host header** — enables virtual hosting (multiple domains on one IP)
- **Cache control** — `Cache-Control`, `ETag`, `If-None-Match`, `If-Modified-Since`
- **Content negotiation** — `Accept`, `Accept-Language`, `Accept-Encoding`

### Pipelining vs Sequential

```
Sequential (HTTP/1.0):          Pipelined (HTTP/1.1):

Client        Server            Client        Server
  │─ GET A ────▶│                 │─ GET A ────▶│
  │◀──── A ─────│                 │─ GET B ────▶│
  │─ GET B ────▶│                 │─ GET C ────▶│
  │◀──── B ─────│                 │◀──── A ─────│
  │─ GET C ────▶│                 │◀──── B ─────│
  │◀──── C ─────│                 │◀──── C ─────│
```

### Head-of-Line (HOL) Blocking

Even with pipelining, **responses must be returned in order**. If response A is slow, B and C are blocked behind it — this is head-of-line blocking.

```
Client        Server
  │─ GET A ────▶│
  │─ GET B ────▶│   A is slow (large file / DB query)
  │─ GET C ────▶│
  │    ...wait...│   B and C are ready, but must wait for A
  │◀──── A ─────│
  │◀──── B ─────│
  │◀──── C ─────│
```

**Practical workaround:** Browsers open **6 parallel TCP connections** per origin. But each connection still suffers from HOL blocking internally.

## HTTP/2 — Binary & Multiplexed (2015)

RFC 7540 (2015), updated in RFC 9113 (2022). Born from Google's SPDY protocol (2009).

### Binary Framing Layer

HTTP/2 replaces the text-based protocol with a binary framing layer. All communication is split into **frames**, carried over **streams** within a single TCP connection.

```
┌──────────────────────────────────────────────────────┐
│                  TCP Connection                       │
│                                                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐              │
│  │ Stream 1│  │ Stream 3│  │ Stream 5│  ...          │
│  │(req/res)│  │(req/res)│  │(req/res)│               │
│  └─────────┘  └─────────┘  └─────────┘              │
│                                                      │
│  Frames interleaved on the wire:                     │
│  [S1:HEADERS][S3:HEADERS][S1:DATA][S5:HEADERS]       │
│  [S3:DATA][S1:DATA][S5:DATA][S3:DATA]...             │
└──────────────────────────────────────────────────────┘
```

### Frame Structure

```
+-----------------------------------------------+
|                Length (24 bits)                |
+---------------+-------------------------------+
| Type (8 bits) | Flags (8 bits)                |
+-+-------------+-------------------------------+
|R|         Stream Identifier (31 bits)         |
+=+=============+===============================+
|              Frame Payload (variable)          |
+-----------------------------------------------+
```

Key frame types:
| Frame Type   | Purpose                        |
|-------------|--------------------------------|
| `HEADERS`   | Request/response headers        |
| `DATA`      | Request/response body           |
| `SETTINGS`  | Connection configuration        |
| `PUSH_PROMISE` | Server push notification     |
| `RST_STREAM` | Cancel a stream               |
| `GOAWAY`    | Graceful connection shutdown    |
| `WINDOW_UPDATE` | Flow control               |

### Key Mechanisms

- **Multiplexing** — multiple requests/responses interleaved on one TCP connection, no HOL blocking at HTTP layer
- **HPACK** — header compression using static/dynamic tables and Huffman encoding. Repeated headers (e.g. `User-Agent`) sent once, then referenced by index
- **Server Push** — server proactively sends resources before the client requests them (e.g. push `style.css` when `/index.html` is requested)
- **Stream Prioritization** — clients assign weights and dependencies to streams

### The Remaining Problem: TCP-Level HOL Blocking

HTTP/2 solved HOL blocking at the HTTP layer, but **TCP itself is still ordered**. If a single TCP packet is lost, **all streams** are blocked until that packet is retransmitted.

```
                  HTTP/2 over TCP

Stream 1: ■ ■ ■ ■ ■ ■
Stream 2: □ □ □ □ □ □
Stream 3: ▪ ▪ ▪ ▪ ▪ ▪

TCP layer: ■ □ ▪ ■ □ ▪ ■ [✗ lost] □ ▪ ■ □ ▪
                               ▲
                    ALL streams blocked here
                    until retransmit completes
```

On lossy networks (mobile, Wi-Fi), HTTP/2 can actually be **slower** than HTTP/1.1 with 6 parallel connections.

## HTTP/3 — QUIC Revolution (2022)

RFC 9114 (2022). The fundamental change: replace TCP with **QUIC** (RFC 9000), a new transport protocol built on UDP.

### Protocol Stack Comparison

```
HTTP/1.1 & HTTP/2:              HTTP/3:

┌──────────────┐               ┌──────────────┐
│   HTTP/1.1   │               │    HTTP/3    │
│   or HTTP/2  │               ├──────────────┤
├──────────────┤               │     QUIC     │
│     TLS      │               │  (includes   │
├──────────────┤               │   TLS 1.3)   │
│     TCP      │               ├──────────────┤
├──────────────┤               │     UDP      │
│      IP      │               ├──────────────┤
└──────────────┘               │      IP      │
                               └──────────────┘
```

### Handshake: TCP+TLS vs QUIC

```
TCP + TLS 1.3 (2-RTT):           QUIC (1-RTT):

Client        Server              Client        Server
  │─ SYN ────────▶│                │─ Initial ───▶│
  │◀──── SYN-ACK ─│  1 RTT         │  (crypto +   │
  │─ ACK ─────────▶│               │   request)   │
  │─ ClientHello ─▶│                │◀── Handshake─│  1 RTT
  │◀── ServerHello─│  2 RTT         │  (crypto +   │
  │─ Finished ────▶│               │   response)  │
  │◀── Finished ───│                │              │
  │─ Request ─────▶│  3 RTT         │  Done!       │
  │◀── Response ───│               │              │


QUIC 0-RTT (returning client):

Client        Server
  │─ Initial ───▶│
  │  (crypto +   │  0 RTT for data!
  │   request)   │  (crypto from previous session)
  │◀── Response ─│
```

### Key Features

**Independent Stream Recovery** — The core breakthrough. Unlike TCP, QUIC handles packet loss per-stream. Lost packets in Stream 1 don't block Stream 2 or 3.

```
                  HTTP/3 over QUIC

Stream 1: ■ ■ ■ [✗] ■ ■     ← only Stream 1 waits
Stream 2: □ □ □  □  □ □     ← unaffected
Stream 3: ▪ ▪ ▪  ▪  ▪ ▪     ← unaffected
```

**Connection Migration** — QUIC uses **Connection IDs** instead of the traditional 4-tuple (src IP, src port, dst IP, dst port). When your phone switches from Wi-Fi to cellular, the connection survives.

```
Phone (Wi-Fi)                      Server
  │── CID: 0xABCD ──── req ────────▶│
  │◀──────────────────── res ────────│
  │                                  │
  [Wi-Fi → Cellular]                 │
  │                                  │
Phone (Cellular)                     │
  │── CID: 0xABCD ──── req ────────▶│  Same connection!
  │◀──────────────────── res ────────│
```

**QPACK** — Header compression adapted for QUIC. Similar to HPACK but designed to work without strict ordering (since QUIC streams are independent).

**Built-in Encryption** — TLS 1.3 is mandatory and integrated into the transport layer. No unencrypted HTTP/3 connections exist.

## Comparison

| Feature | HTTP/1.0 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---------|----------|----------|--------|--------|
| **Year** | 1996 | 1997 | 2015 | 2022 |
| **RFC** | 1945 | 9110-9112 | 9113 | 9114 |
| **Format** | Text | Text | Binary | Binary |
| **Transport** | TCP | TCP | TCP | QUIC (UDP) |
| **Connections** | 1 per request | Persistent | Single multiplexed | Single multiplexed |
| **Multiplexing** | No | No (pipelining) | Yes | Yes |
| **HOL Blocking** | Yes | Yes | TCP-level | No |
| **Header Compression** | No | No | HPACK | QPACK |
| **Server Push** | No | No | Yes | Yes |
| **Encryption** | Optional | Optional | Optional (practical: required) | Always (TLS 1.3) |
| **Connection Migration** | No | No | No | Yes |
| **0-RTT** | No | No | No | Yes |

## Hands-On Demo

### Check HTTP version with curl

```shell
# Force HTTP/1.1
curl -I --http1.1 https://www.google.com 2>&1 | head -1
# HTTP/1.1 200 OK

# Force HTTP/2
curl -I --http2 https://www.google.com 2>&1 | head -1
# HTTP/2 200

# Force HTTP/3 (requires curl 7.88+ built with HTTP/3 support)
curl -I --http3 https://www.google.com 2>&1 | head -1
# HTTP/3 200
```

| Flag | Meaning |
|------|---------|
| `-I` | Fetch headers only (sends a HEAD request) |
| `--http1.1` / `--http2` / `--http3` | Force a specific HTTP version |
| `2>&1` | Redirect stderr to stdout (curl outputs connection info to stderr) |
| `head -1` | Show only the first line (the status line) |

### Verbose connection info

```shell
# See the full handshake and protocol negotiation
curl -v --http2 https://www.google.com -o /dev/null 2>&1 | grep -E '(ALPN|HTTP/|SSL)'

# Example output:
# * ALPN: curl offers h2,http/1.1
# * ALPN: server accepted h2
# * using HTTP/2
# * SSL connection using TLSv1.3
```

| Flag | Meaning |
|------|---------|
| `-v` | Verbose mode — shows handshake and protocol negotiation details |
| `-o /dev/null` | Discard the response body |
| `grep -E '...'` | Filter output with extended regex for protocol negotiation lines |

### Check HTTP/3 support for a domain

```shell
# HTTP/3 is advertised via Alt-Svc header
curl -sI https://www.google.com | grep -i alt-svc
# alt-svc: h3=":443"; ma=2592000,h3-29=":443"; ma=2592000
```

| Flag | Meaning |
|------|---------|
| `-s` | Silent mode — suppress progress bar |
| `-I` | Fetch headers only |
| `grep -i` | Case-insensitive search for the `Alt-Svc` header |

## References

- [RFC 1945 — HTTP/1.0](https://datatracker.ietf.org/doc/html/rfc1945)
- [RFC 9110-9112 — HTTP Semantics, HTTP/1.1](https://datatracker.ietf.org/doc/html/rfc9110)
- [RFC 9113 — HTTP/2](https://datatracker.ietf.org/doc/html/rfc9113)
- [RFC 9114 — HTTP/3](https://datatracker.ietf.org/doc/html/rfc9114)
- [RFC 9000 — QUIC](https://datatracker.ietf.org/doc/html/rfc9000)
- [Evolution of HTTP — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Evolution_of_HTTP)
- [HTTP/3 explained — Daniel Stenberg](https://http3-explained.haxx.se/)
