---
title: "Java Concurrency"
date: 2026-03-19T00:00:00+08:00
description: "Deep dive into Java concurrency — locks, thread pools, AQS, CAS, ThreadLocal, and CompletableFuture"
tags: ["java"]
draft: true
---

# Java Concurrency

## 1. Thread Lifecycle

```
         start()
NEW ──────────► RUNNABLE ◄─────────────────────────┐
                   │                                │
                   │                                │
          ┌────────┼────────────────┐               │
          │        │                │               │
          ▼        ▼                ▼               │
      BLOCKED   WAITING      TIMED_WAITING         │
      (monitor  (wait(),     (sleep(ms),            │
       lock)    join(),       wait(ms),             │
                park())       join(ms),             │
          │        │          parkNanos())           │
          │        │                │               │
          └────────┴────────────────┘               │
                   │                                │
                   │  (lock acquired / notified /   │
                   │   interrupted / timeout)        │
                   └────────────────────────────────┘
                   │
                   ▼
              TERMINATED
```

**Key distinctions**:
- **BLOCKED**: waiting to acquire a monitor lock (entering `synchronized` block)
- **WAITING**: waiting indefinitely for another thread's action (`wait()`, `join()`, `LockSupport.park()`)
- **TIMED_WAITING**: same as WAITING but with timeout
- `Thread.sleep()` does NOT release the lock; `Object.wait()` DOES release the lock

## 2. synchronized — Monitor Lock

Every Java object has an associated monitor. `synchronized` acquires that monitor.

```java
// Method level — locks 'this' (or Class object for static)
public synchronized void method() { }
public static synchronized void staticMethod() { }  // locks Class object

// Block level — locks specified object (more flexible)
synchronized (lockObject) {
    // critical section
}
```

### Lock Escalation (HotSpot optimization)

The Mark Word in object header changes as lock contention increases:

```
No Lock (anonymous, hashCode stored)
    │
    ▼ (first thread accesses)
Biased Lock — Mark Word stores thread ID
    │         No CAS needed for same thread to re-enter
    │         Fastest: just check thread ID
    │
    ▼ (second thread tries to acquire)
Lightweight Lock — Mark Word points to Lock Record on stack
    │               CAS to swap Mark Word
    │               Spin-wait if contended (short)
    │
    ▼ (spin fails / too many threads)
Heavyweight Lock — Mark Word points to ObjectMonitor (OS mutex)
                   Thread blocks (context switch, expensive)
                   Has wait set and entry set for wait/notify
```

**Note**: Biased locking was deprecated in Java 15 and removed in Java 18 — the overhead of revocation outweighed benefits in modern workloads.

### wait() / notify() / notifyAll()

```java
synchronized (lock) {
    while (!condition) {        // ALWAYS use while, never if
        lock.wait();            // releases lock, enters WAITING
    }                           // re-acquires lock when notified
    // condition is true, proceed
}

synchronized (lock) {
    condition = true;
    lock.notifyAll();           // wake ALL waiting threads
    // lock.notify();           // wake ONE (unpredictable which one — avoid)
}
```

**Why `while` not `if`?**
- Spurious wakeups: thread may wake without notify
- Multiple waiters: another thread may have consumed the condition between notify and re-acquiring lock

## 3. ReentrantLock — More Flexible Locking

```java
ReentrantLock lock = new ReentrantLock();       // unfair by default
ReentrantLock fairLock = new ReentrantLock(true); // fair: FIFO order

lock.lock();
try {
    // critical section
} finally {
    lock.unlock();   // MUST be in finally — unlike synchronized, no auto-release
}
```

### synchronized vs ReentrantLock

| Feature | synchronized | ReentrantLock |
|---------|-------------|---------------|
| Release | Automatic (exit block/method) | Manual (`unlock()` in finally) |
| Interruptible | No | Yes (`lockInterruptibly()`) |
| Try with timeout | No | Yes (`tryLock(timeout, unit)`) |
| Condition variables | 1 (`wait`/`notify`) | Multiple (`newCondition()`) |
| Fair locking | No (always unfair) | Optional (`new ReentrantLock(true)`) |
| Performance | Optimized in modern JVMs | Slightly more overhead |
| Reentrant | Yes | Yes |
| Deadlock detection | No | `tryLock()` can prevent |

### Condition — Multiple Wait Sets

```java
ReentrantLock lock = new ReentrantLock();
Condition notEmpty = lock.newCondition();   // for consumers
Condition notFull = lock.newCondition();    // for producers

// Producer
lock.lock();
try {
    while (count == capacity)
        notFull.await();            // wait on notFull condition
    // add item
    notEmpty.signal();              // wake a consumer
} finally { lock.unlock(); }

// Consumer
lock.lock();
try {
    while (count == 0)
        notEmpty.await();           // wait on notEmpty condition
    // remove item
    notFull.signal();               // wake a producer
} finally { lock.unlock(); }
```

