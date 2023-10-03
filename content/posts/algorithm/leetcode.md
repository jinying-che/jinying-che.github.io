---
title: "Algorithm: How I leetcode"
date: 2021-02-13T16:31:28+08:00
tags: ["algorithm", "data structure"]
description: "leetcode checklist for the algorithm interview"
---

When do you play with [leetcode](https://leetcode.com/)? Personally, I open it only before the algorithm interview.

It's wrong actually, the algorithm is not only used in the interview but also really useful in the production, which also make you write the effective code in the daily work. Leetcode helps interview a lot indeed, I sometimes can see some guys who get the Google offer by leetcode, moreover, I believe more algorithm we learned, better engineer we can be.

This post is showing how I leetcode, it's only my personal approach, I usually try to understand the one algorithm completely, then try to search by tag and resolve the problems from easy to hard.

The general steps to resovle a problem:
1. **Abstract the problem**: Most questions are from some scenario in the real world, try to abstract the problem, transfer the problem to the computer world.
2. **Map to the data structure and algorithm**: Do a brainstorm, map the problem to any data structur and algorithm that you are familiar with. If lucky it's exactly matched, apply it. 
    1. Don't try to use smartest solution first, it's probably time consuming, for example, maybe Brute Force at first then optimize it step by step.
    2. No any clue? congratulations! you get space to grow, don't be too sad for the failure of one interview, the better future is waiting for you ahead.
3. **Implemente the solution**: there's a gap between the idea and the code, no magic here, practice more to improve the code skills.

Enjoy the Algorithm, let's leetcode!

### Data Structure
#### Array
- [41. First Missing Positive](https://leetcode.com/problems/first-missing-positive/) -- [[discussion](https://leetcode.com/problems/first-missing-positive/discuss/1076050/Golang41one-general-way-on-geek-way)]
#### Linked List
- [206. Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/) -- [[discussion](https://leetcode.com/problems/reverse-linked-list/discuss/1057045/golang206recursion-is-beautiful)]
#### Tree 
- [226. Invert Binary Tree](https://leetcode.com/problems/invert-binary-tree/)
- [104. maximum-depth-of-binary-tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/)

---
> The solutions for following three problems are similiar, which all base on the inorder traversal with stack
>
> [Discussion - Learn one iterative inorder traversal, apply it to multiple tree questions (Java Solution)](https://leetcode.com/problems/validate-binary-search-tree/discuss/32112/Learn-one-iterative-inorder-traversal-apply-it-to-multiple-tree-questions-(Java-Solution))
- [94. Binary Tree Inorder Traversal](https://leetcode.com/problems/binary-tree-inorder-traversal/)
- [98. Validate Binary Search Tree](https://leetcode.com/problems/validate-binary-search-tree/)
- [230. Kth Smallest Element in a BST](https://leetcode.com/problems/kth-smallest-element-in-a-bst/)
---

#### Heap
- [347. Top K Frequent Elements](https://leetcode.com/problems/top-k-frequent-elements/) -- [[disscussion: Implement the Min Heap on my own](https://leetcode.com/problems/top-k-frequent-elements/discuss/1108972/Golang347-Implement-the-Min-Heap-on-my-own)]

#### Binary 
To master binary related problems, understanding the binary operation is the key point: `^`, `|`, `&`, `>>` and `<<`
- [461. Hamming Distance](https://leetcode.com/problems/hamming-distance/description/)

#### Stack
- [20. Valid Parentheses](https://leetcode.com/problems/valid-parentheses/description/)

### Algorithm
#### Recursion
- [206. Reverse Linked List](https://leetcode.com/problems/reverse-linked-list/) -- [[discussion](https://leetcode.com/problems/reverse-linked-list/discuss/1057045/golang206recursion-is-beautiful)]
- [509. Fibonacci Number](https://leetcode.com/problems/fibonacci-number/) -- [[discussion](https://leetcode.com/problems/fibonacci-number/discuss/1057880/golang509four-ways-to-resolve-fibonacci-number)]
#### Dynamic Programming
- [509. Fibonacci Number](https://leetcode.com/problems/fibonacci-number/) -- [[discussion](https://leetcode.com/problems/fibonacci-number/discuss/1057880/golang509four-ways-to-resolve-fibonacci-number)]
- [70. Climbing Stairs](https://leetcode.com/problems/climbing-stairs/)

#### Binary Search
- [704. Binary Search](https://leetcode.com/problems/binary-search/) -- [[discussion](https://leetcode.com/problems/binary-search/discuss/1055849/golang704beautiful-code-of-binary-search)]
- [34. Find First and Last Position of Element in Sorted Array](https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/) -- [[discussion](https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/discuss/1056313/golang34easy-way-to-understand-with-two-binary-search)]

#### Quick Sort
- [215. Kth Largest Element in an Array](https://leetcode.com/problems/kth-largest-element-in-an-array/) -- [[discussion: two partition schema]](https://leetcode.com/problems/kth-largest-element-in-an-array/discuss/1108891/Golang215two-partition-schema-of-quick-select)
- [347. Top K Frequent Elements](https://leetcode.com/submissions/detail/465797355/)

#### Greedy
- [763. Partition Labels](https://leetcode.com/problems/partition-labels/)
- [1353. Maximum Number of Events That Can Be Attended](https://leetcode.com/problems/maximum-number-of-events-that-can-be-attended/) -- [[solution]](https://leetcode.com/problems/maximum-number-of-events-that-can-be-attended/solutions/4066650/1353-python-maximum-number-of-events-that-can-be-attended)

#### Math
- [204. Count Primes](https://leetcode.com/problems/count-primes/description/) -- [Sieve of Eratosthenes](https://en.wikipedia.org/wiki/Sieve_of_Eratosthenes) [https://en.oi-wiki.org/math/sieve/]

### Design
- [146. LRU Cache](https://leetcode.com/problems/lru-cache/) -- [[discussion](https://leetcode.com/problems/lru-cache/solutions/4113594/python-146-lru-cache/)]
- [460. LFU Cache](https://leetcode.com/problems/lfu-cache/) -- [[discussion](https://leetcode.com/problems/lfu-cache/discuss/1086255/Golang460two-ways-to-resolve-LFU-Cache)]
