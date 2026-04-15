---
title: "Heap"
date: "2026-04-14T10:27:23+0800"
tags: ["algorithm"]
description: "binary heap: structure, operations, and applications"
draft: true
---

## What Is a Heap?

A **heap** is a complete binary tree that satisfies the **heap property**:

| Type | Property |
|---|---|
| Min-Heap | Every parent ≤ its children (root = minimum) |
| Max-Heap | Every parent ≥ its children (root = maximum) |

**Complete binary tree**: every level is fully filled except possibly the last, which is filled left-to-right.

```text
       Min-Heap                    Max-Heap

          1                          9
        /   \                      /   \
       3     5                    7     8
      / \   /                   / \   /
     4   8 7                   3   6 5
```

> This post uses **min-heap** throughout. Max-heap is symmetric — just flip the comparisons.

## Array Representation

A complete binary tree maps perfectly to a **0-indexed array** with no wasted space:

```text
  Tree:          1
               /   \
              3     5
             / \   /
            4   8 7

  Array:  [ 1 | 3 | 5 | 4 | 8 | 7 ]
  Index:    0   1   2   3   4   5
```

Navigation by index:

| Relation | Formula |
|---|---|
| Parent of `i` | `(i - 1) / 2` |
| Left child of `i` | `2*i + 1` |
| Right child of `i` | `2*i + 2` |

Example: node at index 1 (value 3) → parent = `(1-1)/2 = 0` (value 1), left child = `2*1+1 = 3` (value 4), right child = `2*1+2 = 4` (value 8).

## Core Operations

### Sift-Up (bubble up)

Move a node **up** toward the root while it violates the heap property (child < parent in a min-heap). Used after **insert**.

```text
Insert 2 into:  [ 1, 3, 5, 4, 8, 7 ]

Step 1: append 2 at index 6
  [ 1, 3, 5, 4, 8, 7, 2 ]
                         ^

Step 2: compare with parent (index 2, value 5) → 2 < 5, swap
  [ 1, 3, 2, 4, 8, 7, 5 ]
            ^           ^

Step 3: compare with parent (index 0, value 1) → 2 > 1, stop
  [ 1, 3, 2, 4, 8, 7, 5 ]   ✓ valid min-heap

  Tree:          1
               /   \
              3     2
             / \   / \
            4   8 7   5
```

### Sift-Down (bubble down)

Move a node **down** away from the root while it violates the heap property. Used after **extract** and during **build-heap**.

```text
Extract min from:  [ 1, 3, 2, 4, 8, 7, 5 ]

Step 1: swap root with last element, remove last
  [ 5, 3, 2, 4, 8, 7 | 1 ]  ← 1 extracted
    ^

Step 2: sift-down index 0 (value 5)
  children: left=3, right=2 → smallest child = 2 (index 2)
  5 > 2, swap
  [ 2, 3, 5, 4, 8, 7 ]
            ^

Step 3: sift-down index 2 (value 5)
  children: left=7, right=none → smallest child = 7
  5 < 7, stop
  [ 2, 3, 5, 4, 8, 7 ]   ✓ valid min-heap

  Tree:          2
               /   \
              3     5
             / \   /
            4   8 7
```

## Build Heap — Floyd's Algorithm

Given an unsorted array, build a valid heap.

**Naive approach**: insert elements one by one → O(n log n).

**Floyd's approach**: start from the **last non-leaf node** and sift-down each node bottom-up → **O(n)**.

```text
Input: [ 7, 3, 8, 1, 5, 2, 4 ]

  Tree (unordered):
           7
         /   \
        3     8
       / \   / \
      1   5 2   4

Last non-leaf = index (7/2 - 1) = 2 (value 8)

Step 1: sift-down index 2 (value 8)
  smallest child = 2 → swap
  [ 7, 3, 2, 1, 5, 8, 4 ]

Step 2: sift-down index 1 (value 3)
  smallest child = 1 → swap
  [ 7, 1, 2, 3, 5, 8, 4 ]

Step 3: sift-down index 0 (value 7)
  smallest child = 1 → swap
  [ 1, 7, 2, 3, 5, 8, 4 ]
  sift-down continues: index 1 (value 7)
  smallest child = 3 → swap
  [ 1, 3, 2, 7, 5, 8, 4 ]

  Result:        1
               /   \
              3     2
             / \   / \
            7   5 8   4   ✓ valid min-heap
```

### Why O(n), not O(n log n)?

Each node sifts down at most `h` levels where `h` is its height from the bottom. Most nodes are near the bottom and barely move.

```text
Height h    # nodes at height h    sift-down cost
──────────────────────────────────────────────────
  0 (leaves)    n/2                  0
  1             n/4                  1
  2             n/8                  2
  ...           ...                  ...
  log n         1                    log n
```

Total work:

