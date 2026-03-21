---
title: "Netty"
date: 2026-03-19T00:00:00+08:00
tags: ["java", "netty", "networking"]
description: "Netty: high-performance async network framework in Java"
draft: true
---

## 1. Why Netty Exists

### The Problem: Java's I/O Evolution

Java has gone through three generations of network I/O:

```
Gen 1: java.io (BIO)        → 1 thread per connection → doesn't scale
Gen 2: java.nio (NIO)       → non-blocking, selector-based → scales but painful API
Gen 3: Netty (NIO framework) → clean API on top of NIO → scales AND developer-friendly
```

### BIO — Blocking I/O (java.io)

```
Server
  │
  ▼
accept() ──► Thread-1 ──► read()/write() [BLOCKS until data ready]
accept() ──► Thread-2 ──► read()/write() [BLOCKS]
accept() ──► Thread-3 ──► read()/write() [BLOCKS]
  ...
accept() ──► Thread-10000 → OOM / context switch overhead
```

| Problem | Impact |
|---------|--------|
| 1 thread per connection | 10K connections = 10K threads |
| Thread blocked on I/O | CPU idle but thread occupied |
| Context switching overhead | OS spends more time switching than doing work |
| Memory waste | Each thread ~512KB-1MB stack space |

**BIO cannot handle C10K (10,000 concurrent connections).**

### NIO — Non-blocking I/O (java.nio)

Java 1.4 introduced NIO with `Selector`, `Channel`, and `Buffer`:

```
                  ┌─── Channel A (readable)
Selector ────────┼─── Channel B (writable)
(1 thread polls)  ├─── Channel C (idle, skip)
                  └─── Channel D (readable)
```

One thread monitors many connections via `select()` / `epoll()`. Only processes channels that are ready.

**NIO solves the scalability problem, but the API is brutal:**

```java
// Raw NIO — 100+ lines just for a simple echo server
Selector selector = Selector.open();
ServerSocketChannel serverChannel = ServerSocketChannel.open();
serverChannel.configureBlocking(false);
serverChannel.bind(new InetSocketAddress(8080));
serverChannel.register(selector, SelectionKey.OP_ACCEPT);

while (true) {
    selector.select();
    Set<SelectionKey> keys = selector.selectedKeys();
    Iterator<SelectionKey> iter = keys.iterator();
    while (iter.hasNext()) {
        SelectionKey key = iter.next();
        iter.remove();
        if (key.isAcceptable()) {
            SocketChannel client = serverChannel.accept();
            client.configureBlocking(false);
            client.register(selector, SelectionKey.OP_READ);
        } else if (key.isReadable()) {
            SocketChannel client = (SocketChannel) key.channel();
            ByteBuffer buf = ByteBuffer.allocate(1024);
            int n = client.read(buf);
            if (n == -1) { client.close(); continue; }
            buf.flip();  // easy to forget → subtle bugs
            client.write(buf);
        }
    }
}
```

| NIO Pain Point | Description |
|----------------|-------------|
| ByteBuffer API | `flip()`, `compact()`, `clear()` — confusing state machine |
| Epoll bug (JDK) | Selector wakes up spuriously with 100% CPU (fixed late, workaround needed) |
| No built-in codec | Must manually handle half-packet / sticky-packet problems |
| Complex threading | Managing multiple Selectors across threads is error-prone |
| No connection management | Heartbeat, reconnection, idle detection — all DIY |

### Netty — The Solution

Netty wraps NIO with a clean, event-driven API that handles all the hard parts:

```
Raw NIO Pain                    Netty Solution
─────────────────────────────   ─────────────────────────────
ByteBuffer confusion        →   ByteBuf (ref-counted, pooled)
Manual selector management  →   EventLoopGroup (auto-managed)
Half-packet / sticky-packet →   Built-in codecs (LengthFieldBasedFrameDecoder...)
No pipeline                 →   ChannelPipeline (handler chain)
Threading complexity        →   Reactor model built-in
Epoll bug                   →   Workaround built-in
```