Advantage over `wait/notify`: producers only wake consumers (not other producers), and vice versa.

### ReadWriteLock — Shared Reading

```java
ReadWriteLock rwLock = new ReentrantReadWriteLock();

// Multiple threads can read concurrently
rwLock.readLock().lock();
try { /* read */ } finally { rwLock.readLock().unlock(); }

// Only one thread can write, blocks all readers too
rwLock.writeLock().lock();
try { /* write */ } finally { rwLock.writeLock().unlock(); }
```

| | Read Lock Held | Write Lock Held |
|---|---|---|
| **Read Lock request** | Granted (shared) | Blocked |
| **Write Lock request** | Blocked | Blocked |

**StampedLock (Java 8+)**: adds optimistic read — no locking, just validate after:

```java
StampedLock sl = new StampedLock();

// Optimistic read — no blocking, no lock acquisition
long stamp = sl.tryOptimisticRead();
int x = this.x;
int y = this.y;
if (!sl.validate(stamp)) {       // check if a write happened during read
    stamp = sl.readLock();        // fallback to pessimistic read
    try {
        x = this.x;
        y = this.y;
    } finally { sl.unlockRead(stamp); }
}
```

## 4. CAS & Atomic Classes

### CAS — Compare And Swap

```
CAS(memory_location, expected_value, new_value)

1. Read current value at memory_location
2. If current == expected → atomically write new_value → return true
3. If current != expected → do nothing → return false

Hardware instruction: x86 CMPXCHG (single CPU instruction, atomic)
```

```java
// AtomicInteger uses CAS internally
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();   // CAS loop: read → increment → CAS → retry if failed

// Equivalent to:
int oldVal, newVal;
do {
    oldVal = count.get();
    newVal = oldVal + 1;
} while (!count.compareAndSet(oldVal, newVal));  // retry until CAS succeeds
```

### ABA Problem

```
Thread 1: reads value A
Thread 2: changes A → B → A
Thread 1: CAS(expected=A, new=C) → succeeds! (doesn't know value changed)

Solution: AtomicStampedReference — adds a version stamp
```

```java
AtomicStampedReference<Integer> ref = new AtomicStampedReference<>(100, 0);

int[] stampHolder = new int[1];
int value = ref.get(stampHolder);     // value=100, stamp=0
int stamp = stampHolder[0];

// CAS checks BOTH value AND stamp
ref.compareAndSet(100, 200, stamp, stamp + 1);  // stamp prevents ABA
```

### Atomic Classes Summary

| Class | Use Case |
|-------|----------|
| `AtomicInteger/Long/Boolean` | Single primitive atomic ops |
| `AtomicReference<V>` | Single reference atomic ops |
| `AtomicStampedReference<V>` | Reference + version (solves ABA) |
| `AtomicIntegerArray` | Array elements atomic ops |
| `LongAdder` / `LongAccumulator` | High-contention counters (distributed cells, like ConcurrentHashMap.size()) |

**`LongAdder` vs `AtomicLong`**:
- `AtomicLong`: single variable, every thread CAS on same location → high contention
- `LongAdder`: distributes across `Cell[]` array, each thread picks a cell → much less contention
- `sum()` = base + sum(cells) — eventually consistent, not atomic snapshot
- Use `LongAdder` for counters/metrics; `AtomicLong` when you need exact current value

## 5. AQS — AbstractQueuedSynchronizer

AQS is the foundation for `ReentrantLock`, `Semaphore`, `CountDownLatch`, `ReentrantReadWriteLock`.

```
AQS Core:
┌─────────────────────────────┐
│  volatile int state          │  ← meaning depends on implementation
│                              │     ReentrantLock: 0=free, >0=held (reentrant count)
│  Thread exclusiveOwnerThread │     Semaphore: number of permits
│                              │     CountDownLatch: count
│  CLH Queue (FIFO):          │
│  ┌──────┐  ┌──────┐  ┌──────┐
│  │ Head │→│ Node │→│ Tail │  ← waiting threads
│  │(dummy)│  │ T1   │  │ T2   │
│  └──────┘  └──────┘  └──────┘
└─────────────────────────────┘
```

**How ReentrantLock.lock() works via AQS**:

```
1. tryAcquire(1):
   - CAS state 0 → 1, set exclusiveOwnerThread = current
   - If current thread already owns: state++ (reentrant)
   - If fails: go to step 2

2. addWaiter(EXCLUSIVE):
   - Create Node for current thread
   - CAS append to CLH queue tail

3. acquireQueued(node):
   - Spin: if predecessor is head, try tryAcquire again
   - If still fails: park() the thread (LockSupport.park)

4. On unlock: tryRelease(1)
   - state-- (if 0: fully released)
   - Unpark head's successor thread
```