```text
T(n) = Σ (n / 2^(h+1)) × h   for h = 0 to log n
     = n × Σ h / 2^(h+1)
     = n × (1/4 + 2/8 + 3/16 + ...)

The series Σ h/2^(h+1) converges to 1 (constant).

∴ T(n) = O(n)
```

The key insight: half the nodes are leaves (0 work), a quarter sift 1 level, an eighth sift 2 levels... the work is dominated by the many cheap nodes, not the few expensive ones.

## Insert & Extract

| Operation | Steps | Time |
|---|---|---|
| **Insert** | Append to end → sift-up | O(log n) |
| **Extract-min** | Swap root with last → remove last → sift-down root | O(log n) |
| **Peek** | Return root | O(1) |

## Heap Sort

Sort an array in-place using a max-heap:

```text
Input: [4, 1, 7, 3, 8, 5]

Phase 1: Build max-heap → [8, 4, 7, 3, 1, 5]

Phase 2: Repeatedly extract max
  swap root ↔ last unsorted, sift-down root

  [5, 4, 7, 3, 1 | 8]  → sift-down → [7, 4, 5, 3, 1 | 8]
  [1, 4, 5, 3 | 7, 8]  → sift-down → [5, 4, 1, 3 | 7, 8]
  [3, 4, 1 | 5, 7, 8]  → sift-down → [4, 3, 1 | 5, 7, 8]
  [1, 3 | 4, 5, 7, 8]  → sift-down → [3, 1 | 4, 5, 7, 8]
  [1 | 3, 4, 5, 7, 8]  → done

  Result: [1, 3, 4, 5, 7, 8]   ✓ sorted ascending
```

| Property | Value |
|---|---|
| Time | O(n log n) — build O(n) + n extractions × O(log n) |
| Space | O(1) — in-place |
| Stable? | No |

## Applications

| Use Case | How Heap Helps |
|---|---|
| Priority Queue | Insert/extract-min in O(log n) |
| Top-K elements | Min-heap of size K: push element, pop if size > K → O(n log K) |
| Merge K sorted lists | Min-heap of K heads, repeatedly extract-min and push next → O(N log K) |
| Running median | Max-heap (lower half) + min-heap (upper half), balance sizes |
| Task scheduling | Jobs ordered by deadline/priority |
| Dijkstra's algorithm | Extract closest unvisited node in O(log V) |

## Go Implementation

Implement from scratch — no `container/heap`:

```go
package main

import "fmt"

type MinHeap struct {
	data []int
}

func (h *MinHeap) siftUp(i int) {
	for i > 0 {
		parent := (i - 1) / 2
		if h.data[i] >= h.data[parent] {
			break
		}
		h.data[i], h.data[parent] = h.data[parent], h.data[i]
		i = parent
	}
}

func (h *MinHeap) siftDown(i int) {
	n := len(h.data)
	for {
		smallest := i
		left, right := 2*i+1, 2*i+2
		if left < n && h.data[left] < h.data[smallest] {
			smallest = left
		}
		if right < n && h.data[right] < h.data[smallest] {
			smallest = right
		}
		if smallest == i {
			break
		}
		h.data[i], h.data[smallest] = h.data[smallest], h.data[i]
		i = smallest
	}
}

// Floyd's build-heap: O(n)
func NewMinHeap(arr []int) *MinHeap {
	h := &MinHeap{data: arr}
	for i := len(arr)/2 - 1; i >= 0; i-- {
		h.siftDown(i)
	}
	return h
}

func (h *MinHeap) Push(val int) {
	h.data = append(h.data, val)
	h.siftUp(len(h.data) - 1)
}

func (h *MinHeap) Pop() int {
	n := len(h.data)
	min := h.data[0]
	h.data[0] = h.data[n-1]
	h.data = h.data[:n-1]
	if len(h.data) > 0 {
		h.siftDown(0)
	}
	return min
}

func (h *MinHeap) Peek() int { return h.data[0] }
func (h *MinHeap) Len() int  { return len(h.data) }

func main() {
	h := NewMinHeap([]int{7, 3, 8, 1, 5})
	h.Push(2)
	fmt.Println("min:", h.Peek()) // 1
	for h.Len() > 0 {
		fmt.Print(h.Pop(), " ") // 1 2 3 5 7 8
	}
}
```

## Complexity Summary

| Operation | Time | Notes |
|---|---|---|
| Build heap | O(n) | Floyd's bottom-up sift-down |
| Insert | O(log n) | Append + sift-up |
| Extract-min/max | O(log n) | Swap root + sift-down |
| Peek min/max | O(1) | Return root |
| Heap sort | O(n log n) | Build + n extractions |
| Search | O(n) | No ordering between siblings |
| Space | O(n) | Array storage, no pointers |

---

## References
- [Binary Heap — Wikipedia](https://en.wikipedia.org/wiki/Binary_heap)
- [Time Complexity of Building a Heap — GeeksforGeeks](https://www.geeksforgeeks.org/dsa/time-complexity-of-building-a-heap/)
