---
title: "Java I/O — BIO, NIO, AIO & Netty"
date: 2026-03-19T00:00:00+08:00
description: "Deep dive into Java I/O models, NIO internals, Reactor pattern, Netty architecture, and zero-copy"
tags: ["java"]
draft: true
---

# Java I/O — BIO, NIO, AIO & Netty

## 1. Three I/O Models

### BIO — Blocking I/O (java.io)

```
Client 1 ──► Thread 1 ──► read() ──► BLOCKS until data arrives
Client 2 ──► Thread 2 ──► read() ──► BLOCKS until data arrives
Client 3 ──► Thread 3 ──► read() ──► BLOCKS until data arrives
   ...           ...
Client N ──► Thread N    ← 10K clients = 10K threads = OOM!
```

```java
ServerSocket server = new ServerSocket(8080);
while (true) {
    Socket socket = server.accept();         // blocks until connection
    new Thread(() -> {
        InputStream in = socket.getInputStream();
        byte[] buf = new byte[1024];
        int len = in.read(buf);              // blocks until data
        // process...
    }).start();
}
```

**Problems**:
- 1 thread per connection → thread explosion under high concurrency
- Threads mostly idle (waiting for I/O) → wasted resources
- Context switching overhead with thousands of threads
- **C10K problem**: cannot handle 10,000+ concurrent connections

### NIO — Non-blocking I/O (java.nio, Java 1.4+)

```
                    ┌─── Channel A (ready)  → process
Selector ───poll──►├─── Channel B (not ready) → skip
(1 thread)         ├─── Channel C (ready)  → process
                    └─── Channel D (not ready) → skip

1 thread handles thousands of connections!
```

```java
Selector selector = Selector.open();
ServerSocketChannel serverChannel = ServerSocketChannel.open();
serverChannel.bind(new InetSocketAddress(8080));
serverChannel.configureBlocking(false);             // non-blocking mode
serverChannel.register(selector, SelectionKey.OP_ACCEPT);

while (true) {
    selector.select();                               // blocks until at least 1 channel ready
    Set<SelectionKey> keys = selector.selectedKeys();
    for (SelectionKey key : keys) {
        if (key.isAcceptable()) {
            SocketChannel client = serverChannel.accept();
            client.configureBlocking(false);
            client.register(selector, SelectionKey.OP_READ);
        } else if (key.isReadable()) {
            SocketChannel client = (SocketChannel) key.channel();
            ByteBuffer buffer = ByteBuffer.allocate(1024);
            client.read(buffer);                     // non-blocking read
            // process...
        }
    }
    keys.clear();
}
```

### AIO — Asynchronous I/O (java.nio.channels, Java 7+)

```
Thread ──► read(buffer, callback) ──► returns immediately
                                           │
                                      OS completes I/O
                                           │
                                      callback invoked with result
```

```java
AsynchronousSocketChannel channel = AsynchronousSocketChannel.open();
ByteBuffer buffer = ByteBuffer.allocate(1024);

// Callback style
channel.read(buffer, null, new CompletionHandler<Integer, Void>() {
    @Override
    public void completed(Integer bytesRead, Void attachment) {
        // I/O done, process data
    }
    @Override
    public void failed(Throwable exc, Void attachment) {
        // handle error
    }
});
// Thread continues immediately, doesn't wait
```

**AIO adoption is limited** — Linux's native AIO (`io_uring` is newer and better but Java doesn't use it yet). Netty tried AIO and removed it — NIO + epoll was faster in practice. AIO is mainly useful for file I/O on Windows (IOCP).

## 2. NIO Core Components

### Channel — Bidirectional Data Pipe

```
BIO Stream (one-way):
  InputStream  ──► read only
  OutputStream ──► write only

NIO Channel (two-way):
  SocketChannel ◄──► read and write
```

| Channel Type | Use |
|-------------|-----|
| `FileChannel` | File I/O (blocking only, no Selector) |
| `SocketChannel` | TCP client |
| `ServerSocketChannel` | TCP server (accept connections) |
| `DatagramChannel` | UDP |

### Buffer — Data Container

