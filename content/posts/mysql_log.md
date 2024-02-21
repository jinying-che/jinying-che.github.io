---
title: "Mysql Log"
date: "2024-01-27T22:18:59+08:00"
tags: ["", ""]
description: ""
draft: true
---

When a update sql is excuted in InnoDB, there's are three kind of log involved.


## Redo Log
1. The redo log is a disk-based data structure used during crash recovery to correct data written by incomplete transactions. 
2. During normal operations, the redo log encodes requests to change table data that result from SQL statements or low-level API calls.



The redo log is physically represented on disk by redo log files. 

## Binary Log
The binary log contains table creation operations or changes to table data. The binary log is not used for statements such as SELECT or SHOW that do not modify data. 

The binary log has two important purposes:
1. For replication, the binary log on a replication source server provides a record of the data changes to be sent to replicas.
2. Certain data recovery operations require use of the binary log. 

## Undo Log
TBD


## Reference
- https://dev.mysql.com/doc/refman/8.0/en/binary-log.html
- https://dev.mysql.com/doc/refman/8.0/en/innodb-redo-log.html
- https://dev.mysql.com/doc/refman/8.0/en/innodb-undo-logs.html
