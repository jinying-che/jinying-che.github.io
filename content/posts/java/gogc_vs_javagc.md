---
title: "Go GC vs Java GC"
date: 2026-03-19T00:00:00+08:00
description: "Deep comparison of Go and Java garbage collectors — design, trade-offs, and when to choose which"
tags: ["java", "go"]
draft: true
---

# Go GC vs Java GC

> Go and Java both have GC, but with fundamentally different designs and trade-offs. Neither is "better" — they optimize for different workloads.

## 1. Who Runs the GC?

```
Java:                                    Go:
┌─────────────┐                         ┌──────────────────────┐
│  Your Code  │                         │  Your Code           │
├─────────────┤                         │  +                   │
│    JVM      │  ← separate runtime     │  Go Runtime (GC,     │
│  (GC, JIT,  │     process             │   scheduler, alloc)  │
│   classload)│                         │  compiled together   │
├─────────────┤                         └──────────┬───────────┘
│     OS      │                                    │
└─────────────┘                              single binary
```

- **Java**: GC lives inside the JVM, a separate virtual machine that interprets/JITs your bytecode
- **Go**: GC is part of the Go runtime, **compiled directly into every Go binary**. No VM, but the runtime code (goroutine scheduler, memory allocator, GC) is linked into your executable

## 2. GC Algorithm Design

### Java — Generational, Region-Based / Colored Pointers

Java's key insight: **most objects die young** (Weak Generational Hypothesis).

```
Java Heap (G1):
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ E │ E │ S │ O │ O │ H │ H │ E │    ~2048 regions
├───┼───┼───┼───┼───┼───┼───┼───┤
│ O │ E │   │ O │ S │ E │ O │ O │    E=Eden S=Survivor O=Old H=Humongous
└───┴───┴───┴───┴───┴───┴───┴───┘

Young Gen collected frequently (Minor GC) — most objects die here
Old Gen collected rarely (Mixed/Full GC) — long-lived objects
Compaction: objects moved to eliminate fragmentation
```

**G1**: region-based, collects "garbage-first" regions, tunable pause target
**ZGC**: colored pointers + load barriers, concurrent relocation, < 1ms pauses at TB-scale

### Go — Non-Generational, Tri-Color Mark-Sweep

Go's approach: **keep it simple, optimize for low latency, one algorithm for all**.

```
Go Heap:
┌──────────────────────────────────────┐
│  All objects treated equally          │
│  No young/old distinction             │
│  No compaction                        │
│  Entire heap scanned every GC cycle   │
└──────────────────────────────────────┘

Tri-color marking:
  ● = Black (alive, fully scanned)
  ◐ = Grey  (alive, references not yet scanned)
  ○ = White (potentially garbage)

  Start:    ○ ○ ○ ○ ○    all white
  Roots:    ◐ ○ ○ ○ ○    roots marked grey
  Scan:     ● ◐ ◐ ○ ○    grey → scan refs → children grey, self black
  Continue: ● ● ● ◐ ○    keep going...
  Done:     ● ● ● ● ○    white objects = garbage, collect them
```

### GC Phases Compared

```
Java G1:
1. Young GC              (STW, parallel)      — collect Eden+Survivor
2. Initial Mark          (STW, piggyback)     — mark GC roots
3. Concurrent Mark       (concurrent)         — trace object graph
4. Remark                (STW, short)         — handle SATB changes
5. Cleanup               (STW, short)         — identify free regions
6. Mixed GC              (STW, parallel)      — collect Young + some Old

Java ZGC:
1. Pause Mark Start      (STW ~1ms)           — scan GC roots
2. Concurrent Mark       (concurrent)         — trace object graph
3. Pause Mark End        (STW ~1ms)           — finish marking
4. Concurrent Relocate   (concurrent)         — move objects via load barriers

Go:
1. Sweep Termination     (STW, < 100μs)      — finish previous sweep
2. Concurrent Mark       (concurrent)         — tri-color mark with write barrier
3. Mark Termination      (STW, < 100μs)      — finish marking
4. Concurrent Sweep      (concurrent)         — free white objects
```

## 3. Key Design Differences

### Generational vs Non-Generational

```
Java (generational):
  new Object() → Eden → survives? → Survivor (age++) → Old Gen

  Minor GC: only scan Young Gen (~1/3 heap, ~98% die here)
  Major GC: scan Old Gen (rare, only when Old Gen fills)
  → Most GC cycles are cheap (small scan area)

Go (non-generational):
  new object → heap (or stack if escape analysis says so)

  Every GC cycle: scan ALL live objects on heap
  → GC cost scales linearly with live heap size
```

