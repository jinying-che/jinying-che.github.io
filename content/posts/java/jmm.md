---
title: "Java Memory Model (JMM)"
date: 2026-03-19T00:00:00+08:00
description: "Deep dive into JMM — visibility, ordering, volatile, happens-before, and singleton patterns"
tags: ["java"]
draft: true
---

# Java Memory Model (JMM)

> JMM ≠ JVM memory layout. JVM layout = where data physically lives. JMM = what guarantees threads have when reading/writing shared data.

## 1. The Problem — Why We Need JMM

```
                 Main Memory
            ┌───────────────────┐
            │   shared variable │
            │   flag = false    │
            └───────┬───────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
    ┌────▼────┐ ┌───▼────┐ ┌──▼─────┐
    │ CPU 1   │ │ CPU 2  │ │ CPU 3  │
    │ Cache   │ │ Cache  │ │ Cache  │
    │ flag=?  │ │ flag=? │ │ flag=? │
    │ Thread A│ │Thread B│ │Thread C│
    └─────────┘ └────────┘ └────────┘
```

Modern CPUs have multiple levels of cache (L1/L2 per core, L3 shared). When Thread A writes `flag = true`:
1. It might only update CPU 1's L1 cache
2. Thread B on CPU 2 still sees the old value in its own cache
3. Even after flushing to main memory, the CPU/compiler may **reorder instructions** for performance

```java
// Thread A                    // Thread B
x = 1;                         while (!flag) { }  // might loop forever
flag = true;                   System.out.println(x);  // might print 0!
```

Two problems:
1. **Visibility**: Thread B may never see `flag = true`
2. **Ordering**: compiler/CPU may reorder Thread A's instructions: `flag = true` before `x = 1`

## 2. `volatile` — Visibility + Ordering

```java
volatile boolean flag = false;
```

| Guarantee | Meaning | How (hardware level) |
|-----------|---------|---------------------|
| **Visibility** | Write flushes to main memory; read always from main memory | Store barrier after write, load barrier before read |
| **Ordering** | No reordering across volatile read/write | Memory fence instructions (mfence/sfence/lfence on x86) |
| **NOT atomic** | `volatile int count; count++` is NOT thread-safe | count++ = read + increment + write = 3 operations |

**Volatile memory barrier rules:**

```
    ┌──────────────────────────────────────────┐
    │  Before volatile WRITE:                   │
    │    StoreStore barrier                     │
    │    (flush all previous writes)            │
    │  After volatile WRITE:                    │
    │    StoreLoad barrier                      │
    │    (prevent reorder with subsequent reads) │
    ├──────────────────────────────────────────┤
    │  Before volatile READ:                    │
    │    LoadLoad barrier                       │
    │    (invalidate cache, read from memory)   │
    │  After volatile READ:                     │
    │    LoadStore barrier                      │
    │    (prevent reorder with subsequent write) │
    └──────────────────────────────────────────┘
```

## 3. Happens-Before Rules (complete list)

Happens-before defines the **ordering guarantee** — if A happens-before B, then A's effects are visible to B.

```
1. Program order rule:     within a thread, earlier → later
2. Monitor lock rule:      unlock → subsequent lock of same monitor
3. Volatile variable rule: volatile write → subsequent volatile read of same var
4. Thread start rule:      threadA.start() → any action in threadA
5. Thread join rule:       any action in threadA → threadA.join() returns
6. Thread interrupt rule:  threadA.interrupt() → threadB detects interrupt
7. Finalizer rule:         constructor end → finalize() begin
8. Transitivity:           if A hb B, B hb C → A hb C
```

## 4. Double-Checked Locking — Dissected Step by Step

```java
class Singleton {
    private static volatile Singleton instance;  // volatile is REQUIRED

    public static Singleton getInstance() {
        if (instance == null) {                  // 1st check — no lock, fast path
            synchronized (Singleton.class) {     // only lock on first creation
                if (instance == null) {           // 2nd check — another thread may have created
                    instance = new Singleton();   // the dangerous line
                }
            }
        }
        return instance;
    }
}
```

**Why is `volatile` required?** `instance = new Singleton()` compiles to 3 steps:

```
1. memory = allocate()         // allocate memory
2. init(memory)                // call constructor, initialize fields
3. instance = memory           // assign reference

CPU/compiler may REORDER to:
1. memory = allocate()
3. instance = memory           // reference assigned BEFORE init!
2. init(memory)                // constructor runs AFTER assignment

Thread B does 1st check: instance != null → returns half-constructed object!
```

`volatile` prevents this reorder via StoreStore barrier before the write.

## 5. Other Safe Singleton Patterns

```java
// 1. Enum — simplest and best (recommended by Effective Java)
//    - Thread-safe by JVM guarantee
//    - Prevents reflection and serialization attacks
//    - Lazy loaded when enum class is first accessed
enum Singleton {
    INSTANCE;
    public void doSomething() { }
}

// 2. Static inner class — lazy loading via class loader mechanism
//    - Holder class is NOT loaded until getInstance() is called
//    - Class loading is thread-safe by JVM spec (ClassLoader lock)
//    - No synchronization overhead after initialization
class Singleton {
    private Singleton() {}
    private static class Holder {
        static final Singleton INSTANCE = new Singleton();  // loaded on first access
    }
    public static Singleton getInstance() {
        return Holder.INSTANCE;  // triggers Holder class loading
    }
}

// 3. Eager initialization — simplest but not lazy
//    - Created when class is loaded, even if never used
class Singleton {
    private static final Singleton INSTANCE = new Singleton();
    private Singleton() {}
    public static Singleton getInstance() { return INSTANCE; }
}
```

| Pattern | Lazy? | Thread-safe? | Reflection-safe? | Serialization-safe? |
|---------|-------|-------------|------------------|-------------------|
| Double-checked locking | Yes | Yes (with volatile) | No | No |
| Static inner class | Yes | Yes (ClassLoader) | No | No |
| Enum | Yes | Yes (JVM) | Yes | Yes |
| Eager | No | Yes (class loading) | No | No |