```
Buffer internal state:

  0    position        limit      capacity
  │        │             │           │
  ▼        ▼             ▼           ▼
  ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
  │##│##│##│  │  │  │  │  │  │  │  │
  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘
  ◄─ written ─►◄─ writable ─►◄ N/A ►

After flip() (switch from write mode to read mode):

  0                  limit      capacity
  │                    │           │
  ▼position            ▼           ▼
  ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
  │##│##│##│  │  │  │  │  │  │  │  │
  └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘
  ◄─ readable ─►

flip(): limit = position, position = 0
clear(): position = 0, limit = capacity (discard all)
compact(): copy unread data to beginning, position after last copied byte
```

**Buffer types**: `ByteBuffer` (most common), `CharBuffer`, `IntBuffer`, `LongBuffer`, etc.

**HeapByteBuffer vs DirectByteBuffer**:

| | HeapByteBuffer | DirectByteBuffer |
|---|---|---|
| Memory | JVM heap (`byte[]`) | Native memory (off-heap) |
| GC | Subject to GC | Not directly GC'd (reference is) |
| Allocation | Fast | Slow (OS call) |
| I/O performance | Slower (JVM copies to native for I/O) | Faster (no copy, direct kernel access) |
| Use case | Temporary, short-lived | Long-lived I/O buffers (Netty) |

```java
ByteBuffer heap = ByteBuffer.allocate(1024);        // heap
ByteBuffer direct = ByteBuffer.allocateDirect(1024); // native, faster I/O
```

### Selector — I/O Multiplexer

```
                         Selector
                            │
              ┌─────────────┼─────────────┐
              │             │             │
         SelectionKey  SelectionKey  SelectionKey
         (Channel A)   (Channel B)   (Channel C)
         OP_READ       OP_WRITE      OP_ACCEPT
```

**Selection key interest ops**:
- `OP_ACCEPT` (16): ServerSocketChannel — new connection ready
- `OP_CONNECT` (8): SocketChannel — connection established
- `OP_READ` (1): Channel has data to read
- `OP_WRITE` (4): Channel ready to write

**Under the hood (Linux)**:

| Java API | Linux syscall | Behavior |
|----------|---------------|----------|
| `selector.select()` (old) | `poll()` / `select()` | O(n) scan all file descriptors |
| `selector.select()` (Java 5+ Linux) | `epoll` | O(1) event notification, scales to millions of fds |

**epoll is the key to high-performance NIO on Linux**:
- `epoll_create`: create epoll instance
- `epoll_ctl`: register/modify interest in file descriptors
- `epoll_wait`: block until events occur, returns ONLY ready fds (not all fds)

`select/poll` scans ALL fds every time → O(n). `epoll` maintains a ready list → O(1) per event. This is why NIO scales to millions of connections.

## 3. Reactor Pattern

The design pattern underlying NIO servers. Three variants:

### Single Reactor Single Thread

```
┌─────────────────────────────────┐
│         Reactor Thread          │
│                                 │
│  Selector                       │
│     │                           │
│     ├─► Accept → create handler │
│     ├─► Read → decode → compute │
│     └─► Write → encode → send   │
│                                 │
│  (everything in one thread)     │
└─────────────────────────────────┘

Problem: one slow handler blocks everything
Example: Redis (single-threaded, but commands are fast)
```

### Single Reactor Multi Thread

```
┌──────────────────┐    ┌──────────────────────┐
│  Reactor Thread  │    │  Worker Thread Pool   │
│                  │    │                       │
│  Selector        │    │  Thread 1: compute    │
│     │            │    │  Thread 2: compute    │
│     ├─► Accept   │    │  Thread 3: compute    │
│     ├─► Read ────┼───►│  ...                  │
│     └─► Write ◄──┼────│                       │
│                  │    └──────────────────────┘
└──────────────────┘

Problem: single Reactor thread becomes bottleneck for accept + I/O
```

### Multi Reactor (Master-Worker) — Netty's Model

```
┌──────────────────┐    ┌──────────────────────┐
│  Main Reactor    │    │  Sub Reactors        │
│  (Boss Group)    │    │  (Worker Group)       │
│                  │    │                       │
│  Selector        │    │  Selector 1 ──► read/write Channel A, B
│     │            │    │  Selector 2 ──► read/write Channel C, D
│     └─► Accept ──┼───►│  Selector 3 ──► read/write Channel E, F
│                  │    │  ...                  │
│  1-2 threads     │    │  N threads (CPU cores)│
└──────────────────┘    └──────────────────────┘

Boss accepts connections, distributes to Workers.
Each Worker handles I/O for assigned channels.
Compute-heavy work can be offloaded to a separate business thread pool.
```