Why Go skipped generational:
1. **Goroutine stacks are on heap** — they're not short-lived, complicates generational tracking
2. **Escape analysis is aggressive** — many short-lived objects never reach heap (stay on stack, zero GC cost)
3. **Write barrier cost** — generational GC needs write barriers all the time (track old→young refs), Go only needs them during GC marking
4. **Simplicity** — one GC, one tuning knob, predictable behavior

```
Go's escape analysis compensates for no generational GC:

Java: short-lived objects → allocate on heap → Young Gen → Minor GC (cheap)
Go:   short-lived objects → escape analysis → stack allocation → free on return (free!)
      long-lived objects → heap → full GC scan (expensive at scale)
```

### Compaction vs No Compaction

```
Java (compacts):
  Before: [A][_][B][__][C][_][D]    fragmented
  After:  [A][B][C][D][________]    compacted, contiguous free space

  → No fragmentation, but must update all references to moved objects
  → G1 copies between regions, ZGC uses colored pointers + load barriers

Go (no compaction):
  Before: [A][_][B][__][C][_][D]    fragmented
  After:  [A][_][B][__][C][_][D]    stays fragmented

  Mitigation: size-class allocator (TCMalloc-style)
    Objects grouped by size: 8B, 16B, 32B, 48B, ... 32KB
    Each size class has its own free list
    → Reduces fragmentation within size classes
    → But inter-class fragmentation still possible
```

### Memory Allocator

```
Java (TLAB bump pointer):                Go (TCMalloc-inspired):
  Thread → TLAB (private Eden chunk)       Goroutine → mcache (per-P, no lock)
           bump pointer (ultra fast)                    free list by size class
           ↓ TLAB full                                  ↓ mcache empty
           Request new TLAB (lock)          mcentral (per size-class, lock)
                                                        ↓ mcentral empty
                                            mheap (global, lock)
                                                        ↓ mheap empty
                                            OS mmap
```

Both avoid lock contention for most allocations (TLAB / mcache), but Java's bump pointer is slightly faster than Go's free-list lookup.

## 4. STW Pause Comparison

STW (Stop-The-World) = all application threads/goroutines frozen while GC works.

```
          Pause Duration (log scale)

  1s      ┤ ██ Serial/Parallel GC
          │
  200ms   ┤ ██ G1 (default target)
          │
  50ms    ┤ ██ CMS (deprecated)
          │
  10ms    ┤
          │
  1ms     ┤ ██ Java ZGC
          │
  0.5ms   ┤ ██ Go GC
          │
  0.1ms   ┤ ██ Go GC (typical)
          └──────────────────────
```

| GC | Typical STW Pause | What's STW |
|----|-------------------|-----------|
| Java Serial | 100ms - seconds | Everything |
| Java Parallel | 50ms - seconds | Everything |
| Java G1 | ~200ms (tunable) | Young GC, remark, cleanup |
| Java ZGC | < 1ms | Root scanning only |
| Go | < 0.5ms (typically < 100μs) | Sweep termination + mark termination |

**Go wins on default latency**. ZGC matches it but requires explicit opt-in and tuning.

## 5. Drawbacks of Go GC

### 5.1 No Generational — Full Heap Scan Every Cycle

```
GC CPU cost vs heap size:

         │  Go (linear — scan everything)
  GC CPU │  /
  Cost   │ /
         │/     Java G1 (mostly flat — scan young gen only)
         │──────────────────────
         └──────────────────────
              Heap Size →

At 1GB:   Go ≈ Java
At 10GB:  Go spends significantly more CPU
At 50GB+: Go impractical; Java ZGC handles TB-scale
```

### 5.2 No Compaction — Fragmentation

Size-class allocator mitigates but doesn't eliminate. Long-running services with diverse allocation patterns waste memory over time.

### 5.3 Higher Memory Usage (2x headroom)

```
GOGC=100 (default): trigger GC when heap = 2× live set

Live set = 1GB → GC at 2GB → peak ~2GB
Live set = 5GB → GC at 10GB → peak ~10GB

Java: -Xmx tightly controls max heap, generational means less headroom needed
```

### 5.4 Write Barrier Overhead

During concurrent marking, every pointer write executes barrier code: **~5-15% throughput overhead** while GC is active.

### 5.5 Almost No Tuning Knobs

```
Go tuning:
  GOGC=100          (GC trigger ratio, that's about it)
  GOMEMLIMIT=4GiB   (hard memory limit, Go 1.19+)

Java tuning:
  -XX:+UseZGC                    choose algorithm
  -XX:MaxGCPauseMillis=50        pause target
  -XX:ConcGCThreads=4            parallel workers
  -XX:G1HeapRegionSize=16m       region size
  -XX:MaxTenuringThreshold=8     promotion age
  ... dozens more
```

