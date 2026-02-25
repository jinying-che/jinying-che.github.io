---
title: "Sliding Window Pattern"
date: "2026-02-25T11:11:26+08:00"
tags: ["algorithm", "sliding-window"]
description: "Sliding window pattern and template for LeetCode problems"
---

## The Pattern

```
1. Initialize window state
2. Expand right pointer (add element into window)
3. While window is invalid/valid → shrink left pointer (remove element from window)
4. Update answer (either during expand or shrink, depends on problem type)
```

## Two Types of Sliding Window

### Type 1: Find Minimum Window That Satisfies a Condition

Expand until valid, then shrink to minimize.

```python
for right in range(len(arr)):
    # add arr[right] to window

    while window_is_valid():      # shrink
        update_answer()           # answer during shrink
        # remove arr[left] from window
        left += 1
```

Examples: Minimum Window Substring (LC 76), Minimum Size Subarray Sum (LC 209)

### Type 2: Find Maximum Window That Satisfies a Condition

Expand as far as possible, shrink when invalid.

```python
for right in range(len(arr)):
    # add arr[right] to window

    while window_is_invalid():    # shrink
        # remove arr[left] from window
        left += 1

    update_answer()               # answer during expand
```

Examples: Longest Substring Without Repeating Characters (LC 3), Max Consecutive Ones III (LC 1004)

### The Key Difference
| | Min window | Max window |
|--|---|---|
| Shrink when | valid | invalid |
| Update answer | during shrink | after shrink (during expand) |
| You want | smallest valid window | largest valid window |

## What Changes Between Problems

The template stays the same. Only these parts change:

1. **What is the window state?** - a map, a count, a sum, a set
2. **What is the condition?** - sum >= target, all chars covered, no duplicates
3. **How to add/remove?** - increment/decrement count, add/remove from set

## Example Mapping
| Problem | State | Condition | Type |
|---|---|---|---|
| LC 76 (Min Window Substring) | char count map | all chars of t covered | Min |
| LC 3 (Longest No Repeat) | char set | no duplicates | Max |
| LC 209 (Min Size Subarray Sum) | running sum | sum >= target | Min |
| LC 1004 (Max Ones III) | zero count | zeros <= k | Max |
| LC 424 (Longest Repeating Replace) | char frequency | window - max_freq <= k | Max |
