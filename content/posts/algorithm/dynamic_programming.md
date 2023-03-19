---
title: "Dynamic Programming"
date: "2023-03-11T23:03:37+08:00"
tags: ["algorithm"]
description: "Dynamic Programming is simplifying a complicated problem by breaking it down into simpler sub-problems in a recursive manner"
---
Dynamic Programming is mainly an optimization over plain recursion. Wherever we see a recursive solution that has repeated calls for the same inputs, we can optimize it using Dynamic Programming. The idea is to simply store the results of subproblems so that we do not have to re-compute them when needed later. This simple optimization reduces time complexities from exponential to polynomial

## Two Key Attributes
How to classify a problem as a Dynamic Programming algorithm Problem?
#### 1. Overlapping Subproblems
The solutions to the same subproblems are needed repetitively for solving the actual problem.

#### 2. Optimal Substructure Property
The solution to a given optimization problem can be obtained by the combination of optimal solutions to its sub-problems. Such optimal substructures are usually described by means of recursion.

> If a problem can be solved by combining optimal solutions to non-overlapping sub-problems, the strategy is called "divide and conquer" instead. This is why merge sort and quick sort are not classified as dynamic programming problems.

## The Steps To Resove The A Dynamic Programming Problem

#### 1. Identify a **DP** problem, Identify the **subproblems**
refer to two key attributes 
#### 2. Decide a state expression with the Least parameters
Determine what information you need to represent the solution to each subproblem. This is often done using a state vector or matrix.
#### 3. Formulate state and transition relationships 
Determine the relationship between the solution to a subproblem and the solutions to its smaller subproblems. This is often done using a recursive formula or a set of rules.
#### 4. Adding memoization or tabulation for the state
Simply storing the state solution will allow us to access it from memory the next time that state is needed. Solve the subproblems in a bottom-up (tabulation) or top-down (memorization) manner. 
#### 5. Compute the final solution using the solutions to the subproblems.

TODO: Example

## nmemoization vs tabulation (TODO)