Simplicity is a strength for most apps, but a weakness when you need fine-grained control.

## 6. Why Cloud Infrastructure Chose Go Despite GC Limitations

K8s, etcd, Prometheus, Docker, containerd — all Go. Why doesn't GC hurt them?

### They Keep Big Data OFF the Go Heap

```
┌─── Go Heap (GC managed, kept small) ──┐
│  Request/response objects               │
│  Goroutine stacks                       │
│  Temp buffers, metadata                 │
│  → small live set, GC scans fast        │
└─────────────────────────────────────────┘

┌─── Off-Heap (GC invisible) ───────────┐
│  etcd:        boltdb (mmap'd B+ tree)  │
│  Prometheus:  TSDB (mmap'd chunks)     │
│  K8s:         state in etcd (external) │
│  → GC doesn't see or scan any of this  │
└────────────────────────────────────────┘
```

| System | Big data location | Go heap holds |
|--------|-------------------|---------------|
| **etcd** | boltdb (mmap'd file) | Raft state, gRPC buffers |
| **Prometheus** | TSDB on disk (mmap'd) | Query buffers, scrape metadata |
| **K8s API server** | etcd (external store) | API request/response objects |
| **Docker/containerd** | Filesystem, kernel namespaces | Container metadata |

### Request-Response = Go's Sweet Spot

```
K8s API request:
  Request in → allocate objects → process → respond → garbage
                    ↑                                    ↑
              most stay on stack              short-lived, collected fast
              (escape analysis)              small live set at any time

OKX Order Book:
  Order placed → lives in memory for hours/days → mutated on every trade
                          ↑
                 LONG-LIVED, LARGE, growing
                 all on heap, scanned every GC cycle
```

### Go's Real Advantages for Infrastructure

GC is secondary. Go was chosen because:

| Advantage | Why It Matters | Java Comparison |
|-----------|---------------|-----------------|
| **Single binary** | No runtime to install, tiny containers | Docker image: Go 10MB vs Java 200MB+ |
| **Fast startup** | ~10ms, critical for containers/CLI | Java: 1-5s (class loading, JIT warmup) |
| **Goroutines** | Millions of lightweight concurrent tasks | Java thread: ~1MB stack, 10K threads = 10GB |
| **Low memory** | Runs on 512MB VMs | JVM needs 2GB+ just for overhead |
| **Simplicity** | K8s has 3000+ contributors, anyone can learn Go in weeks | Java ecosystem is vast and complex |

## 7. Head-to-Head Summary

| | Java (G1/ZGC) | Go |
|---|---|---|
| **GC Algorithm** | Generational, compacting | Non-generational, non-compacting, tri-color mark-sweep |
| **STW Pauses** | G1: ~200ms, ZGC: < 1ms | < 0.5ms (typically < 100μs) |
| **Throughput** | Higher (generational = less work) | Lower (full heap scan) |
| **Large Heap (50GB+)** | Handles well (ZGC: TB-scale) | Struggles (linear scan cost) |
| **Memory Overhead** | Higher (object headers, VM) | Lower (no headers, no VM) |
| **Fragmentation** | None (compaction) | Possible (no compaction) |
| **Memory Headroom** | Tight (-Xmx control) | 2× live set (GOGC=100) |
| **Tuning** | Dozens of knobs | One: GOGC (+ GOMEMLIMIT) |
| **Startup Time** | 1-5s | ~10ms |
| **Binary Size** | JVM + JARs (~200MB) | Single binary (~10MB) |

## 8. When to Choose Which

```
Choose Go when:                          Choose Java when:
─────────────────                        ──────────────────
• Infrastructure tooling (CLI, DevOps)   • Large in-memory state (order books, caches)
• Container/cloud native services        • High throughput batch processing
• API gateways, proxies                  • Enterprise apps (Spring ecosystem)
• Small-to-medium heap (<4GB)            • Large heap (10GB+)
• Need fast startup + tiny containers    • Need fine-grained GC tuning
• Simple microservices                   • Big data (Spark, Flink)
• Latency-sensitive, small working set   • Trading engines (ZGC)

Examples:                                Examples:
  K8s, etcd, Prometheus, Docker            OKX, Binance, Kafka, Elasticsearch
  Terraform, Vault, Consul                 Spring Cloud microservices
  gRPC services, Envoy (control plane)     Hadoop/Spark/Flink
```

**For OKX specifically**: the matching engine holds GBs of live order data in memory. Java's generational GC (G1/ZGC) avoids scanning the entire order book every cycle, and compaction prevents fragmentation from constant order create/cancel/fill churn. Go's GC would spend excessive CPU scanning the full live set repeatedly.