---

## 2. Core Design: Reactor Pattern

Netty is built on the **Reactor pattern** — an event-driven design for handling concurrent I/O.

### Single Reactor (concept)

```
                        ┌──────────────┐
  Incoming connections  │   Reactor    │
  ─────────────────────►│  (Selector)  │
                        │              │
                        │  Event Loop  │─── detect events ──► dispatch to handlers
                        └──────────────┘
```

### Netty's Multi-Reactor: Boss + Worker

```
                    ┌─────────────────┐
  Client connects → │   Boss Group    │  (1-2 threads)
                    │  (accept only)  │
                    └────────┬────────┘
                             │ register new connection
                             ▼
                    ┌─────────────────┐
                    │  Worker Group   │  (N threads, default = CPU cores * 2)
                    │                 │
                    │  EventLoop-1 ──►│── Channel A, Channel D
                    │  EventLoop-2 ──►│── Channel B, Channel E
                    │  EventLoop-3 ──►│── Channel C, Channel F
                    └─────────────────┘
```

| Component | Role |
|-----------|------|
| **BossGroup** | Accepts new connections, registers them to a Worker |
| **WorkerGroup** | Handles I/O read/write + execute handlers for assigned channels |
| **EventLoop** | Single thread + Selector + task queue. One channel binds to one EventLoop for its lifetime (no synchronization needed) |

**Key insight:** One channel is always handled by the same EventLoop thread — this eliminates most concurrency issues without locks.

---

## 3. Architecture & Core Components

```
┌───────────────────────────────────────────────┐
│                  Bootstrap                     │  ← entry point (config)
├───────────────────────────────────────────────┤
│              EventLoopGroup                    │  ← thread pool of EventLoops
│  ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │EventLoop│ │EventLoop│ │EventLoop│ ...      │
│  │(thread) │ │(thread) │ │(thread) │          │
│  └─────────┘ └─────────┘ └─────────┘         │
├───────────────────────────────────────────────┤
│                 Channel                        │  ← wraps socket
│  ┌───────────────────────────────────────┐    │
│  │          ChannelPipeline               │    │  ← handler chain
│  │                                        │    │
│  │  Inbound:   Decoder → BizHandler       │    │
│  │  Outbound:  BizHandler → Encoder       │    │
│  └───────────────────────────────────────┘    │
├───────────────────────────────────────────────┤
│                  ByteBuf                       │  ← buffer (pooled, ref-counted)
└───────────────────────────────────────────────┘
```

### 3.1 Bootstrap

```java
// Server setup — clean and declarative
ServerBootstrap b = new ServerBootstrap();
b.group(bossGroup, workerGroup)           // reactor groups
 .channel(NioServerSocketChannel.class)   // transport type
 .childHandler(new ChannelInitializer<SocketChannel>() {
     @Override
     protected void initChannel(SocketChannel ch) {
         ch.pipeline().addLast(new LineBasedFrameDecoder(1024));  // codec
         ch.pipeline().addLast(new StringDecoder());
         ch.pipeline().addLast(new EchoServerHandler());         // business logic
     }
 });
b.bind(8080).sync();
```

### 3.2 ChannelPipeline — The Handler Chain

The pipeline is a **doubly-linked list** of handlers. Inbound events flow forward, outbound events flow backward:

```
                         ChannelPipeline
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  Inbound (read):                                        │
  │  Socket → Head → Decoder → BizHandler → Tail            │
  │           ──────────────────────────►                    │
  │                                                         │
  │  Outbound (write):                                      │
  │  Socket ← Head ← Encoder ← BizHandler ← Tail           │
  │           ◄──────────────────────────                    │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

| Handler Type | Direction | Examples |
|-------------|-----------|---------|
| `ChannelInboundHandler` | Socket → App | Decoders, business logic |
| `ChannelOutboundHandler` | App → Socket | Encoders, write logic |
| `ChannelDuplexHandler` | Both | Idle state handler |

### 3.3 ByteBuf — Better than ByteBuffer

```
ByteBuffer (JDK NIO):
  - Single position pointer → must flip() between read/write
  - Fixed capacity → no dynamic expansion
  - Unpooled → GC pressure

