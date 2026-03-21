---
title: "JVM Memory & Object Lifecycle"
date: 2026-03-19T00:00:00+08:00
description: "Deep dive into JVM runtime memory layout, object allocation, GC algorithms, and tuning"
tags: ["java"]
draft: true
---

# JVM Memory & Object Lifecycle

> These two topics are tightly coupled — where an object lives in memory determines how and when it gets collected.

## 1. JVM Runtime Memory Layout

```
┌──────────────────────────────────────────────────────────────┐
│                         JVM Process                           │
│                                                               │
│  ┌──────────────── Thread-Shared Areas ────────────────────┐  │
│  │                                                         │  │
│  │  ┌─── Heap ──────────────────────────────────────────┐  │  │
│  │  │                                                   │  │  │
│  │  │  ┌─ Young Generation (1/3 of heap) ────────────┐  │  │  │
│  │  │  │  ┌─ Eden (8/10) ─┐ ┌─ S0 (1/10)┐┌─ S1 ─┐  │  │  │  │
│  │  │  │  │  new objects   │ │ from-space ││to-spc│  │  │  │  │
│  │  │  │  │  allocated     │ │ survivors  ││empty │  │  │  │  │
│  │  │  │  │  here (TLAB)   │ │            ││      │  │  │  │  │
│  │  │  │  └────────────────┘ └───────────┘└──────┘  │  │  │  │
│  │  │  └─────────────────────────────────────────────┘  │  │  │
│  │  │                                                   │  │  │
│  │  │  ┌─ Old Generation (2/3 of heap) ──────────────┐  │  │  │
│  │  │  │  long-lived objects, large objects            │  │  │  │
│  │  │  │  promoted from Young Gen                     │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  │                                                   │  │  │
│  │  └───────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  ┌─── Metaspace (native memory, NOT in heap) ───────┐  │  │
│  │  │  - Class metadata (bytecode, field/method info)   │  │  │
│  │  │  - Runtime constant pool (literals, symbol refs)  │  │  │
│  │  │  - String pool (interned strings, since Java 7)   │  │  │
│  │  │  - Static variables references                    │  │  │
│  │  │  Grows dynamically, limited by native memory      │  │  │
│  │  │  -XX:MaxMetaspaceSize to cap it                   │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────── Per-Thread Areas ───────────────────────┐  │
│  │                                                         │  │
│  │  ┌─── VM Stack ──────────────────────────────────────┐  │  │
│  │  │  One stack per thread, composed of stack frames    │  │  │
│  │  │                                                    │  │  │
│  │  │  ┌─ Stack Frame (per method call) ──────────────┐  │  │  │
│  │  │  │  - Local Variable Table: primitives stored    │  │  │  │
│  │  │  │    directly, objects stored as references      │  │  │  │
│  │  │  │  - Operand Stack: working area for bytecode   │  │  │  │
│  │  │  │  - Dynamic Linking: resolve symbolic refs     │  │  │  │
│  │  │  │  - Return Address: where to go after return   │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  │                                                    │  │  │
│  │  │  StackOverflowError: too many frames (deep        │  │  │
│  │  │  recursion). -Xss to set stack size (default      │  │  │
│  │  │  512KB-1MB depending on platform)                  │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  ┌─── PC Register ──────────────────────────────────┐  │  │
│  │  │  Address of current bytecode instruction          │  │  │
│  │  │  Undefined for native methods                     │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  ┌─── Native Method Stack ──────────────────────────┐  │  │
│  │  │  For JNI calls (C/C++ code)                       │  │  │
│  │  │  Similar to VM Stack but for native methods       │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────── Direct Memory ──────────────────────────┐  │
│  │  NIO ByteBuffer.allocateDirect() — off-heap             │  │
│  │  Not managed by GC (but DirectByteBuffer reference is)  │  │
│  │  Avoids copying between JVM heap and native memory      │  │
│  │  Used in Netty, LMAX Disruptor for zero-copy I/O        │  │
│  │  -XX:MaxDirectMemorySize to limit                       │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 2. Heap vs Native Memory — What's the Physical Reality?

> There is only one physical RAM. Both "heap" and "native memory" are regions of the **same RAM**. The difference is **who manages that memory**.

```
Physical RAM (e.g., 16GB)
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  ┌─── JVM Process (virtual address space) ─────────────┐  │
│  │                                                      │  │
│  │  ┌─ Heap (managed by JVM & GC) ──────────────────┐  │  │
│  │  │  JVM requests memory from OS (mmap/brk)       │  │  │
│  │  │  JVM controls allocation internally:           │  │  │
│  │  │    TLAB bump pointer, free lists               │  │  │
│  │  │  GC tracks every object, moves/compacts them   │  │  │
│  │  │  Size: -Xms (initial) to -Xmx (max)           │  │  │
│  │  │  Content: all Java objects (new Foo())          │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                      │  │
│  │  ┌─ Native Memory (managed by OS / malloc) ───────┐  │  │
│  │  │  Metaspace: JVM calls malloc() for class info  │  │  │
│  │  │  DirectByteBuffer: malloc() for NIO buffers    │  │  │
│  │  │  Thread stacks: OS allocates per thread (-Xss) │  │  │
│  │  │  JNI: C/C++ native code uses malloc/free       │  │  │
│  │  │  Code cache: JIT compiled machine code         │  │  │
│  │  │                                                │  │  │
│  │  │  GC does NOT manage this!                      │  │  │
│  │  │  Freed by: Cleaner, explicit free, or          │  │  │
│  │  │  process exit                                  │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─── Other Processes ────────────────────────────────┐   │
│  │  ...                                                │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

