---
title: "WebSocket"
date: 2026-03-26T10:00:00+08:00
tags: ["network"]
description: "WebSocket protocol overview"
---

WebSocket ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)) provides full-duplex, bidirectional communication over a single TCP connection. Here's a summary of the protocol.

## Background & Motivation

HTTP follows a request-response model — the client sends a request, the server replies. This works well for loading web pages, but falls short for real-time applications (chat, gaming, live dashboards) where the server needs to push data to the client at any time.

Before WebSocket, developers used workarounds:

| Technique | How It Works | Drawbacks |
|-----------|-------------|-----------|
| **Polling** | Client repeatedly sends HTTP requests at intervals | Wasteful — most responses are empty; high latency |
| **Long Polling** | Client sends request, server holds it open until data is available | Still one-directional; connection overhead on each response |
| **SSE** | Server pushes events over a long-lived HTTP connection | Unidirectional (server→client only); limited to text; 6 connections per domain under HTTP/1.1 |

All of these are hacks layered on top of HTTP's request-response model. WebSocket solves this at the protocol level.

## What Is It & How It Works

WebSocket is a protocol that upgrades an HTTP connection into a persistent, full-duplex channel. After the initial handshake, both client and server can send messages independently at any time over the same TCP connection.

Key characteristics:
- **Built on TCP**: the HTTP upgrade handshake and all subsequent WebSocket frames share the same TCP connection — "upgrade" switches the application protocol, not the transport
- **Full-duplex**: both sides send/receive simultaneously
- **Low overhead**: no HTTP headers on every message — just a small frame header (2-14 bytes)
- **URI schemes**: `ws://` (plaintext) and `wss://` (TLS-encrypted, analogous to HTTPS)

```
Traditional HTTP:
  Client ──req──▶ Server
  Client ◀──res── Server
  Client ──req──▶ Server
  Client ◀──res── Server

WebSocket (all over the same TCP connection):
  Client ──HTTP Upgrade──▶ Server     ← TCP + HTTP
  Client ◀──101 Switching── Server    ← TCP + HTTP
         ╔═══════════════╗
  Client ◀══════════════▶ Server      ← TCP + WebSocket frames
         ╚═══════════════╝
```

## Protocol Details

### Opening Handshake

The connection starts as a standard HTTP/1.1 request with an `Upgrade` header:

**Client Request:**
```
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: http://example.com
```

**Server Response:**
```
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

The `Sec-WebSocket-Accept` is computed as:
```
Base64(SHA-1(Sec-WebSocket-Key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))
```

This is not for security — it simply confirms the server understands WebSocket and prevents accidental upgrades.

### Framing Protocol

After the handshake, data is transmitted as **frames**. Let's walk through the entire echo example — from handshake to close — showing the actual bytes on the wire.

#### Frame Structure

Each frame has a small header followed by payload data:

```
     Byte 0          Byte 1          Byte 2          Byte 3
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
```

Key fields:
- **FIN** (1 bit): 1 = final fragment, 0 = more fragments follow
- **Opcode** (4 bits): `0x1` text, `0x2` binary, `0x8` close, `0x9` ping, `0xA` pong, `0x0` continuation
- **MASK** (1 bit): 1 = payload is masked (required for client→server)
- **Payload len** (7 bits): The 7-bit field can hold values 0–127. Values 126 and 127 are **not** actual lengths — they are sentinels signaling "read more bytes for the real length":

| 7-bit value | Meaning | Bytes used for length |
|---|---|---|
| 0–125 | Value **is** the payload length. Done. | 1 (the 7-bit field itself) |
| 126 | Real length in the **next 2 bytes** (up to 64 KB) | 3 (7-bit field + 2 bytes) |
| 127 | Real length in the **next 8 bytes** (up to 2^63) | 9 (7-bit field + 8 bytes) |

This is a space optimization — most WebSocket messages are small, so they only need 1 byte for length instead of wasting 8 bytes every time.

#### Dry Run: Echo "hello websocket"

The payload is `"hello websocket"` = 15 bytes. Assume masking key = `0x37 0xFA 0x21 0x3D`.

**Step 1 — Opening Handshake (HTTP)**

```
Client → Server:
  GET /ws HTTP/1.1
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
  Sec-WebSocket-Version: 13

Server → Client:
  HTTP/1.1 101 Switching Protocols
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

