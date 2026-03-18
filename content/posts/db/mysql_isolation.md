---
title: "MySQL Isolation Levels"
date: "2026-03-18T10:00:00+08:00"
tags: ["mysql"]
description: "Understanding 4 isolation levels with hands-on demos"
draft: true
---

## TL;DR

MySQL has 4 isolation levels that control what a transaction can "see" when other transactions are modifying data concurrently. From weakest to strongest:

| Level | What You See | Trade-off |
|---|---|---|
| READ UNCOMMITTED | Everything, even uncommitted changes | Fast, but dangerous |
| READ COMMITTED | Only committed data, refreshed per statement | No dirty reads, but same query can return different results |
| **REPEATABLE READ** (default) | Snapshot frozen at TX start | Consistent reads, slight overhead from gap locks |
| SERIALIZABLE | Locked reads, full blocking | Safest, but slowest |

This post walks through each level with **two-terminal demos** you can copy-paste and run. Open two `mysql` sessions and follow along — seeing the behavior yourself is much more effective than reading about it.

## Setup

```sql
CREATE TABLE t (
  id INT PRIMARY KEY,
  name VARCHAR(32),
  age INT
) ENGINE=InnoDB;

INSERT INTO t VALUES
  (1, 'Alice', 10),
  (5, 'Bob', 20),
  (10, 'Carol', 30),
  (15, 'Dave', 40);
```

## Three Anomalies

Each isolation level protects against increasingly subtle data inconsistency:

| Anomaly | What Happens | Example |
|---|---|---|
| Dirty Read | Read **uncommitted** data from another TX | TX A updates row but hasn't committed, TX B sees the uncommitted value |
| Non-Repeatable Read | Same row returns **different value** within one TX | TX B reads row twice, TX A commits an update in between |
| Phantom Read | Same range query returns **different row set** within one TX | TX B queries a range twice, TX A inserts a new row in between |

```
Dirty Read:             you see something that may never exist
Non-Repeatable Read:    you see the same row change value
Phantom Read:           you see new rows appear (or old rows disappear)
```

## Overview

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read |
|---|---|---|---|
| READ UNCOMMITTED | Yes | Yes | Yes |
| READ COMMITTED | No | Yes | Yes |
| **REPEATABLE READ** (default) | No | No | No (via gap locks) |
| SERIALIZABLE | No | No | No |

```sql
-- check current isolation level
SELECT @@transaction_isolation;

-- change for current session
SET SESSION transaction_isolation = 'READ-UNCOMMITTED';
```

## READ UNCOMMITTED

The weakest level. Can see **uncommitted** changes from other transactions.

### Demo: Dirty Read

```sql
SET SESSION transaction_isolation = 'READ-UNCOMMITTED';  -- both terminals

-- Terminal A                          -- Terminal B
BEGIN;                                 BEGIN;
UPDATE t SET age = 99 WHERE id = 1;
-- NOT committed yet
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 99 ← dirty! A hasn't committed

ROLLBACK;
-- age is back to 10, but B already
-- used the value 99 that never existed
                                       COMMIT;
```

> Almost never used in practice. No protection at all.

## READ COMMITTED

Each `SELECT` takes a **fresh snapshot of committed data** at the time the statement executes. This prevents dirty reads, but the snapshot changes between statements.

### Demo: No Dirty Read

```sql
SET SESSION transaction_isolation = 'READ-COMMITTED';  -- both terminals

-- Terminal A                          -- Terminal B
BEGIN;                                 BEGIN;
UPDATE t SET age = 99 WHERE id = 1;
-- NOT committed yet
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 10 ✅ (sees only committed data)
COMMIT;
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 99 (A committed, B sees new snapshot)
                                       COMMIT;
```

### Demo: Non-Repeatable Read

```sql
SET SESSION transaction_isolation = 'READ-COMMITTED';  -- both terminals

-- Terminal A                          -- Terminal B
                                       BEGIN;
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 10

BEGIN;
UPDATE t SET age = 99 WHERE id = 1;
COMMIT;
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 99 ← different!
                                       -- Same row, same TX, different value
                                       COMMIT;
```

> The **snapshot refreshes per statement**. So each SELECT sees the latest committed state, not a frozen view.

### Demo: Phantom Read

```sql
SET SESSION transaction_isolation = 'READ-COMMITTED';  -- both terminals

-- Terminal A                          -- Terminal B
                                       BEGIN;
                                       SELECT * FROM t WHERE age BETWEEN 10 AND 30;
                                       -- Returns: Alice(10), Bob(20), Carol(30)

BEGIN;
INSERT INTO t VALUES (6, 'Eve', 25);
COMMIT;
                                       SELECT * FROM t WHERE age BETWEEN 10 AND 30;
                                       -- Returns: Alice(10), Bob(20), Eve(25), Carol(30)
                                       --          ↑ phantom row appeared!
                                       COMMIT;
```

## REPEATABLE READ (Default)

The snapshot is taken **once at the start of the transaction** (first read). All subsequent reads within the same TX see the same data, regardless of other commits.