ByteBuf (Netty):
  ┌──────────────────────────────────────────┐
  │  0...readerIndex...writerIndex...capacity │
  │  [discardable] [readable]  [writable]    │
  └──────────────────────────────────────────┘
  - Separate read/write index → no flip()
  - Dynamic expansion
  - Pooled (PooledByteBufAllocator) → reuse memory, less GC
  - Reference counted → explicit lifecycle management
  - Supports composite buffers (zero-copy merge)
```

| Feature | ByteBuffer (JDK) | ByteBuf (Netty) |
|---------|------------------|-----------------|
| Read/Write index | Single `position` | Separate `readerIndex` / `writerIndex` |
| flip() needed | Yes | No |
| Dynamic resize | No | Yes |
| Pooled | No | Yes (PooledByteBufAllocator) |
| Reference counting | No | Yes |
| Zero-copy composite | No | `CompositeByteBuf` |

### 3.4 EventLoop — The Heart

```
┌────────────────────────────────────────┐
│              EventLoop                  │
│                                         │
│  ┌─── Single Thread ───────────────┐   │
│  │                                  │   │
│  │  1. selector.select()           │   │ ← poll I/O events
│  │  2. process selected keys       │   │ ← handle I/O
│  │  3. run pending tasks           │   │ ← execute submitted tasks
│  │  4. run scheduled tasks         │   │ ← delayed/periodic tasks
│  │                                  │   │
│  │  loop forever                    │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Channel-A ─┐                           │
│  Channel-B ─┤ bound to this EventLoop   │
│  Channel-C ─┘ (for their lifetime)      │
└────────────────────────────────────────┘
```

**I/O ratio:** Netty balances time between I/O events and task execution (default 50:50, configurable via `ioRatio`).

---

## 4. How a Request Flows Through Netty

```
Step 1: Client connects
        │
        ▼
Step 2: BossGroup EventLoop detects OP_ACCEPT
        │
        ▼
Step 3: Create SocketChannel, init pipeline (ChannelInitializer)
        │
        ▼
Step 4: Register channel to a WorkerGroup EventLoop
        │
        ▼
Step 5: WorkerGroup EventLoop detects OP_READ
        │
        ▼
Step 6: Read bytes into ByteBuf
        │
        ▼
Step 7: Fire through ChannelPipeline:
        │
        │   ByteBuf
        │     │
        │     ▼
        │   Decoder (e.g., LengthFieldBasedFrameDecoder)
        │     │
        │     ▼
        │   Decoder (e.g., StringDecoder)
        │     │
        │     ▼
        │   Business Handler (your code)
        │     │
        │     ▼
        │   Encoder (e.g., StringEncoder)
        │     │
        │     ▼
        │   Write to socket
        │
        ▼
Step 8: Response sent to client
```

---

## 5. Solving Half-Packet & Sticky-Packet

TCP is a **byte stream** protocol — it has no message boundaries. Two common problems:

```
Sent:     [MSG-A][MSG-B]        [MSG-C]
Received: [MSG-A + partial MSG-B] [rest of MSG-B + MSG-C]
           ↑ sticky-packet          ↑ half-packet
```

Netty provides built-in frame decoders:

| Decoder | Strategy | Example |
|---------|----------|---------|
| `FixedLengthFrameDecoder` | Fixed-size messages | Each message is exactly 64 bytes |
| `LineBasedFrameDecoder` | Delimiter `\n` or `\r\n` | Text protocols |
| `DelimiterBasedFrameDecoder` | Custom delimiter | Messages end with `$$` |
| `LengthFieldBasedFrameDecoder` | Length header prefix | `[4-byte length][payload]` — most common |

```
LengthFieldBasedFrameDecoder example:

  ┌──────────┬───────────────────────┐
  │ Length: 5 │ H E L L O             │
  │ (4 bytes) │ (5 bytes payload)     │
  └──────────┴───────────────────────┘
      ↑ decoder reads this first, then waits until 5 bytes arrive
