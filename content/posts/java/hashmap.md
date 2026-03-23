---
title: "HashMap Internals"
date: 2026-03-19T00:00:00+08:00
description: "Deep dive into HashMap — hash function, put/resize mechanics, treeify, and ConcurrentHashMap"
tags: ["java"]
draft: true
---

# HashMap Internals (Java 8+)

## 1. Structure

```
HashMap<K,V>

table: Node<K,V>[]   (default initial capacity = 16, load factor = 0.75)

Index:   0     1     2     3     4     5     6     7    ... 15
       ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
       │null │  ●  │null │  ●  │null │null │  ●  │null │
       └─────┴──┬──┴─────┴──┬──┴─────┴─────┴──┬──┴─────┘
                │           │                 │
                ▼           ▼                 ▼
             [K1,V1]     [K3,V3]          [K5,V5]
                │           │                 │
                ▼           ▼                 ▼
             [K2,V2]     [K4,V4]          [K6,V6]
                            │                 │
                            ▼                 ▼
                         [K7,V7]          [K8,V8]
                                              │
                     (if chain > 8 &&         ▼
                      capacity >= 64)    ┌─ Red-Black Tree ─┐
                                         │  O(log n) lookup │
                                         └──────────────────┘
```

## 2. Hash Function — Why `h ^ (h >>> 16)`

```java
static final int hash(Object key) {
    int h;
    return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
}
```

```
Original hashCode:    1111 1111 1010 0011 | 0000 0000 0000 0101
h >>> 16:             0000 0000 0000 0000 | 1111 1111 1010 0011
XOR result:           1111 1111 1010 0011 | 1111 1111 1010 0110
                                            ^^^^^^^^^^^^^^^^^^^^^^^^
                      high bits mixed into low bits

index = hash & (capacity - 1)
      = hash & 0xF              (for capacity=16)
      = only uses lowest 4 bits!

Without perturbation: different keys whose low bits are same → same bucket → more collisions
With perturbation:    high bits influence low bits → better distribution
```

## 3. put() — Complete Flow

```java
// Simplified logic
final V putVal(int hash, K key, V value) {
    // 1. Table not initialized? → resize() to create initial table
    if (table == null || table.length == 0)
        table = resize();

    // 2. Calculate index, check if bucket is empty
    int index = hash & (table.length - 1);
    if (table[index] == null) {
        table[index] = new Node<>(hash, key, value, null);  // insert directly
    } else {
        Node<K,V> node = table[index];

        // 3. First node matches key? → update
        if (node.hash == hash && (node.key == key || key.equals(node.key))) {
            // update existing
        }
        // 4. Is it a TreeNode? → tree insertion
        else if (node instanceof TreeNode) {
            ((TreeNode<K,V>)node).putTreeVal(hash, key, value);
        }
        // 5. Linked list → traverse to end
        else {
            for (int binCount = 0; ; ++binCount) {
                if (node.next == null) {
                    node.next = new Node<>(hash, key, value, null); // tail insertion (Java 8!)
                    if (binCount >= 7)   // 7 means 8 nodes total → treeify
                        treeifyBin(table, hash);
                    break;
                }
                if (node.next matches key) { /* update */ break; }
                node = node.next;
            }
        }
    }

    // 6. Check if resize needed
    if (++size > threshold)  // threshold = capacity * loadFactor
        resize();
}
```

## 4. Resize — How It Works

```
Old table (capacity=8):

Index:  0    1    2    3    4    5    6    7
      [  ] [A ] [  ] [B ] [  ] [C ] [  ] [D ]
            │         │         │
            ▼         ▼         ▼
           [E ]      [F ]      [G ]

New table (capacity=16):

For each node, check: (hash & oldCap) == 0 ?
  - Yes → stays at same index
  - No  → moves to index + oldCap

Example: oldCap = 8 (binary 1000)
  hash of A = ...0001  →  0001 & 1000 = 0  → stays at index 1
  hash of E = ...1001  →  1001 & 1000 = 1  → moves to index 1+8 = 9

Index:  0    1    2    3    4    5    6    7    8    9    10 ...
      [  ] [A ] [  ] [B ] [  ] [C ] [  ] [D ] [  ] [E ] [  ] ...
```