InnoDB achieves this with:
- **MVCC snapshot** — frozen view for plain SELECTs (no locks needed)
- **Gap locks** — prevent inserts into scanned ranges for locking reads / DML

### Demo: No Non-Repeatable Read

```sql
SET SESSION transaction_isolation = 'REPEATABLE-READ';  -- both terminals

-- Terminal A                          -- Terminal B
                                       BEGIN;
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 10 (snapshot taken here)

BEGIN;
UPDATE t SET age = 99 WHERE id = 1;
COMMIT;
                                       SELECT age FROM t WHERE id = 1;
                                       -- Returns: 10 ✅ still 10!
                                       -- TX snapshot is frozen, doesn't see A's commit
                                       COMMIT;
```

### Demo: No Phantom Read

```sql
SET SESSION transaction_isolation = 'REPEATABLE-READ';  -- both terminals

-- Terminal A                          -- Terminal B
                                       BEGIN;
                                       SELECT * FROM t WHERE age BETWEEN 10 AND 30;
                                       -- Returns: Alice(10), Bob(20), Carol(30)

BEGIN;
INSERT INTO t VALUES (6, 'Eve', 25);
COMMIT;
                                       SELECT * FROM t WHERE age BETWEEN 10 AND 30;
                                       -- Returns: Alice(10), Bob(20), Carol(30)
                                       --          ✅ no phantom! same result set
                                       COMMIT;
```

### MVCC vs Gap Lock: Two Different Mechanisms

```
                       Plain SELECT              Locking Read (FOR UPDATE) / DML
                       ────────────              ───────────────────────────────
How it prevents        MVCC snapshot             Gap locks
phantom reads:         (reads frozen view,       (physically blocks INSERTs
                        no locks at all)           into the scanned range)
```

Plain `SELECT` doesn't need gap locks because it reads from the frozen snapshot — new rows committed by other TXs are simply invisible. Gap locks are needed for `SELECT ... FOR UPDATE`, `UPDATE`, `DELETE` because these must operate on the **current** data, not the snapshot.

```sql
-- Terminal A                          -- Terminal B
                                       BEGIN;
                                       SELECT * FROM t WHERE age BETWEEN 10 AND 30 FOR UPDATE;
                                       -- Gap locks on idx_age: blocks inserts with age in [10,30]

BEGIN;
INSERT INTO t VALUES (6, 'Eve', 25);
-- ❌ BLOCKED by gap lock (not by MVCC)
```

## SERIALIZABLE

The strictest level. Every plain `SELECT` is implicitly converted to `SELECT ... FOR SHARE`. This means readers **block** writers and writers **block** readers.

### Demo

```sql
SET SESSION transaction_isolation = 'SERIALIZABLE';  -- both terminals

-- Terminal A                          -- Terminal B
BEGIN;                                 BEGIN;
SELECT * FROM t WHERE id = 5;
-- Implicitly: SELECT ... FOR SHARE
-- Acquires S lock on id=5

                                       SELECT * FROM t WHERE id = 5;
                                       -- ✅ OK (S + S compatible)

                                       UPDATE t SET age = 99 WHERE id = 5;
                                       -- ❌ BLOCKED (X conflicts with S)
                                       -- Must wait until A commits
COMMIT;
                                       -- Now unblocked, UPDATE proceeds
                                       COMMIT;
```

> Rarely used in practice — it severely limits concurrency. Most applications use REPEATABLE READ and add explicit `FOR UPDATE` where needed.

## Side-by-Side Comparison

```
-- Same operations, different behavior per isolation level:
--
-- Setup: id=1, age=10 initially
-- TX A: UPDATE age=99 WHERE id=1, then COMMIT
-- TX B: reads age WHERE id=1 before and after A's commit
--
-- ┌──────────────────────┬────────────┬────────────┐
-- │                      │ B's 1st    │ B's 2nd    │
-- │ Isolation Level      │ read       │ read       │
-- │                      │ (before A  │ (after A   │
-- │                      │  commits)  │  commits)  │
-- ├──────────────────────┼────────────┼────────────┤
-- │ READ UNCOMMITTED     │ 99 (dirty) │ 99         │
-- │ READ COMMITTED       │ 10         │ 99 (changed)│
-- │ REPEATABLE READ      │ 10         │ 10 (frozen)│
-- │ SERIALIZABLE         │ 10         │ BLOCKED    │
-- └──────────────────────┴────────────┴────────────┘
```

## How InnoDB Implements Each Level

| Level | Plain SELECT | Locking Read / DML | Gap Locks |
|---|---|---|---|
| READ UNCOMMITTED | Reads latest data (no snapshot) | X record lock | No |
| READ COMMITTED | MVCC snapshot **per statement** | X record lock | No |
| REPEATABLE READ | MVCC snapshot **per transaction** | X record + gap lock | Yes |
| SERIALIZABLE | Implicit `FOR SHARE` (S lock) | X record + gap lock | Yes |

## Reference
- [InnoDB Transaction Isolation Levels — MySQL Official Doc](https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html)
- [MySQL Locking](/posts/db/mysql_locking/) — deep dive into each lock type with demos