**No data "copies" between heap and native in the general case** — they're just different regions of RAM with different management. The one exception is **I/O**:

```
Heap I/O (slow — extra copy):
  App writes heapBuffer ──► JVM copies to temp native buffer ──► OS kernel (DMA to NIC)
                                  ↑
                       Why? GC might MOVE the heap object mid-transfer.
                       OS kernel needs a stable memory address for DMA.

Direct I/O (fast — no copy):
  App writes directBuffer ──► OS kernel (DMA to NIC)
                                Already in native memory, stable address.
```

This is why `DirectByteBuffer` exists and why Netty/Kafka use it — skip the heap-to-native copy on every I/O operation. The trade-off: allocation is slower (OS `malloc` vs JVM bump pointer) and must be manually managed (reference counting or `Cleaner`), but I/O throughput is significantly better.

**Common confusion clarified**:
- "Heap" is NOT a special hardware area — it's a chunk of RAM that the JVM requested from the OS and manages internally with its own allocator and GC
- "Native memory" is NOT different hardware — it's RAM allocated via standard OS calls (`malloc`, `mmap`) that the JVM does not track with GC
- Metaspace is native memory — that's why it's not bounded by `-Xmx` but by physical RAM (or `-XX:MaxMetaspaceSize`)
- A `DirectByteBuffer` object itself lives on the heap (so GC tracks the reference), but its actual data buffer is in native memory (so GC doesn't move it)

## 3. Where Does Each Thing Live?

```java
public class Example {
    private static int COUNT = 0;          // static var ref → Metaspace, value is primitive
    private static final String TAG = "X"; // "X" → String Pool (Metaspace)
    private int id;                        // instance field → Heap (part of object)

    public void process() {
        int localVar = 42;                 // primitive → VM Stack (local variable table)
        Object obj = new Object();         // reference → VM Stack, object → Heap (Eden)
        String s1 = "hello";              // reference → VM Stack, "hello" → String Pool
        String s2 = new String("hello");  // reference → VM Stack, new String → Heap (Eden)
                                          // "hello" literal also in String Pool
    }
}
```

**Key points:**
- **Primitives** in local variables → stack; as instance fields → heap (part of the object)
- **Object references** (pointers) → stack or heap (depending on where declared); actual object → always heap
- **String literals** → String Pool (moved from PermGen to Heap in Java 7, conceptually part of Metaspace management)
- **Class metadata** → Metaspace (native memory, replaced PermGen in Java 8)

## 4. TLAB — Thread-Local Allocation Buffer

Allocating objects in Eden requires synchronization (multiple threads compete). TLAB solves this:

```
Eden Space
┌──────────────────────────────────────────────┐
│  ┌─ TLAB Thread-1 ─┐  ┌─ TLAB Thread-2 ─┐  │
│  │  [obj1] [obj2]   │  │  [obj3]          │  │
│  │  ▲ alloc ptr     │  │  ▲ alloc ptr     │  │
│  └──────────────────┘  └──────────────────┘  │
│                                              │
│         ┌─ TLAB Thread-3 ─┐                  │
│         │  [obj4] [obj5]   │                 │
│         └──────────────────┘                  │
└──────────────────────────────────────────────┘
```

- Each thread gets a **private chunk** of Eden (TLAB)
- Allocation = bump the pointer, no locking needed (very fast)
- When TLAB is full → request a new one (this needs synchronization, but rare)
- Enabled by default (`-XX:+UseTLAB`)

## 5. Object Memory Layout (HotSpot 64-bit)

Every object on the heap has this internal structure:

```
┌───────────────────────────────────────────────┐
│              Object Header                     │
│  ┌─ Mark Word (8 bytes) ──────────────────┐   │
│  │  - hashCode (31 bits)                  │   │
│  │  - GC age (4 bits, max 15)             │   │
│  │  - lock state (2 bits)                 │   │
│  │  - biased lock thread ID               │   │
│  │  (reused based on lock state)          │   │
│  └────────────────────────────────────────┘   │
│  ┌─ Klass Pointer (4 bytes compressed) ───┐   │
│  │  pointer to class metadata in Metaspace│   │
│  └────────────────────────────────────────┘   │
│  ┌─ Array Length (4 bytes, arrays only) ──┐   │
│  │  only present for array objects        │   │
│  └────────────────────────────────────────┘   │
├───────────────────────────────────────────────┤
│              Instance Data                     │
│  fields ordered by type width:                │
│  longs/doubles → ints/floats → shorts/chars   │
│  → bytes/booleans → references                │
│  (to minimize padding)                        │
├───────────────────────────────────────────────┤
│              Padding                           │
│  align to 8-byte boundary                     │
└───────────────────────────────────────────────┘
```

**Mark Word is key for interviews** — it changes based on lock state:

| Lock State | Mark Word Content |
|-----------|-------------------|
| No lock | hashCode (31) + age (4) + biased (1) + lock (2) |
| Biased lock | thread ID (54) + epoch (2) + age (4) + biased (1) + lock (2) |
| Lightweight lock | pointer to lock record in stack |
| Heavyweight lock | pointer to monitor object |
| GC marked | forwarding address |

The **GC age** field is only 4 bits → max value 15 → that's why `-XX:MaxTenuringThreshold` max is 15.

## 6. Object Allocation & Lifecycle — The Full Journey

```
                    new Object()
                         │
                         ▼
              ┌─ Escape Analysis ─┐
              │  Does the object  │
              │  escape the       │
              │  method scope?    │
              └────────┬──────────┘
                 no/   │   \yes
                /      │    \
               ▼       │     ▼
     Stack Alloc       │   ┌─────────────────────┐
     (rare,            │   │  Is it a large       │
      JIT only,        │   │  object?             │
      no GC needed)    │   │  > PretenureSizeThreshold
                       │   └──────────┬──────────┘
                       │        no/   │   \yes
                       │       /      │    \
                       │      ▼       │     ▼
                       │   ┌──────┐   │  Old Gen (directly)
                       │   │ TLAB │   │
                       │   │ full?│   │
                       │   └──┬───┘   │
                       │  no/ │ \yes  │
                       │ /    │  \    │
                       ▼▼     │   ▼   │
                    TLAB      │  CAS alloc in Eden
                    bump ptr  │  (slower, needs sync)
                              │
                              ▼
        ┌─────── Object now lives in Eden ────────┐
        │                                          │
        │  Eden fills up → Minor GC (Young GC)     │
        │                                          │
        │  GC uses reachability analysis:          │
        │  start from GC Roots, traverse refs      │
        │                                          │
        │  GC Roots include:                       │
        │  - local vars in active stack frames     │
        │  - static fields                         │
        │  - JNI references                        │
        │  - active threads                        │
        │  - synchronized monitors                 │
        └──────────────────┬───────────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Is object          │
                │  reachable from     │
                │  GC Roots?          │
                └──────────┬──────────┘
              yes/         │        \no
             /             │         \
            ▼              │          ▼
     Copy to Survivor      │     Collected (dead)
     (S0 or S1)            │
     age = 1               │
            │              │
            ▼              │
     ┌─ Next Minor GC ─┐  │
     │  Still alive?    │  │
     └───────┬──────────┘  │
        yes/ │ \no         │
       /     │  \          │
      ▼      │   ▼         │
   Copy to   │  Collected  │
   other     │             │
   Survivor  │             │
   age++     │             │
      │      │             │
      ▼      │             │
   ┌─ Promotion conditions ────────────────────┐
   │  1. age >= MaxTenuringThreshold (def 15)  │
   │  2. Survivor space > 50% filled with      │
   │     objects of same age (dynamic age)      │
   │  3. Survivor can't hold all survivors      │
   └──────────────────┬────────────────────────┘
                      │
                      ▼
               ┌─ Old Gen ─────────────────────┐
               │                                │
               │  Collected by Major GC/Full GC │
               │  Much less frequent            │
               │  Usually triggers STW pause    │
               └────────────────────────────────┘
```

## 7. Reachability — How GC Decides What's Alive

Java does NOT use reference counting (Python does). Instead it uses **reachability analysis** — trace from GC Roots down:

```
GC Roots
   │
   ├──► static field ──► ObjectA ──► ObjectB
   │                                   │
   ├──► local var ──► ObjectC          │
   │                    │              │
   │                    └──► ObjectD ◄─┘
   │
   └──► ObjectE (directly referenced)

ObjectF ◄──► ObjectG   ← circular reference, but UNREACHABLE from roots
                         → both will be collected!
```

**This is why Java handles circular references** — unlike Python's reference counting, reachability analysis doesn't care about cycles. If you can't reach it from a GC Root, it's garbage.

## 8. Reference Types (determines GC behavior)

```java
// Strong — never collected while reachable
Object obj = new Object();

// Soft — collected only when memory is low (before OOM)
SoftReference<Object> soft = new SoftReference<>(new Object());
// Use case: memory-sensitive caches

// Weak — collected at next GC regardless of memory
WeakReference<Object> weak = new WeakReference<>(new Object());
// Use case: WeakHashMap, avoid memory leaks in caches

// Phantom — already finalized, used to schedule cleanup
PhantomReference<Object> phantom = new PhantomReference<>(obj, queue);
// Use case: Cleaner API, replace finalize()
```

| Reference Type | GC Behavior | Survives Minor GC? | Survives Full GC? | Use Case |
|---------------|-------------|--------------------|--------------------|----------|
| **Strong** | Never collected if reachable | Yes | Yes | Default |
| **Soft** | Collected when memory is low | Yes (usually) | No (if low) | Cache |
| **Weak** | Collected at next GC | No | No | WeakHashMap |
| **Phantom** | Already collected, pending cleanup | No | No | Cleaner |

## 9. GC Algorithms in Detail

### STW — Stop-The-World

STW means the JVM **pauses all application threads** while GC works. No user code executes — the entire application freezes.

```
App Threads:  ──────────┤  FROZEN  ├──────────►
                        │          │
GC Thread:              ├─ GC work ┤
                        │          │
                    STW start   STW end
```

**Why it's necessary**: GC needs a consistent snapshot of the object graph. If app threads keep creating/modifying references while GC is scanning, it might miss live objects (collect something still in use) or never converge (new garbage keeps appearing).

**How different GCs handle STW**:

| GC | What's STW | What's Concurrent | Typical Pause |
|----|-----------|-------------------|---------------|
| **Serial / Parallel** | Everything (mark + sweep/compact) | Nothing | Hundreds of ms to seconds |
| **CMS** | Initial mark + remark only | Concurrent mark + sweep | ~10-50ms |
| **G1** | Young GC + remark + cleanup | Concurrent marking | Tunable (~200ms default) |
| **ZGC** | Root scanning only | Mark + relocate + remap | < 1ms regardless of heap size |

For a trading system like OKX, a 200ms STW pause during order matching could mean missed trades or stale prices. That's why ZGC (sub-1ms pauses) or careful G1 tuning is critical.

### Mark-Sweep

```
Before:   [A][B][C][D][E][F][G]    (B, D, F are garbage)

Mark:     [A][ ][C][ ][E][ ][G]    mark reachable objects

Sweep:    [A][_][C][_][E][_][G]    free unmarked objects

Problem:  memory fragmentation! Large objects may not find contiguous space
```

### Mark-Compact

```
Before:   [A][_][C][_][E][_][G]    (after sweep, fragmented)

Compact:  [A][C][E][G][_][_][_]    slide objects to one end

Benefit:  no fragmentation, but requires moving objects (update all references)
          more expensive than mark-sweep
```

### Copying (used in Young Gen)

```
From-Space (S0):  [A][B][C][D]     (B, D are garbage)
To-Space (S1):    [_][_][_][_]

Copy alive:
From-Space (S0):  [A][B][C][D]
To-Space (S1):    [A][C][_][_]     only copy live objects

Swap roles:
S0 (now empty):   [_][_][_][_]     becomes new to-space
S1 (now active):  [A][C][_][_]     becomes new from-space

Benefit:  no fragmentation, simple and fast
Cost:     wastes 50% of space (that's why Survivor is split S0/S1)
```

**Why Eden:S0:S1 = 8:1:1?**
- IBM research showed ~98% of objects die young (Weak Generational Hypothesis)
- Eden is large because most objects die immediately
- Only ~2% survive → S0/S1 only needs to be small
- Wasted space is only 10% (one Survivor), not 50%

## 10. GC Collectors — Detailed

### G1 (Garbage-First)

```
Heap divided into ~2048 equal-sized regions (1-32MB each):

┌───┬───┬───┬───┬───┬───┬───┬───┐
│ E │ E │ S │ O │ O │ H │ H │ E │
├───┼───┼───┼───┼───┼───┼───┼───┤
│ O │ E │   │ O │ S │ E │ O │ O │
├───┼───┼───┼───┼───┼───┼───┼───┤
│   │ O │ E │ E │ O │   │ O │ E │
└───┴───┴───┴───┴───┴───┴───┴───┘

E = Eden    S = Survivor    O = Old    H = Humongous
(blank = free)

Humongous: objects > 50% of region size, allocated in contiguous regions
```

G1 GC phases:
1. **Young GC** — collect all Eden + Survivor regions (STW, parallel)
2. **Concurrent Marking** — trace live objects across entire heap (mostly concurrent)
   - Initial Mark (STW, piggyback on Young GC)
   - Concurrent Mark (concurrent with app)
   - Remark (STW, short, handle SATB changes)
   - Cleanup (STW, identify empty regions)
3. **Mixed GC** — collect Young + some Old regions with most garbage (that's the "Garbage-First" name)

Key tuning: `-XX:MaxGCPauseMillis=200` (default) — G1 selects how many regions to collect to meet the pause target.

### ZGC (Java 11+, production-ready Java 15+)

Core innovations:
- **Colored pointers**: uses 4 bits in the 64-bit pointer for GC metadata (marked0, marked1, remapped, finalizable). No separate mark bitmap needed.
- **Load barriers**: every reference load goes through a barrier that checks pointer color. If stale, fix it on the spot (self-healing). This is how ZGC does concurrent relocation without STW.
- **Concurrent phases**: almost everything concurrent — marking, relocation, reference processing

```
ZGC Phases:
1. Pause Mark Start    (STW ~1ms)  — scan GC roots
2. Concurrent Mark     (concurrent) — trace object graph
3. Pause Mark End      (STW ~1ms)  — handle edge cases
4. Concurrent Relocate (concurrent) — move objects, update via load barriers
```

Why sub-millisecond pauses regardless of heap size: the only STW work is scanning GC roots (thread stacks, static fields). Everything else — traversing the object graph, moving objects — happens concurrently. Heap could be 16TB, pause is still ~1ms.

## 11. Common OOM Scenarios

| OOM Type | Cause | Diagnosis |
|----------|-------|-----------|
| `Java heap space` | Too many objects, memory leak | Heap dump (`-XX:+HeapDumpOnOutOfMemoryError`), analyze with MAT/VisualVM |
| `Metaspace` | Too many classes loaded (CGLIB, dynamic proxies) | `-XX:MaxMetaspaceSize`, check class loader leaks |
| `GC overhead limit exceeded` | >98% time in GC, <2% heap recovered | Same as heap space — likely memory leak |
| `Direct buffer memory` | Too many NIO DirectByteBuffer | `-XX:MaxDirectMemorySize`, ensure buffers are released |
| `unable to create new native thread` | Too many threads | Reduce `-Xss`, or increase OS ulimit |
| `StackOverflowError` | Deep/infinite recursion | Fix recursion, or increase `-Xss` |

## 12. Key JVM Flags Cheat Sheet

```bash
# Heap sizing
-Xms4g                  # initial heap size
-Xmx4g                  # max heap size (set equal to Xms to avoid resize)
-Xmn1g                  # young gen size (or use -XX:NewRatio=2 for Old:Young=2:1)

# GC selection
-XX:+UseG1GC            # G1 (default Java 9+)
-XX:+UseZGC             # ZGC
-XX:+UseShenandoahGC    # Shenandoah

# GC tuning
-XX:MaxGCPauseMillis=200       # G1 pause target
-XX:MaxTenuringThreshold=15    # max age before promotion (max 15)
-XX:PretenureSizeThreshold=1m  # objects larger than this go directly to Old Gen

# Metaspace
-XX:MetaspaceSize=256m         # initial metaspace (triggers GC when exceeded)
-XX:MaxMetaspaceSize=512m      # max metaspace

# Diagnostics
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/tmp/heapdump.hprof
-XX:+PrintGCDetails -Xloggc:gc.log    # GC logging (Java 8)
-Xlog:gc*:file=gc.log                  # GC logging (Java 9+)

# Stack
-Xss512k                # thread stack size

# Direct memory
-XX:MaxDirectMemorySize=1g
```
