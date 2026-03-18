---
title: "MySQL Locking"
date: "2023-11-22T10:35:54+08:00"
tags: ["mysql"]
description: "MySQL Locking Overview"
draft: true
---

## TL;DR

InnoDB locks are placed on **index records**, not on "rows" abstractly. Understanding what gets locked (and what doesn't) is key to diagnosing deadlocks, unexpected blocking, and performance issues.

| Lock Type | What It Locks | Why It Exists |
|---|---|---|
| S / X (Shared / Exclusive) | A specific row | Concurrent read vs exclusive write |
| Intention (IS / IX) | Table-level flag | Avoid scanning all rows when acquiring table locks |
| Record Lock | Single index record | Protect one row from concurrent modification |
| Gap Lock | Gap between two index records | Prevent phantom inserts into a range |
| Next-Key Lock | Record + gap before it | Default in REPEATABLE READ, prevents phantoms completely |
| Insert Intention Lock | Position within a gap | Allow concurrent inserts at different positions in the same gap |

This post covers each lock type with **two-terminal demos** you can copy-paste and run — seeing locks in action is much clearer than reading definitions. Open two `mysql` sessions and follow along.

## Setup

```sql
CREATE TABLE t (
  id INT PRIMARY KEY,
  name VARCHAR(32),
  age INT,
  INDEX idx_age (age)
) ENGINE=InnoDB;

INSERT INTO t VALUES
  (1, 'Alice', 10),
  (5, 'Bob', 20),
  (10, 'Carol', 30),
  (15, 'Dave', 40);
```

Index state for reference:
```
Clustered Index (id):   1 --- 5 --- 10 --- 15
Secondary Index (age): 10 --- 20 --- 30 --- 40
```

## Isolation Levels

Locks exist to enforce isolation guarantees. Different isolation levels protect against different anomalies:

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
SET SESSION transaction_isolation = 'READ-COMMITTED';
```

**Why this matters for locking**: `REPEATABLE READ` uses **next-key locks** (record + gap) to prevent phantoms. `READ COMMITTED` uses **record locks only** — no gap locks. This single difference changes nearly every locking behavior below.

> **Deep Dive**: [MySQL Isolation Levels](/posts/db/mysql_isolation/) — explains each anomaly (dirty read, non-repeatable read, phantom read) with demos.

## Shared and Exclusive Locks (S / X)

Row-level locks with two modes:

| | S (Shared) | X (Exclusive) |
|---|---|---|
| **S (Shared)** | Compatible | Conflict |
| **X (Exclusive)** | Conflict | Conflict |

- **S lock**: allows other transactions to read the same row, blocks writes
- **X lock**: blocks both reads (locking reads) and writes from other transactions

**Why**: S lock allows concurrent reads without interference. X lock ensures a writer has exclusive access so no one reads stale data or overwrites concurrently.

### Demo

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 5 FOR SHARE;  -- acquires S lock on id=5

-- Terminal B
SELECT * FROM t WHERE id = 5 FOR SHARE;  -- ✅ OK (S + S compatible)
UPDATE t SET name = 'Bob2' WHERE id = 5;  -- ❌ BLOCKED (X conflicts with S)

-- Terminal A
ROLLBACK;  -- releases S lock
-- Terminal B unblocks, UPDATE succeeds
```

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 5 FOR UPDATE;  -- acquires X lock on id=5

-- Terminal B
SELECT * FROM t WHERE id = 5 FOR SHARE;   -- ❌ BLOCKED (S conflicts with X)
SELECT * FROM t WHERE id = 5 FOR UPDATE;  -- ❌ BLOCKED (X conflicts with X)
SELECT * FROM t WHERE id = 5;             -- ✅ OK (plain SELECT uses MVCC snapshot, no lock)

-- Terminal A
ROLLBACK;
```

> **Key insight**: plain `SELECT` (without `FOR SHARE`/`FOR UPDATE`) never acquires locks — it reads from the MVCC snapshot. Only **locking reads** (`FOR SHARE`, `FOR UPDATE`) and **DML** (`UPDATE`, `DELETE`, `INSERT`) acquire row locks.

### How to check locks

```sql
-- see current locks held
SELECT * FROM performance_schema.data_locks\G

-- see lock waits (who is blocking whom)
SELECT * FROM performance_schema.data_lock_waits\G

-- human-readable blocking info
SELECT * FROM sys.innodb_lock_waits\G
```

## Intention Locks (IS / IX)

**Table-level** locks that signal a transaction's **intent** to acquire row-level locks.

| | IS | IX | S | X |
|---|---|---|---|---|
| **IS** | Compatible | Compatible | Compatible | Conflict |
| **IX** | Compatible | Compatible | Conflict | Conflict |
| **S** | Compatible | Conflict | Compatible | Conflict |
| **X** | Conflict | Conflict | Conflict | Conflict |

**Why**: without intention locks, acquiring a table-level lock (e.g. `LOCK TABLES t WRITE`) would need to check **every row** to see if any row lock exists. Intention locks allow the table-level lock to check a single table-level flag instead.

- `FOR SHARE` → acquires **IS** on the table, then **S** on the row
- `FOR UPDATE` / `UPDATE` / `DELETE` → acquires **IX** on the table, then **X** on the row

### Demo

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 5 FOR UPDATE;  -- acquires IX (table) + X (row)

-- Terminal B
LOCK TABLES t WRITE;  -- ❌ BLOCKED (table X conflicts with IX)
LOCK TABLES t READ;   -- ❌ BLOCKED (table S conflicts with IX)

-- Another scenario:
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 5 FOR SHARE;  -- acquires IS (table) + S (row)

-- Terminal B
LOCK TABLES t READ;   -- ✅ OK (table S compatible with IS)
LOCK TABLES t WRITE;  -- ❌ BLOCKED (table X conflicts with IS)
```

> Intention locks **never conflict with each other** (IS vs IX is always compatible). They only conflict with **table-level** S/X locks.

## Record Locks

Lock a **single index record**. This is the most basic row-level lock.

**Why**: protect a specific row from concurrent modification.

Record locks always lock **index records**, even if a table has no explicit index — InnoDB creates a hidden clustered index (on the row ID) and locks that.

### Demo

```sql
-- Terminal A
BEGIN;
UPDATE t SET name = 'Alice2' WHERE id = 1;  -- X record lock on id=1

-- Terminal B
UPDATE t SET name = 'Alice3' WHERE id = 1;  -- ❌ BLOCKED (same record)
UPDATE t SET name = 'Bob2' WHERE id = 5;    -- ✅ OK (different record)

-- check locks
SELECT engine_lock_id, lock_type, lock_mode, lock_data
FROM performance_schema.data_locks
WHERE object_name = 't';
/*
+------------------+-----------+-----------+-----------+
| engine_lock_id   | lock_type | lock_mode | lock_data |
+------------------+-----------+-----------+-----------+
| ...              | TABLE     | IX        | NULL      |  ← intention lock
| ...              | RECORD    | X,REC_NOT_GAP | 1     |  ← record lock on id=1
+------------------+-----------+-----------+-----------+
*/
```

## Gap Locks

Lock the **gap between** index records, preventing inserts into that gap. The gap lock does **not** lock the record itself.

**Why**: prevent **phantom reads**. Without gap locks, another transaction could insert a new row into a range you already queried, causing a different result set on the next read within the same transaction.

```
Records:   1 --- 5 --- 10 --- 15
Gaps:    (-∞,1) (1,5) (5,10) (10,15) (15,+∞)
```

Gap locks **can co-exist** — multiple transactions can hold gap locks on the same gap. There is no difference between shared and exclusive gap locks. They do not conflict with each other. Their only purpose is to **block inserts** into the gap.

### Demo: Phantom Read Prevention

```sql
-- Terminal A (REPEATABLE READ)
BEGIN;
SELECT * FROM t WHERE id BETWEEN 5 AND 10 FOR UPDATE;
-- Locks: X record on id=5, X record on id=10, gap lock on (5,10)

-- Terminal B
INSERT INTO t VALUES (7, 'Eve', 25);  -- ❌ BLOCKED (7 falls in gap (5,10))
INSERT INTO t VALUES (3, 'Frank', 15); -- ✅ OK (3 falls in gap (1,5), not locked)

-- Without the gap lock, Terminal B's insert of id=7 would succeed,
-- and Terminal A's next SELECT would return a "phantom" row
```

### Demo: Gap Locks Don't Conflict with Each Other

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 8 FOR UPDATE;
-- id=8 doesn't exist → gap lock on (5,10), no record lock

-- Terminal B
BEGIN;
SELECT * FROM t WHERE id = 7 FOR UPDATE;
-- id=7 doesn't exist → gap lock on (5,10), no record lock
-- ✅ OK! Both hold gap lock on the same gap — no conflict

-- But:
INSERT INTO t VALUES (6, 'Eve', 25);  -- ❌ BLOCKED (insert into locked gap)
```

### Gap Locks Under READ COMMITTED

```sql
-- Gap locks are DISABLED under READ COMMITTED
SET SESSION transaction_isolation = 'READ-COMMITTED';

-- Terminal A
BEGIN;
SELECT * FROM t WHERE id BETWEEN 5 AND 10 FOR UPDATE;
-- Only record locks on id=5 and id=10, NO gap lock

-- Terminal B
INSERT INTO t VALUES (7, 'Eve', 25);  -- ✅ OK (no gap lock to block it)
-- This means phantom reads are possible under READ COMMITTED
```

## Next-Key Locks

A **next-key lock = record lock + gap lock** on the gap **before** that record. It locks the record AND the gap in front of it.

```
Records:   1 --- 5 --- 10 --- 15
Next-key:  (-∞,1] (1,5] (5,10] (10,15] (15,+∞)
            ↑ gap + record  ↑
```

**Why**: this is InnoDB's **default locking strategy** in `REPEATABLE READ`. By locking both the record and the preceding gap, it prevents both concurrent modification of existing rows AND insertion of new rows into the scanned range — solving the phantom read problem completely.

### Locking Rules (Important)

InnoDB applies next-key locks during index scans, then **optimizes** them down based on conditions:

1. **Unique index + exact match on existing record** → degrades to **record lock only** (gap lock unnecessary because uniqueness guarantees no phantom)
2. **Unique index + exact match on non-existing record** → degrades to **gap lock only**
3. **Non-unique index scan** → full **next-key lock** (record + gap)
4. **Range scan** → next-key locks on all scanned records + gap after the last scanned record

### Demo: Rule 1 — Unique Index Exact Match

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 5 FOR UPDATE;
-- id is PRIMARY KEY (unique), row exists
-- → record lock on id=5 ONLY, no gap lock

-- Terminal B
INSERT INTO t VALUES (3, 'Eve', 15);  -- ✅ OK (no gap lock on (1,5))
INSERT INTO t VALUES (7, 'Eve', 25);  -- ✅ OK (no gap lock on (5,10))
UPDATE t SET name = 'Bob2' WHERE id = 5; -- ❌ BLOCKED (record lock)
```

### Demo: Rule 2 — Unique Index, Record Not Found

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 8 FOR UPDATE;
-- id=8 doesn't exist, falls in gap (5,10)
-- → gap lock on (5,10) ONLY, no record lock

-- Terminal B
INSERT INTO t VALUES (7, 'Eve', 25);   -- ❌ BLOCKED (in gap)
INSERT INTO t VALUES (6, 'Eve', 25);   -- ❌ BLOCKED (in gap)
UPDATE t SET name = 'Bob2' WHERE id = 5;  -- ✅ OK (id=5 not locked)
UPDATE t SET name = 'Carol2' WHERE id = 10; -- ✅ OK (id=10 not locked)
```

### Demo: Rule 3 — Non-Unique Index

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE age = 20 FOR UPDATE;
-- age is non-unique index, scans idx_age
-- → next-key lock on (10, 20] on idx_age
-- → gap lock on (20, 30) on idx_age (to prevent phantoms with age=20)
-- → record lock on clustered index id=5

-- Terminal B
INSERT INTO t VALUES (3, 'Eve', 15);   -- ❌ BLOCKED (age=15 in gap (10,20))
INSERT INTO t VALUES (6, 'Eve', 25);   -- ❌ BLOCKED (age=25 in gap (20,30))
INSERT INTO t VALUES (20, 'Eve', 35);  -- ✅ OK (age=35 in gap (30,40), not locked)
UPDATE t SET name = 'Alice2' WHERE id = 1; -- ✅ OK (id=1 not locked)
```

### Demo: Rule 4 — Range Scan

```sql
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id >= 10 FOR UPDATE;
-- Scans: id=10, id=15, then supremum (the "infinity" pseudo-record)
-- → next-key lock on (5,10], (10,15], (15,+∞)

-- Terminal B
INSERT INTO t VALUES (7, 'Eve', 25);   -- ❌ BLOCKED (in gap (5,10))
INSERT INTO t VALUES (12, 'Eve', 25);  -- ❌ BLOCKED (in gap (10,15))
INSERT INTO t VALUES (20, 'Eve', 25);  -- ❌ BLOCKED (in gap (15,+∞))
UPDATE t SET name = 'Bob2' WHERE id = 5; -- ✅ OK (id=5 not locked, only gap before 10)
```

## Insert Intention Locks

A special type of **gap lock** acquired by `INSERT` before inserting a row. It signals the intent to insert at a specific position within a gap.

**Why**: allow multiple inserts into the **same gap** at **different positions** without blocking each other. Without insert intention locks, any insert into a gap-locked range would block all other inserts into that same gap — even at non-conflicting positions.

Insert intention locks **conflict with gap locks** but **do not conflict with each other** (as long as they target different positions).

### Demo

```sql
-- Two inserts into the same gap, different positions — no conflict:

-- Terminal A
BEGIN;
INSERT INTO t VALUES (3, 'Eve', 15);
-- Acquires insert intention lock in gap (1,5) at position 3
-- Then acquires X record lock on id=3

-- Terminal B
BEGIN;
INSERT INTO t VALUES (4, 'Frank', 18);
-- Acquires insert intention lock in gap (1,5) at position 4
-- ✅ OK! Different positions, no conflict

-- But if a gap lock exists:
-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 3 FOR UPDATE;
-- id=3 doesn't exist → gap lock on (1,5)

-- Terminal B
INSERT INTO t VALUES (4, 'Frank', 18);
-- ❌ BLOCKED (insert intention lock conflicts with gap lock)
```

## Deadlocks

Deadlocks occur when two transactions hold locks that the other needs, creating a circular wait.

**Why it matters**: InnoDB automatically **detects** deadlocks and rolls back the cheaper transaction (fewer rows modified). But understanding common patterns helps you avoid them.

### Demo: Classic Deadlock

```sql
-- Terminal A
BEGIN;
UPDATE t SET name = 'Alice2' WHERE id = 1;  -- X lock on id=1

-- Terminal B
BEGIN;
UPDATE t SET name = 'Bob2' WHERE id = 5;    -- X lock on id=5

-- Terminal A
UPDATE t SET name = 'Alice_Bob' WHERE id = 5;  -- ❌ BLOCKED (waiting for id=5)

-- Terminal B
UPDATE t SET name = 'Bob_Alice' WHERE id = 1;  -- DEADLOCK DETECTED!
-- ERROR 1213 (40001): Deadlock found; try restarting transaction
-- Terminal B is rolled back, Terminal A proceeds
```

### Demo: Gap Lock Deadlock (Subtle)

```sql
-- This is a common surprise in production:

-- Terminal A
BEGIN;
SELECT * FROM t WHERE id = 8 FOR UPDATE;  -- gap lock on (5,10)

-- Terminal B
BEGIN;
SELECT * FROM t WHERE id = 8 FOR UPDATE;  -- gap lock on (5,10) — ✅ OK! gap locks coexist

-- Terminal A
INSERT INTO t VALUES (7, 'Eve', 25);
-- ❌ BLOCKED (Terminal B's gap lock blocks this insert intention lock)

-- Terminal B
INSERT INTO t VALUES (9, 'Frank', 35);
-- DEADLOCK! Terminal A's gap lock blocks this insert too
-- Both waiting for each other's gap lock to release
```

> This pattern often appears in "INSERT ... ON DUPLICATE KEY UPDATE" or "check-then-insert" logic.

### Diagnosing Deadlocks

```sql
-- show the most recent deadlock
SHOW ENGINE INNODB STATUS\G
-- Look for "LATEST DETECTED DEADLOCK" section

-- enable deadlock logging to error log
SET GLOBAL innodb_print_all_deadlocks = ON;
```

## Locking and Indexes

Locks are placed on **index records**, not on "rows" abstractly. The index used (or lack thereof) dramatically affects what gets locked.

### No Index → Full Table Lock (Effectively)

```sql
-- name has no index
-- Terminal A
BEGIN;
UPDATE t SET age = 99 WHERE name = 'Alice';
-- InnoDB must scan the clustered index (full table scan)
-- Locks EVERY record it examines: id=1, 5, 10, 15 + all gaps

-- Terminal B
UPDATE t SET age = 100 WHERE id = 15;  -- ❌ BLOCKED (id=15 is locked!)
INSERT INTO t VALUES (20, 'Eve', 25);  -- ❌ BLOCKED (all gaps locked)
```

> **Lesson**: always ensure your `WHERE` clause uses an indexed column. Without an index, InnoDB locks the entire table effectively.

### Secondary Index → Two B+ Trees Locked

When a query uses a secondary index, InnoDB locks records in **both** the secondary index B+ tree and the clustered index B+ tree:

```sql
-- Terminal A
BEGIN;
UPDATE t SET name = 'Bob2' WHERE age = 20;
-- 1. Lock on idx_age: next-key lock (10, 20] + gap lock (20, 30)
-- 2. Lock on clustered index: record lock on id=5

-- Terminal B
UPDATE t SET age = 25 WHERE id = 5;    -- ❌ BLOCKED (clustered index id=5 locked)
INSERT INTO t VALUES (3, 'Eve', 15);   -- ❌ BLOCKED (age=15 in gap (10,20) on idx_age)
UPDATE t SET name = 'X' WHERE age = 30; -- ✅ OK (age=30 not in locked range)
```

## Lock Compatibility Summary

```
              Existing Lock
              S     X     Gap   Insert-Intention   Next-Key
Request  S    ✅    ❌    ✅    ✅                 ❌
         X    ❌    ❌    ✅    ✅                 ❌
         Gap  ✅    ✅    ✅    ✅                 ✅
         I-I  ✅    ✅    ❌    ✅                 ❌
         N-K  ❌    ❌    ✅    ✅                 ❌

✅ = compatible (both can coexist)
❌ = conflict (requester must wait)
```

Key takeaways:
- **Gap locks never conflict with each other** — they only block inserts
- **Insert intention locks only conflict with gap locks** — not with each other
- **Record locks follow the simple S/X compatibility** rule

## Reference
- [InnoDB Locking — MySQL Official Doc](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking.html)
- [InnoDB Transaction Isolation Levels](https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html)