## 4. Netty Architecture

Netty is the de facto NIO framework in Java. Used by: Dubbo, gRPC-java, Elasticsearch, Kafka (client), OKX WebSocket feeds, etc.

### Core Components

```
┌─────────────────────────────────────────────┐
│                  Bootstrap                   │
│                                              │
│  ┌─ Boss EventLoopGroup ─────────────────┐  │
│  │  EventLoop (thread + Selector)         │  │
│  │  Accept connections → assign to Worker │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─ Worker EventLoopGroup ───────────────┐  │
│  │  EventLoop 1 (thread + Selector)       │  │
│  │    └─► Channel A, Channel D            │  │
│  │  EventLoop 2 (thread + Selector)       │  │
│  │    └─► Channel B, Channel E            │  │
│  │  EventLoop N ...                       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌─ Channel Pipeline ───────────────────┐   │
│  │  Inbound:  ByteBuf → Decoder → Handler│   │
│  │  Outbound: Handler → Encoder → ByteBuf│   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Key Concepts

| Component | Role |
|-----------|------|
| `EventLoop` | Thread + Selector loop, handles I/O events for assigned Channels. One Channel is bound to one EventLoop forever (no thread safety issues) |
| `EventLoopGroup` | Pool of EventLoops. Boss group = accept. Worker group = I/O |
| `Channel` | Wraps NIO SocketChannel. Lifecycle: register → active → inactive → unregister |
| `ChannelPipeline` | Chain of ChannelHandlers (like servlet filters). Inbound flows in, outbound flows out |
| `ChannelHandler` | Business logic. `ChannelInboundHandler` (read), `ChannelOutboundHandler` (write) |
| `ByteBuf` | Netty's Buffer, better than `ByteBuffer`: separate read/write index (no flip!), pooled, reference counted, composite |

### Netty Server Example

```java
EventLoopGroup bossGroup = new NioEventLoopGroup(1);      // 1 thread for accept
EventLoopGroup workerGroup = new NioEventLoopGroup();      // default: CPU cores × 2

ServerBootstrap b = new ServerBootstrap();
b.group(bossGroup, workerGroup)
 .channel(NioServerSocketChannel.class)
 .childHandler(new ChannelInitializer<SocketChannel>() {
     @Override
     protected void initChannel(SocketChannel ch) {
         ch.pipeline()
           .addLast(new LengthFieldBasedFrameDecoder(65535, 0, 4))  // solve TCP sticky/unpacking
           .addLast(new StringDecoder())
           .addLast(new BusinessHandler())        // your logic
           .addLast(new StringEncoder());
     }
 })
 .option(ChannelOption.SO_BACKLOG, 128)            // accept queue size
 .childOption(ChannelOption.SO_KEEPALIVE, true);

ChannelFuture f = b.bind(8080).sync();
f.channel().closeFuture().sync();
```

### ByteBuf vs ByteBuffer

```
ByteBuffer (JDK NIO):
  One index (position). Must flip() between read/write.
  ┌──────────────────────────┐
  │  position    limit  cap  │
  └──────────────────────────┘

ByteBuf (Netty):
  Separate readerIndex and writerIndex. No flip needed.
  ┌──────────────────────────────────────────────┐
  │ 0  readerIndex   writerIndex    capacity      │
  │ ◄─ discardable ─►◄─ readable ─►◄─ writable ─►│
  └──────────────────────────────────────────────┘