**Why this works**: when capacity doubles, each node's index either stays the same or increases by `oldCap`. The determining bit is exactly the bit at `oldCap` position. This is more efficient than recalculating every hash.

## 5. Java 7 vs Java 8 Differences

| Aspect | Java 7 | Java 8 |
|--------|--------|--------|
| Collision handling | Linked list only | Linked list + Red-Black Tree |
| Insertion | Head insertion | Tail insertion |
| Resize | Transfer with head insertion | Check high bit, no reorder |
| Concurrency bug | Infinite loop (head insertion creates cycle during resize) | Data loss possible, but no infinite loop |
| Treeify threshold | N/A | chain > 8 && capacity >= 64 |
| Untreeify | N/A | tree size < 6 → back to linked list |

### Java 7 Infinite Loop — How It Happens

```
Original (capacity=2):   bucket[1]: A → B → null

Thread 1 starts resize, reads A.next = B
Thread 1 suspends...

Thread 2 completes resize (head insertion reverses order):
  bucket[1]: B → A → null

Thread 1 resumes, still thinks A.next = B:
  Inserts A at head: A → ...
  Then processes B, B.next = A (from Thread 2's resize)
  Inserts B at head: B → A → B → A → ...  ← INFINITE LOOP!

Java 8 fix: tail insertion preserves original order, no reversal → no cycle
```

## 6. Why NOT Thread-Safe? → Use ConcurrentHashMap

```java
// Thread A: put("key1", val)        // Thread B: put("key2", val)
// Both hash to same bucket, bucket is currently null

// Thread A: checks table[i] == null  ✓
// Thread B: checks table[i] == null  ✓  (context switch)
// Thread A: table[i] = new Node(key1)
// Thread B: table[i] = new Node(key2)  // overwrites Thread A's node!

// Result: key1's entry is LOST
```

### ConcurrentHashMap — Java 7 vs Java 8

**Java 7: Segment locking**

```
ConcurrentHashMap (16 segments by default)
┌──────────┬──────────┬──────────┬──────────┐
│ Segment0 │ Segment1 │ Segment2 │ ...      │
│ (Lock)   │ (Lock)   │ (Lock)   │          │
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │          │
│ │table │ │ │table │ │ │table │ │          │
│ └──────┘ │ └──────┘ │ └──────┘ │          │
└──────────┴──────────┴──────────┴──────────┘

- Each Segment extends ReentrantLock
- Concurrent writes to DIFFERENT segments = no contention
- Concurrent writes to SAME segment = blocked
- Concurrency level = number of segments (default 16)
```

**Java 8: CAS + per-bucket synchronized**

```java
// ConcurrentHashMap.putVal simplified:
if (table[i] == null) {
    // CAS to insert — no lock needed for empty bucket
    casTabAt(table, i, null, new Node<>(hash, key, value));
} else {
    synchronized (table[i]) {  // lock ONLY this bucket's head node
        // ... traverse and insert/update
    }
}
```

| Aspect | Java 7 ConcurrentHashMap | Java 8 ConcurrentHashMap |
|--------|-------------------------|-------------------------|
| Lock granularity | Per-segment (16 by default) | Per-bucket (much finer) |
| Lock type | ReentrantLock | CAS + synchronized |
| Data structure | Segment → HashEntry[] | Node[] (same as HashMap) |
| Tree support | No | Yes (same treeify as HashMap) |
| size() | Sum segments (may be inaccurate) | baseCount + CounterCell[] (LongAdder-like) |

### ConcurrentHashMap.size() — How It Works (Java 8)

```java
// Naive approach: single AtomicLong → hot contention on every put/remove
// ConcurrentHashMap solution: distributed counting (like LongAdder)

// baseCount: updated via CAS if no contention
// counterCells[]: array of counters, each thread picks one (hash-based)
// size() = baseCount + sum(counterCells)

// On put():
//   1. Try CAS on baseCount
//   2. If CAS fails (contention) → pick a counterCell and CAS that instead
//   3. If counterCell CAS also fails → expand counterCells array
```
