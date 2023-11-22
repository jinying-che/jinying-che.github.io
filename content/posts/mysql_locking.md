---
title: "MySQL Locking"
date: "2023-11-22T10:35:54+08:00"
tags: ["mysql"]
description: "MySQL Locking Overview"
draft: true
---

## Shared and Exclusive Locks

## Intention Locks

## Record Locks
Record locks always lock index records, even if a table is defined with no indexes. For such cases, InnoDB creates a hidden clustered index and uses this index for record locking.

## Gap Locks

Gap locks can co-exist. A gap lock taken by one transaction does not prevent another transaction from taking a gap lock on the same gap. There is no difference between shared and exclusive gap locks. They do not conflict with each other, and they perform the same function.

## Next-Key Locks
By default, InnoDB operates in REPEATABLE READ transaction isolation level. In this case, InnoDB uses next-key locks for searches and index scans, which prevents phantom rows.

## Insert Intention Locks