```

| Feature | ByteBuffer | ByteBuf |
|---------|------------|---------|
| Read/write index | Single position, need flip() | Separate readerIndex/writerIndex |
| Pooling | No | Yes (PooledByteBufAllocator) — reduces GC |
| Reference counting | No | Yes (`retain()`/`release()`) |
| Composite | No | Yes (`CompositeByteBuf` — zero-copy merge) |
| Auto-expand | No (fixed capacity) | Yes (dynamic) |
| Direct memory | `allocateDirect()` | `directBuffer()` with pooling |

### TCP Sticky Packet / Unpacking Problem

TCP is a stream protocol — no message boundaries. Receiver may get:
- **Sticky**: two messages merged into one read (`msg1 + msg2`)
- **Unpacking**: one message split into two reads (`msg1_part1` then `msg1_part2`)

**Netty solutions**:

| Decoder | Strategy |
|---------|----------|
| `FixedLengthFrameDecoder` | Fixed-size messages |
| `DelimiterBasedFrameDecoder` | Delimiter (e.g., `\n`) |
| `LengthFieldBasedFrameDecoder` | Length prefix header (most common in protocols) |
| `LineBasedFrameDecoder` | Line break delimiter |

## 5. Zero-Copy

"Zero-copy" means **no data copy between kernel space and user space**.

### Traditional File Transfer (4 copies)

```
1. Disk → Kernel Buffer         (DMA copy)
2. Kernel Buffer → User Buffer  (CPU copy) ← unnecessary
3. User Buffer → Socket Buffer  (CPU copy) ← unnecessary
4. Socket Buffer → NIC          (DMA copy)

4 copies, 4 context switches (user↔kernel)
```

### mmap (2.5 copies)

```
1. Disk → Kernel Buffer              (DMA copy)
2. Kernel Buffer mapped to user space (no copy, shared memory)
3. Kernel Buffer → Socket Buffer     (CPU copy)
4. Socket Buffer → NIC               (DMA copy)

3 copies, 4 context switches
Used by: MappedByteBuffer (FileChannel.map())
```

### sendfile / transferTo (2 copies)

```
1. Disk → Kernel Buffer    (DMA copy)
2. Kernel Buffer → NIC     (DMA copy, with scatter-gather DMA)

2 copies, 2 context switches — data never enters user space!
```

```java
// Java API
FileChannel fileChannel = FileChannel.open(path);
// Transfer file directly to socket — never enters JVM heap
fileChannel.transferTo(0, fileChannel.size(), socketChannel);
```

**Who uses zero-copy**:
- **Kafka**: `transferTo()` for sending log segments to consumers — key to Kafka's throughput
- **Netty**: `FileRegion` wraps `transferTo()` for file serving
- **Netty CompositeByteBuf**: merges multiple buffers logically without copying bytes
- **RocketMQ**: `mmap` (MappedByteBuffer) for message store

### Zero-Copy in Netty

```java
// 1. FileRegion — sendfile for file transfer
FileChannel fc = new RandomAccessFile("data.bin", "r").getChannel();
FileRegion region = new DefaultFileRegion(fc, 0, fc.size());
ctx.writeAndFlush(region);  // zero-copy to socket

// 2. CompositeByteBuf — logical merge without copy
CompositeByteBuf composite = Unpooled.compositeBuffer();
composite.addComponents(true, header, body);  // no byte copy, just reference merge
// acts as single buffer for reading

// 3. slice() / duplicate() — share underlying memory
ByteBuf slice = buf.slice(0, 100);  // shares buf's memory, no copy
// modifying slice's data modifies buf's data (shared reference)

// 4. Unpooled.wrappedBuffer() — wrap byte[] without copy
byte[] data = getBytes();
ByteBuf buf = Unpooled.wrappedBuffer(data);  // no copy, wraps array directly
```

## 6. I/O Model Comparison Summary

| | BIO | NIO | AIO |
|---|---|---|---|
| **Java package** | `java.io` | `java.nio` (1.4+) | `java.nio.channels` (7+) |
| **Blocking** | Yes | No (Selector-based) | No (callback-based) |
| **Thread model** | 1:1 (thread per conn) | 1:N (Selector multiplexing) | 0:N (OS callback) |
| **API style** | Stream (InputStream/OutputStream) | Buffer + Channel + Selector | CompletionHandler callback |
| **Linux kernel** | `read()` blocks | `epoll` | `io_uring` (limited in Java) |
| **Concurrency** | ~hundreds | ~millions (with epoll) | ~millions |
| **Complexity** | Simple | Medium (Selector API awkward) | Medium (callback hell) |
| **Framework** | Tomcat BIO (legacy) | **Netty**, Tomcat NIO | Rarely used directly |
| **Use at OKX** | None | WebSocket, gRPC, Dubbo | N/A |