Connection upgraded. From now on, only WebSocket frames are exchanged over this TCP connection.

**Step 2 — Client sends "hello websocket" (masked)**

Client→server frames **must** be masked. The masking XORs each payload byte with the key:

```
payload:  h     e     l     l     o           w     e     b     s     o     c     k     e     t
hex:      0x68  0x65  0x6C  0x6C  0x6F  0x20  0x77  0x65  0x62  0x73  0x6F  0x63  0x6B  0x65  0x74
mask key: 0x37  0xFA  0x21  0x3D  0x37  0xFA  0x21  0x3D  0x37  0xFA  0x21  0x3D  0x37  0xFA  0x21
XOR:      0x5F  0x9F  0x4D  0x51  0x58  0xDA  0x56  0x58  0x55  0x89  0x4E  0x5E  0x5C  0x9F  0x55
```

The frame on the wire:
```
Byte:  0x81  0x8F  0x37  0xFA  0x21  0x3D  0x5F  0x9F  0x4D  ... (15 bytes masked payload)
       ────  ────  ──────────────────────  ─────────────────────────────────────────────────
       │     │     │                       └─ Masked payload data
       │     │     └─ Masking key (4 bytes)
       │     └─ MASK=1, Payload len=15 (0b_1_0001111 = 0x8F)
       └─ FIN=1, opcode=0x1 text (0b_1000_0001 = 0x81)
```

Total frame size: 2 (header) + 4 (mask key) + 15 (payload) = **21 bytes**

**Step 3 — Server echoes "hello websocket" (unmasked)**

Server→client frames are **not** masked, so the payload is sent in plaintext:

```
Byte:  0x81  0x0F  0x68  0x65  0x6C  0x6C  0x6F  0x20  0x77  ... (15 bytes raw payload)
       ────  ────  ─────────────────────────────────────────────────────────────────────
       │     │     └─ Payload data: "hello websocket" in UTF-8
       │     └─ MASK=0, Payload len=15 (0b_0_0001111 = 0x0F)
       └─ FIN=1, opcode=0x1 text (0x81)
```

Total frame size: 2 (header) + 15 (payload) = **17 bytes**. No mask key needed.

**Step 4 — Close Handshake**

Client initiates close with status code 1000 (normal closure):

```
Client → Server (masked close frame):
  Byte:  0x88  0x82  0x37  0xFA  0x21  0x3D  0x34  0x12
         ────  ────  ──────────────────────  ────────────
         │     │     │                       └─ Masked status code 1000
         │     │     │                          (0x03E8 XOR 0x37FA = 0x3412)
         │     │     └─ Masking key
         │     └─ MASK=1, Payload len=2
         └─ FIN=1, opcode=0x8 close (0x88)

Server → Client (unmasked close frame):
  Byte:  0x88  0x02  0x03  0xE8
         ────  ────  ────────────
         │     │     └─ Status code 1000 (0x03E8)
         │     └─ MASK=0, Payload len=2
         └─ FIN=1, opcode=0x8 close (0x88)
```

After both sides exchange close frames, the underlying TCP connection is terminated.

#### Summary

The full exchange:
```
Client                                          Server
  │                                               │
  │──── HTTP GET (Upgrade: websocket) ──────────▶│
  │◀─── HTTP 101 Switching Protocols ────────────│
  │                                               │
  │  ---- WebSocket frames over same TCP conn --- │
  │                                               │
  │──── [0x81 0x8F ...] text "hello websocket" ─▶│  (masked, 21 bytes)
  │◀─── [0x81 0x0F ...] text "hello websocket" ──│  (unmasked, 17 bytes)
  │                                               │
  │──── [0x88 0x82 ...] close (1000) ───────────▶│  (masked)
  │◀─── [0x88 0x02 ...] close (1000) ────────────│  (unmasked)
  │                                               │
  │──── TCP FIN ────────────────────────────────▶│
  │◀─── TCP FIN ─────────────────────────────────│
```

**Why mask client→server only?** The mask prevents cache-poisoning attacks where a malicious client crafts payloads that look like valid HTTP responses to confuse intermediary proxies. Since servers are trusted, server→client frames don't need masking.

#### Common Close Status Codes

