---
title: "VictoriaLogs"
date: "2025-12-16T10:28:36+08:00"
tags: ["log", "victoriametrics"]
description: "VictoriaLogs Overview"
draft: true
---

## Data Model
VictoriaLogs works with both structured and unstructured logs. Every log entry must contain at least the log message field . An arbitrary number of additional key=value fields can be added to the log entry. 
```JSON
{
  "job": "my-app",
  "instance": "host123:4567",
  "level": "error",
  "client_ip": "1.2.3.4",
  "trace_id": "1234-56789-abcdef",
  "_msg": "failed to serve the client request"
}
```

## Storage
### 3 way to optimize log storage
bloom filters + streams + column-oriented storage

> 1. VictoriaLogs uses bloom filters for improving the performance of full-text search, while keeping low storage space usage (up to 15x less than Elasticsearch) and low RAM size requirements (up to 30x less than Elasticsearch). Simple queries may be still slower than in Elasticsearch though :(
> 2. VictoriaLogs supports log streams similar to Grafana Loki. This provides fast querying over log streams.
> 3. VictoriaLogs uses column-oriented storage for reducing storage space usage further. This also reduces storage read IO bandwidth usage during heavy queries over large volumes of logs.

## References
- https://docs.victoriametrics.com/victorialogs/keyconcepts/
- [How do open source solutions for logs work: Elasticsearch, Loki and VictoriaLogs](https://itnext.io/how-do-open-source-solutions-for-logs-work-elasticsearch-loki-and-victorialogs-9f7097ecbc2f)