```

---

## 6. Zero-Copy in Netty

Netty achieves zero-copy at multiple levels (not OS-level `sendfile`, but **user-space zero-copy**):

| Technique | How |
|-----------|-----|
| `CompositeByteBuf` | Merge multiple buffers logically without memory copy |
| `slice()` / `duplicate()` | Create views over existing buffer, share underlying memory |
| `FileRegion` | Wraps OS `transferTo()` / `sendfile()` for file transfer |
| `Unpooled.wrappedBuffer()` | Wrap byte array into ByteBuf without copy |
| Direct memory ByteBuf | Allocate off-heap, avoid one copy between JVM heap and socket buffer |

```
Without zero-copy:
  [Header buf] + [Body buf] → copy into [Combined buf] → write to socket

With CompositeByteBuf:
  CompositeByteBuf
  ├── component[0] → Header buf (no copy)
  └── component[1] → Body buf   (no copy)
  → write both to socket directly
```

---

## 7. Threading Model

```
┌──────────────────────────────────────────────────────┐
│                  Netty Threading                      │
│                                                       │
│  BossGroup (1 thread typically)                       │
│  └── EventLoop-0: accept connections                  │
│                                                       │
│  WorkerGroup (N threads = CPU * 2)                    │
│  ├── EventLoop-0: I/O + handlers for Channel A, D    │
│  ├── EventLoop-1: I/O + handlers for Channel B, E    │
│  └── EventLoop-2: I/O + handlers for Channel C, F    │
│                                                       │
│  BusinessGroup (optional, for blocking operations)    │
│  └── EventExecutor threads: database, HTTP calls      │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**Rule:** Never block an EventLoop thread. If you have blocking operations (DB queries, external API calls), offload to a separate `EventExecutorGroup`:

```java
EventExecutorGroup bizGroup = new DefaultEventExecutorGroup(16);

ch.pipeline().addLast(bizGroup, new BlockingBusinessHandler());
//                     ↑ runs on bizGroup threads, not EventLoop
```

---

## 8. Who Uses Netty

| Project | Usage |
|---------|-------|
| **Dubbo** | RPC framework — Netty as transport layer |
| **gRPC-Java** | Default HTTP/2 transport |
| **Elasticsearch** | Internal node communication |
| **Cassandra** | Client-server protocol |
| **Spring WebFlux** | Reactive web — Netty as default server |
| **RocketMQ** | Message broker networking |
| **Zuul 2** | Netflix API gateway |
| **Vert.x** | Reactive toolkit built on Netty |

---

## 9. Summary

```
Java I/O Evolution:
  BIO (1 thread/conn) → NIO (selector, painful API) → Netty (elegant NIO framework)

Netty Core Design:
  ┌─────────────────────────────────────────────────┐
  │  Reactor Pattern (Boss + Worker EventLoopGroup) │
  │  ChannelPipeline (pluggable handler chain)      │
  │  ByteBuf (pooled, ref-counted, dual-index)      │
  │  Built-in codecs (frame decoders, SSL, HTTP...) │
  │  Zero-copy (composite buf, direct memory, etc.) │
  └─────────────────────────────────────────────────┘

Key Takeaways:
  1. Netty exists because raw NIO is powerful but painful
  2. Reactor pattern: Boss accepts, Workers handle I/O — one EventLoop per channel
  3. Pipeline: chain of handlers — clean separation of codec and business logic
  4. ByteBuf > ByteBuffer — pooled, no flip(), ref-counted
  5. Frame decoders solve TCP sticky/half-packet problems out of the box
  6. Never block the EventLoop — offload blocking work to a separate group
```

## Reference
- https://netty.io
- https://github.com/netty/netty