## 6. ThreadPoolExecutor

### 7 Parameters

```java
ThreadPoolExecutor(
    int corePoolSize,        // threads kept alive even when idle
    int maximumPoolSize,     // max threads allowed
    long keepAliveTime,      // idle time before non-core threads die
    TimeUnit unit,           // time unit for keepAliveTime
    BlockingQueue<Runnable> workQueue,   // task queue
    ThreadFactory threadFactory,          // custom thread creation (naming!)
    RejectedExecutionHandler handler     // what to do when full
)
```

### Task Submission Flow

```
submit(task)
    │
    ▼
┌─ workerCount < corePoolSize? ─┐
│           YES                  │
│  Create core thread, run task  │
└────────────────────────────────┘
    │ NO
    ▼
┌─ workQueue.offer(task)? ───────┐
│           YES                   │
│  Task added to queue, wait     │
└─────────────────────────────────┘
    │ NO (queue full)
    ▼
┌─ workerCount < maximumPoolSize?┐
│           YES                   │
│  Create non-core thread         │
└─────────────────────────────────┘
    │ NO
    ▼
┌─ RejectedExecutionHandler ─────┐
│  AbortPolicy: throw exception  │  ← default
│  DiscardPolicy: silently drop  │
│  DiscardOldestPolicy: drop     │
│    oldest queued task           │
│  CallerRunsPolicy: caller      │
│    thread runs the task         │  ← best for backpressure
└─────────────────────────────────┘
```

### Queue Types

| Queue | Behavior | Use Case |
|-------|----------|----------|
| `LinkedBlockingQueue` | Unbounded (or bounded) FIFO | `Executors.newFixedThreadPool` — careful: unbounded can OOM |
| `ArrayBlockingQueue` | Bounded FIFO | Best for production — explicit capacity |
| `SynchronousQueue` | Zero capacity, direct handoff | `Executors.newCachedThreadPool` — creates thread per task |
| `PriorityBlockingQueue` | Unbounded, priority-ordered | Task prioritization |

### Thread Pool Sizing

```
CPU-bound tasks:   threads = CPU cores + 1
                   (extra thread covers when one thread pauses for page fault etc.)

I/O-bound tasks:   threads = CPU cores × (1 + wait_time / compute_time)
                   e.g., 8 cores, tasks wait 80% of time:
                   8 × (1 + 0.8/0.2) = 8 × 5 = 40 threads
```

### Why NOT Use Executors Factory Methods

```java
// DANGER: LinkedBlockingQueue is UNBOUNDED → OOM
ExecutorService bad1 = Executors.newFixedThreadPool(10);

// DANGER: maximumPoolSize = Integer.MAX_VALUE → thread explosion
ExecutorService bad2 = Executors.newCachedThreadPool();

// GOOD: explicit, bounded everything
ExecutorService good = new ThreadPoolExecutor(
    10, 20, 60, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(1000),         // bounded queue
    new ThreadFactoryBuilder().setNameFormat("worker-%d").build(),
    new ThreadPoolExecutor.CallerRunsPolicy()
);
```

## 7. ThreadLocal

Each thread gets its own copy of the variable — no synchronization needed.

```java
ThreadLocal<SimpleDateFormat> dateFormat =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

// Each thread has independent SimpleDateFormat instance
String date = dateFormat.get().format(new Date());
```

### How It Works Internally

```
Thread object
  └── ThreadLocalMap (custom HashMap, NOT java.util.HashMap)
        ├── Entry(ThreadLocal<?> key, Object value)
        │         ↑ WeakReference!
        ├── Entry(ThreadLocal<?> key, Object value)
        └── ...

threadLocal.get():
  1. Get current thread
  2. Get thread's ThreadLocalMap
  3. Look up entry by this ThreadLocal instance as key
  4. Return value
```

### Memory Leak Problem (CRITICAL for interviews)

```
Thread Pool Thread (long-lived, never dies)
  └── ThreadLocalMap
        └── Entry
              ├── key: WeakReference<ThreadLocal> ──► ThreadLocal instance
              │         ↓ (GC collects ThreadLocal if no strong ref)
              │         key becomes null!
              │
              └── value: Strong Reference ──► YOUR OBJECT (never collected!)
                         This is the LEAK

Timeline:
1. ThreadLocal variable goes out of scope → WeakReference key collected → key=null
2. But Entry still holds strong reference to value
3. Thread pool thread lives forever → ThreadLocalMap lives forever
4. Entry with null key and non-null value → value can never be accessed or removed
5. MEMORY LEAK!
```

**Fix**: always call `remove()` when done:

```java
ThreadLocal<UserContext> context = new ThreadLocal<>();

try {
    context.set(new UserContext(userId));
    // ... do work
} finally {
    context.remove();   // ALWAYS clean up, especially in thread pools
}
```