| Code | Meaning |
|------|---------|
| 1000 | Normal closure |
| 1001 | Going away (e.g. server shutdown, page navigated away) |
| 1002 | Protocol error |
| 1003 | Unsupported data type |
| 1006 | Abnormal closure (no Close frame received) |
| 1011 | Unexpected server error |

### Closing Handshake

Either side can initiate closure by sending a Close frame (opcode `0x8`):

```
1. Client sends Close frame (status code + optional reason)
2. Server responds with Close frame
3. TCP connection is terminated
```

Common status codes:

| Code | Meaning |
|------|---------|
| 1000 | Normal closure |
| 1001 | Going away (e.g. server shutdown, page navigated away) |
| 1002 | Protocol error |
| 1003 | Unsupported data type |
| 1006 | Abnormal closure (no Close frame received) |
| 1011 | Unexpected server error |

## Usage & Use Cases

### When to Use WebSocket

- **Chat / messaging**: bidirectional, low-latency message exchange
- **Online gaming**: real-time game state synchronization
- **Collaborative editing**: multiple users editing the same document
- **Live dashboards**: streaming metrics, stock tickers, sports scores
- **AI agent workflows**: multi-turn interactions with human-in-the-loop approval

### When NOT to Use WebSocket

| Scenario | Better Alternative | Why |
|----------|--------------------|-----|
| Server pushes updates, client only listens | **SSE** | Simpler, auto-reconnect, works with HTTP/2 multiplexing |
| Standard request-response API | **HTTP REST** | No need for persistent connection |
| File upload / download | **HTTP** | WebSocket has no built-in content-type or caching |
| One-off data fetch | **HTTP** | Connection setup overhead not justified |

### Comparison

| Feature | WebSocket | SSE | HTTP Polling |
|---------|-----------|-----|-------------|
| Direction | Bidirectional | Server → Client | Client → Server (simulated) |
| Protocol | `ws://` / `wss://` | HTTP | HTTP |
| Overhead per message | 2-14 bytes (frame header) | ~50 bytes (event format) | Full HTTP headers each time |
| Binary support | Yes | No (text only) | Yes |
| Auto-reconnect | No (manual) | Yes (built-in) | N/A |
| Connection limit (HTTP/1.1) | Browser-dependent | 6 per domain | 6 per domain |
| Proxy/firewall friendly | Sometimes blocked | Yes | Yes |

## Hands-On Demo

A minimal echo server and client in Go using `gorilla/websocket`:

**Server (`server.go`):**
```go
package main

import (
	"fmt"
	"log"
	"net/http"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

func echo(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("upgrade:", err)
		return
	}
	defer conn.Close()

	for {
		msgType, msg, err := conn.ReadMessage()
		if err != nil {
			log.Println("read:", err)
			break
		}
		fmt.Printf("recv: %s\n", msg)
		if err := conn.WriteMessage(msgType, msg); err != nil {
			log.Println("write:", err)
			break
		}
	}
}

func main() {
	http.HandleFunc("/ws", echo)
	log.Println("server started on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
```

**Client (`client.go`):**
```go
package main

import (
	"fmt"
	"log"

	"github.com/gorilla/websocket"
)

func main() {
	conn, _, err := websocket.DefaultDialer.Dial("ws://localhost:8080/ws", nil)
	if err != nil {
		log.Fatal("dial:", err)
	}
	defer conn.Close()

	// Send a message
	msg := "hello websocket"
	if err := conn.WriteMessage(websocket.TextMessage, []byte(msg)); err != nil {
		log.Fatal("write:", err)
	}
	fmt.Println("sent:", msg)

	// Read the echo
	_, reply, err := conn.ReadMessage()
	if err != nil {
		log.Fatal("read:", err)
	}
	fmt.Println("recv:", string(reply))
}
```

**Run it:**
```shell
# Terminal 1
go run server.go

# Terminal 2
go run client.go
# Output:
# sent: hello websocket
# recv: hello websocket
```

You can also test with `wscat` (a CLI WebSocket client):
```shell
# Install
npm install -g wscat

# Connect to the echo server
wscat -c ws://localhost:8080/ws
> hello
< hello
```

## References

- [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [WebSocket Protocol Guide — websocket.org](https://websocket.org/guides/websocket-protocol/)
- [MDN — WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [gorilla/websocket — Go WebSocket library](https://github.com/gorilla/websocket)
