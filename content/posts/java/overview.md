---
title: "Java Overview"
date: 2026-03-19T00:00:00+08:00
description: "Java interview cheat sheet — concise summary with links to deep dives"
tags: ["java"]
draft: true
---

# Java Overview

> Concise interview cheat sheet. Each section links to a detailed post.

## 1. JVM Memory & Object Lifecycle → [detail](../jvm_memory)

```
┌─── Thread-Shared ──────────────────────────────┐
│  Heap: Young Gen (Eden, S0, S1) + Old Gen      │
│  Metaspace: class metadata, string pool         │
└─────────────────────────────────────────────────┘
┌─── Per-Thread ─────────────────────────────────┐
│  VM Stack (frames) │ PC Register │ Native Stack│
└─────────────────────────────────────────────────┘
┌─── Off-Heap ───────────────────────────────────┐
│  Direct Memory (NIO, Netty)                     │
└─────────────────────────────────────────────────┘
```

**Object journey**: `new` → escape analysis → TLAB (Eden) → Minor GC → Survivor (age++) → Old Gen → Major/Full GC

**GC quick pick**:

| GC | Pause | Best For |
|----|-------|----------|
| G1 | Tunable (~200ms) | General, 4-16GB heap |
| ZGC | < 1ms | Ultra-low latency (trading) |

**Key flags**: `-Xms` / `-Xmx` (heap), `-Xmn` (young gen), `-XX:+UseZGC`, `-XX:MaxGCPauseMillis`


## 2. Java Memory Model (JMM) → [detail](../jmm)

> JMM ≠ JVM memory layout. JMM = visibility + ordering guarantees between threads.

**Core concepts**:
- **Visibility problem**: CPU caches may hide writes from other threads
- **Ordering problem**: compiler/CPU may reorder instructions
- **`volatile`**: visibility (flush to main memory) + ordering (memory barriers), but NOT atomic
- **Happens-before**: the formal rules for what's guaranteed visible (8 rules, transitivity)

**Classic question — Double-Checked Locking**:

```java
private static volatile Singleton instance; // volatile prevents reorder of constructor
```

Without `volatile`: reference may be assigned before constructor finishes → half-constructed object.


## 3. HashMap Internals → [detail](../hashmap)

**Structure**: `Node[]` array + linked list → Red-Black Tree (chain > 8 && capacity >= 64)

**Key mechanics**:
- Hash: `h ^ (h >>> 16)` — mix high bits into low bits for better distribution
- Index: `hash & (capacity - 1)` — why capacity must be power of 2
- Load factor: 0.75, resize doubles capacity
- Resize: `hash & oldCap` decides stay (0) or move (+oldCap)

**Java 7 vs 8**: head insertion → tail insertion (fixes infinite loop bug), added treeify

**Thread safety**: NOT safe. Use `ConcurrentHashMap` (CAS + per-bucket `synchronized` in Java 8)


## 4. Concurrency → [detail](../concurrency)

**Thread lifecycle**: NEW → RUNNABLE → (BLOCKED / WAITING / TIMED_WAITING) → TERMINATED

**Lock escalation** (object Mark Word): no lock → biased lock → lightweight lock (CAS) → heavyweight lock (OS mutex)

**synchronized vs ReentrantLock**:

| | synchronized | ReentrantLock |
|---|---|---|
| Release | auto (exit block) | manual (`unlock()` in finally) |
| Interruptible | No | Yes (`lockInterruptibly()`) |
| Try lock | No | Yes (`tryLock(timeout)`) |
| Condition | 1 (wait/notify) | Multiple (`newCondition()`) |
| Fair lock | No | Optional (`new ReentrantLock(true)`) |

**ThreadPoolExecutor** — 7 params: corePoolSize, maxPoolSize, keepAliveTime, unit, workQueue, threadFactory, rejectionPolicy

```
Task arrives → core thread available? → YES → execute
                     ↓ NO
              queue full? → NO → add to queue
                     ↓ YES
              < maxPoolSize? → YES → create new thread
                     ↓ NO
              rejection policy (Abort/Discard/CallerRuns/DiscardOldest)
```

**Key tools**: `volatile` (visibility), `CAS/Atomic*` (lock-free), `AQS` (foundation of locks/semaphores/CountDownLatch), `CompletableFuture` (async composition), `ThreadLocal` (per-thread storage, watch for memory leaks with thread pools)


## 5. Java I/O → [detail](../java_io)

**Three I/O models**:

```
BIO (Blocking)          NIO (Non-blocking)           AIO (Async)
1 thread per conn       1 thread many conns          OS callback

Thread──►read()         Thread──►Selector             Thread──►read()
         (blocks)                  │                            │
         ...wait...       poll ready channels           (returns immediately)
         data ready       ├─ Channel A ready              ...
         process          ├─ Channel B ready           OS completes I/O
                          └─ process each              callback notifies
```

| | BIO | NIO | AIO |
|---|---|---|---|
| Model | 1 thread : 1 connection | 1 thread : N connections (Selector) | OS-driven callback |
| Blocking | Yes | No (Selector polls readiness) | No (fully async) |
| API | `InputStream/OutputStream` | `Channel + Buffer + Selector` | `AsynchronousChannel` |
| Use case | Simple, low concurrency | High concurrency (Netty, Tomcat NIO) | File I/O (limited adoption) |
| Linux kernel | `read()` blocks | `epoll` (select/poll) | `io_uring` / AIO |

**NIO core**: `Channel` (bidirectional) + `Buffer` (data container) + `Selector` (multiplexer, one thread monitors many channels)

**Netty** = NIO framework. Reactor pattern: Boss group (accept connections) → Worker group (handle I/O). Used at OKX for WebSocket feeds, internal RPC.

**Zero-copy**: `FileChannel.transferTo()` → kernel sends file data directly to socket, no user-space copy. Kafka uses this for high-throughput message delivery.