## 8. CompletableFuture (Java 8+)

### Basic Usage

```java
// Run async task
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    return fetchFromDB();   // runs in ForkJoinPool.commonPool()
});

// Chain transformations
CompletableFuture<Integer> result = future
    .thenApply(s -> s.length())              // sync transform
    .thenApplyAsync(len -> len * 2)          // async transform
    .exceptionally(ex -> -1);                // error handling

// Get result (blocking)
int value = result.get();                    // blocks until complete
int value = result.get(5, TimeUnit.SECONDS); // with timeout
```

### Composition Patterns

```java
// Combine two independent futures
CompletableFuture<String> nameF = CompletableFuture.supplyAsync(() -> getName());
CompletableFuture<Integer> ageF = CompletableFuture.supplyAsync(() -> getAge());

// Wait for both
CompletableFuture<String> combined = nameF.thenCombine(ageF,
    (name, age) -> name + " is " + age);

// Wait for first completed
CompletableFuture<String> fastest = CompletableFuture.anyOf(future1, future2, future3)
    .thenApply(obj -> (String) obj);

// Wait for all completed
CompletableFuture<Void> all = CompletableFuture.allOf(future1, future2, future3);
all.thenRun(() -> {
    // all futures complete
    String r1 = future1.join();
    String r2 = future2.join();
});
```

### Async vs Sync Methods

```java
// thenApply:      same thread (or caller thread if already complete)
// thenApplyAsync: ForkJoinPool.commonPool() (different thread)
// thenApplyAsync(fn, executor): specified executor

future.thenApply(s -> transform(s));                    // may run in completing thread
future.thenApplyAsync(s -> transform(s));               // always in pool thread
future.thenApplyAsync(s -> transform(s), myExecutor);   // always in myExecutor
```

### Error Handling

```java
CompletableFuture<String> result = supplyAsync(() -> riskyOperation())
    .exceptionally(ex -> "fallback")           // recover from error
    .handle((val, ex) -> {                      // handle both success and error
        if (ex != null) return "error: " + ex.getMessage();
        return "success: " + val;
    })
    .whenComplete((val, ex) -> {                // side effect, doesn't change value
        if (ex != null) log.error("Failed", ex);
    });
```

## 9. Common Concurrency Utilities

### CountDownLatch — Wait for N Events

```java
CountDownLatch latch = new CountDownLatch(3);  // count = 3

// Worker threads
executor.submit(() -> { doWork(); latch.countDown(); }); // count → 2
executor.submit(() -> { doWork(); latch.countDown(); }); // count → 1
executor.submit(() -> { doWork(); latch.countDown(); }); // count → 0

latch.await();  // blocks until count reaches 0
// All 3 workers done, proceed

// Note: CountDownLatch is ONE-TIME — cannot reset count
```

### CyclicBarrier — Wait for Each Other

```java
CyclicBarrier barrier = new CyclicBarrier(3, () -> {
    System.out.println("All 3 arrived, merging results");  // barrier action
});

// Each of 3 threads:
doPhase1();
barrier.await();  // wait until all 3 reach here
doPhase2();
barrier.await();  // reusable! wait again for phase 2 completion
doPhase3();
```

| | CountDownLatch | CyclicBarrier |
|---|---|---|
| Reusable? | No (one-shot) | Yes (cyclic) |
| Who waits? | One thread waits for N events | N threads wait for each other |
| Reset? | No | Yes (auto-reset or `reset()`) |
| Use case | Main waits for workers | Phased parallel computation |

### Semaphore — Rate Limiting / Resource Pool

```java
Semaphore semaphore = new Semaphore(10);  // 10 permits

semaphore.acquire();   // take permit (block if none available)
try {
    accessLimitedResource();
} finally {
    semaphore.release();   // return permit
}

// tryAcquire for non-blocking
if (semaphore.tryAcquire(1, TimeUnit.SECONDS)) {
    try { /* ... */ } finally { semaphore.release(); }
} else {
    // timed out, handle rejection
}
```

## 10. Concurrency Pitfalls Cheat Sheet

| Pitfall | Cause | Fix |
|---------|-------|-----|
| **Deadlock** | Circular lock acquisition | Lock ordering, tryLock with timeout |
| **Livelock** | Threads keep retrying, no progress | Backoff with jitter |
| **Starvation** | Unfair lock, low-priority thread never scheduled | Fair locks, avoid priority inversion |
| **False sharing** | Two threads write adjacent cache line fields | `@Contended` padding (JDK internal), separate into different objects |
| **ThreadLocal leak** | Thread pool + no remove() | Always `remove()` in finally |
| **volatile not enough** | Compound operations (check-then-act) | Use Atomic* or synchronized |
| **notify vs notifyAll** | notify wakes wrong thread | Prefer notifyAll (or Condition) |
