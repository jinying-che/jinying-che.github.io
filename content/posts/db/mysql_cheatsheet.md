---
title: "MySQL Cheatsheet"
date: "2026-02-23T15:39:30+08:00"
tags: ["mysql", "cheatsheet"]
description: "how to troubleshoot mysql?"
draft: true
---

## Quick Status

```sql
-- mysql version
SELECT VERSION();

-- what's going on? (truncated query, use FULL for complete SQL)
SHOW PROCESSLIST;
SHOW FULL PROCESSLIST;

-- server uptime, queries, threads, slow queries
SHOW GLOBAL STATUS LIKE 'Uptime';
SHOW GLOBAL STATUS LIKE 'Threads_%';
SHOW GLOBAL STATUS LIKE 'Slow_queries';
SHOW GLOBAL STATUS LIKE 'Questions';
```

## Table & Row Stats

```sql
-- fast row count for a single table (approximate, from metadata, no table scan)
SHOW TABLE STATUS WHERE Name = 'your_table';

-- fast row count across all tables in current db
SELECT table_name, table_rows, data_length, index_length
FROM information_schema.tables
WHERE table_schema = 'your_db';

-- table size (human-readable)
SELECT table_name,
       ROUND(data_length / 1024 / 1024, 2) AS data_mb,
       ROUND(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.tables
WHERE table_schema = 'your_db'
ORDER BY data_length DESC;
```

> `table_rows` is an **estimate** for InnoDB (exact for MyISAM). Much faster than `SELECT COUNT(*)` which requires a full table scan.

## Connections

```sql
-- current / max connections
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL VARIABLES LIKE 'max_connections';

-- who is connected
SELECT user, host, db, command, time, state
FROM information_schema.processlist
ORDER BY time DESC;

-- kill a long-running query
KILL <process_id>;
```

## Locks & Transactions

```sql
-- current locks (InnoDB)
SELECT * FROM information_schema.innodb_locks;
SELECT * FROM information_schema.innodb_lock_waits;

-- current transactions
SELECT * FROM information_schema.innodb_trx;

-- find blocking queries (MySQL 8.0+, performance_schema)
SELECT * FROM sys.innodb_lock_waits\G
```

## Slow Queries

```sql
-- is slow query log enabled?
SHOW VARIABLES LIKE 'slow_query_log%';
SHOW VARIABLES LIKE 'long_query_time';

-- enable on the fly
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- threshold in seconds
```

## Query Analysis

```sql
-- execution plan
EXPLAIN SELECT ...;
EXPLAIN FORMAT=JSON SELECT ...;  -- more detail

-- index usage of a table
SHOW INDEX FROM your_table;

-- table structure
SHOW CREATE TABLE your_table;
DESC your_table;
```

## InnoDB Engine

```sql
-- InnoDB overall status (buffer pool, I/O, locks, transactions)
SHOW ENGINE INNODB STATUS\G

-- buffer pool hit rate
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read%';

-- buffer pool size
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';

-- dirty pages / flush
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_pages_%';
```

## Replication

```sql
-- replica status
SHOW REPLICA STATUS\G   -- MySQL 8.0.22+
SHOW SLAVE STATUS\G      -- older versions

-- binary log
SHOW MASTER STATUS;
SHOW BINARY LOGS;
```

## Useful One-liners

```sql
-- find tables without a primary key
SELECT t.table_schema, t.table_name
FROM information_schema.tables t
LEFT JOIN information_schema.table_constraints c
  ON t.table_schema = c.table_schema
  AND t.table_name = c.table_name
  AND c.constraint_type = 'PRIMARY KEY'
WHERE t.table_schema NOT IN ('mysql','information_schema','performance_schema','sys')
  AND t.table_type = 'BASE TABLE'
  AND c.constraint_name IS NULL;

-- find duplicate indexes
SELECT * FROM sys.schema_redundant_indexes;

-- find unused indexes
SELECT * FROM sys.schema_unused_indexes;
```
