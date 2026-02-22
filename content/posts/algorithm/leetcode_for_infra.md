---
title: "Leetcode Category in Infrastructure"
date: "2026-02-22T17:40:02+08:00"
tags: ["algorithm", "leetcode"]
description: "As an infrastructure engineer, let's go through the most important algorithm and data structure used in infrastructure world"
---

# Classical Data Structures
| Data Structure | Title & Question Number | Key Concept / Focus |
| :--- | :--- | :--- |
| **Hash Table** | [#146 LRU Cache](https://leetcode.com/problems/lru-cache/) | **Infra Essential:** HashMaps + Doubly Linked Lists for O(1) access/eviction. |
| **Hash Table** | [#460 LFU Cache](https://leetcode.com/problems/lfu-cache/) | Advanced eviction policy; frequency-based tracking with nested HashMaps. |
| **Array** | [#1 Two Sum](https://leetcode.com/problems/two-sum/) | The foundation of frequency mapping and index lookups. |
| **Array** | [#238 Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/) | Prefix/suffix products without division; common in metric normalization. |
| **String** | [#3 Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/) | Mastering the **Sliding Window** pattern. |
| **String** | [#49 Group Anagrams](https://leetcode.com/problems/group-anagrams/) | Hashing and grouping; applicable to log deduplication and fingerprinting. |
| **Linked List** | [#206 Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/) | Core pointer manipulation and iterative/recursive logic. |
| **Linked List** | [#23 Merge K Sorted Lists](https://leetcode.com/problems/merge-k-sorted-lists/) | Heap-based merging; mirrors merging sorted log streams from multiple sources. |
| **Stack** | [#20 Valid Parentheses](https://leetcode.com/problems/valid-parentheses/) | Linear parsing and LIFO (Last-In-First-Out) logic. |
| **Stack** | [#84 Largest Rectangle in Histogram](https://leetcode.com/problems/largest-rectangle-in-histogram/) | Monotonic stack; useful for capacity planning and resource window analysis. |
| **Queue** | [#239 Sliding Window Maximum](https://leetcode.com/problems/sliding-window-maximum/) | Monotonic Queue for optimized window processing. |
| **Queue** | [#933 Number of Recent Calls](https://leetcode.com/problems/number-of-recent-calls/) | Rate limiting simulation; directly models request throttling logic. |
| **Tree** | [#102 Binary Tree Level Order Traversal](https://leetcode.com/problems/binary-tree-level-order-traversal/) | The "Hello World" of **Breadth-First Search (BFS)**. |
| **Tree** | [#236 Lowest Common Ancestor of a Binary Tree](https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/) | Recursive tree traversal; models namespace/path hierarchy resolution. |
| **BST** | [#98 Validate Binary Search Tree](https://leetcode.com/problems/validate-binary-search-tree/) | Understanding recursion boundaries and tree properties. |
| **BST** | [#230 Kth Smallest Element in a BST](https://leetcode.com/problems/kth-smallest-element-in-a-bst/) | In-order traversal; useful for percentile queries on ordered metrics. |
| **Heap** | [#215 Kth Largest Element in an Array](https://leetcode.com/problems/kth-largest-element-in-an-array/) | Efficiently managing "Top K" streaming data or task priority. |
| **Heap** | [#295 Find Median from Data Stream](https://leetcode.com/problems/find-median-from-data-stream/) | Dual-heap pattern; real-time percentile tracking (p50/p99 latency). |
| **Graph** | [#200 Number of Islands](https://leetcode.com/problems/number-of-islands/) | Matrix traversal using **DFS/BFS**; the most common graph prompt. |
| **Graph** | [#133 Clone Graph](https://leetcode.com/problems/clone-graph/) | BFS/DFS with memoization; models deep-copying distributed config graphs. |
| **Trie** | [#208 Implement Trie (Prefix Tree)](https://leetcode.com/problems/implement-trie-prefix-tree/) | Efficient string prefix storage and autocomplete logic. |
| **Trie** | [#212 Word Search II](https://leetcode.com/problems/word-search-ii/) | Trie + DFS backtracking; models multi-pattern log/path matching. |
| **Union-Find** | [#547 Number of Provinces](https://leetcode.com/problems/number-of-provinces/) | **Infra Essential:** Models network partition detection and cluster connectivity. |
| **Union-Find** | [#684 Redundant Connection](https://leetcode.com/problems/redundant-connection/) | Cycle detection in graphs; identifies redundant links in network topology. |

# Classical Algorithms
| Algorithm Category | Title & Question Number | Real-World Context (Infra/SRE) |
| :--- | :--- | :--- |
| **Binary Search** | [#33 Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/) | Searching through partitioned or sharded sorted data sets. |
| **Binary Search** | [#153 Find Minimum in Rotated Sorted Array](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/) | Efficiently locating boundaries in rotated/partitioned data. |
| **BFS (Graph)** | [#127 Word Ladder](https://leetcode.com/problems/word-ladder/) | Finding the shortest path in an unweighted state-space/network. |
| **BFS (Graph)** | [#994 Rotting Oranges](https://leetcode.com/problems/rotting-oranges/) | Multi-source BFS; models failure/alert propagation across a network. |
| **DFS (Graph)** | [#207 Course Schedule](https://leetcode.com/problems/course-schedule/) | **Topological Sort:** Resolving service or package dependencies. |
| **DFS (Graph)** | [#399 Evaluate Division](https://leetcode.com/problems/evaluate-division/) | Weighted graph traversal; models unit conversion chains and metric ratios. |
| **Dijkstra** | [#743 Network Delay Time](https://leetcode.com/problems/network-delay-time/) | Directly mirrors network packet routing and latency calculations. |
| **Dijkstra** | [#787 Cheapest Flights Within K Stops](https://leetcode.com/problems/cheapest-flights-within-k-stops/) | Constrained shortest path; models cost-aware routing with hop limits. |
| **Two Pointers** | [#15 3Sum](https://leetcode.com/problems/3sum/) | Optimizing multi-variable searches from O(n³) to O(n²). |
| **Two Pointers** | [#11 Container With Most Water](https://leetcode.com/problems/container-with-most-water/) | Greedy boundary shrinking; models capacity optimization problems. |
| **Sliding Window** | [#76 Minimum Window Substring](https://leetcode.com/problems/minimum-window-substring/) | Extracting specific patterns from high-velocity log streams. |
| **Sliding Window** | [#438 Find All Anagrams in a String](https://leetcode.com/problems/find-all-anagrams-in-a-string/) | Fixed-size window pattern matching; applicable to network signature detection. |
| **Backtracking** | [#46 Permutations](https://leetcode.com/problems/permutations/) | Exhaustive state-space search (e.g., finding all possible config combinations). |
| **Backtracking** | [#79 Word Search](https://leetcode.com/problems/word-search/) | DFS + backtracking on a grid; models path finding in topology graphs. |
| **Greedy** | [#435 Non-overlapping Intervals](https://leetcode.com/problems/non-overlapping-intervals/) | **Infra Essential:** Scheduling maintenance windows and minimizing overlapping deploys. |
| **Greedy** | [#55 Jump Game](https://leetcode.com/problems/jump-game/) | Local decision-making to reach a global destination efficiently. |
| **DP (1D)** | [#322 Coin Change](https://leetcode.com/problems/coin-change/) | Optimization problems like fitting tasks into fixed-size nodes. |
| **DP (1D)** | [#300 Longest Increasing Subsequence](https://leetcode.com/problems/longest-increasing-subsequence/) | Modeling monotonically growing metrics; version ordering. |
| **DP (2D)** | [#1143 Longest Common Subsequence](https://leetcode.com/problems/longest-common-subsequence/) | Underlying logic for `diff` tools and version control comparisons. |
| **DP (2D)** | [#72 Edit Distance](https://leetcode.com/problems/edit-distance/) | Minimum edit operations; powers fuzzy log matching and config drift detection. |
| **Bit Manipulation** | [#191 Number of 1 Bits](https://leetcode.com/problems/number-of-1-bits/) | Low-level performance tuning and flag-based state management. |
| **Bit Manipulation** | [#136 Single Number](https://leetcode.com/problems/single-number/) | XOR-based deduplication; detecting unique anomalies in paired datasets. |
