---
title: "metric vs log vs trace"
date: "2026-03-14T08:44:18+08:00"
tags: ["observability"]
description: "the overview for 3 main observability data types: metric, log and trace"
draft: true
---

## Overview

The three pillars of observability each answer a different question:

| Pillar  | Question                     | Value type       | Cardinality | Volume  |
|---------|------------------------------|------------------|-------------|---------|
| Metric  | Is the system healthy?       | float64 sample   | Low         | Low     |
| Log     | What happened?               | variable-length string | High  | High    |
| Trace   | Why did this request slow?   | span tree        | High        | Medium  |

---

## Metric

### Data Structure

A metric is a numeric measurement associated with a set of labels at a point in time.

```
{__name__="http_requests_total", method="GET", status="200"} -> [(t1, 100), (t2, 105), (t3, 112), ...]
```

- **Time series**: identified by metric name + label set (key-value pairs)
- **Sample**: a (timestamp, float64) pair
- **Cardinality**: total number of unique label combinations — the primary scaling challenge

### Storage: TSDB

Prometheus uses a local TSDB with this on-disk layout:

```
data/
├── 01BKGV7JC0RY8A6AVTR4465YY/   <- immutable Block (2h window)
│   ├── chunks/
│   │   └── 000001               <- XOR-compressed samples
│   ├── index                    <- inverted label index
│   └── meta.json
├── chunks_head/                 <- current window (mmap)
└── wal/                         <- Write-Ahead Log (crash recovery)
    └── 00000001
```

**Write path:**
```
Sample arrives
  -> WAL (durability)
  -> Head block (in-memory)
  -> Every 2h: compacted to immutable on-disk Block
  -> Periodic compaction: Blocks merged to reduce query fan-out
```

**XOR compression (Gorilla paper):** adjacent float64 values share many bits; XOR + variable-length encoding achieves ~1.37 bytes/sample.

**Inverted index:** for each label value, stores a posting list of series IDs. Queries intersect posting lists.

```
method="GET"  -> [series_1, series_3, series_7, ...]
status="200"  -> [series_1, series_2, series_5, ...]
intersection  -> [series_1, ...]   <- matches both labels
```

### VictoriaMetrics Storage Differences

VictoriaMetrics uses a columnar LSM-tree (like a merge-tree) instead of Prometheus's append-only block model:

```
Prometheus:            VictoriaMetrics:
time-ordered blocks    columnar partitions per metric/label
per-series chunks      per-column data files
block compaction       LSM-style merge
~1.37 bytes/sample     ~0.4 bytes/sample (better compression)
```

Each label column is stored separately, which improves both compression (similar values together) and query performance (skip irrelevant columns).

### Open Source Projects

| Project          | Storage Model                 | Key Characteristic                        |
|------------------|-------------------------------|-------------------------------------------|
| **Prometheus**   | Local TSDB, pull-based        | Reference implementation                  |
| **VictoriaMetrics** | Columnar LSM TSDB          | Better compression, higher ingest rate    |
| **Thanos**       | Prometheus + object storage   | Long-term retention, global query         |
| **Mimir**        | Prometheus-compatible, multi-tenant | Horizontally scalable, cloud-native |

---

## Log

### Data Structure

A log entry is a timestamped string (structured or unstructured) associated with a stream.

```
stream: {app="api-server", env="prod", pod="api-7d9f"}
entries:
  2026-03-14T08:00:01Z  INFO  user 123 logged in
  2026-03-14T08:00:02Z  ERROR failed to connect to db: timeout
  2026-03-14T08:00:03Z  INFO  retry successful
```

The key challenge: the value is variable-length text. Full-text search requires either an index (expensive) or scanning compressed chunks (cheap to store, slow to query).

### Storage Approach 1: Label Index + Chunk Storage (Loki)

Loki indexes only stream **labels** (not log content), then stores raw compressed log chunks in object storage.

```
Architecture:

  Promtail / Alloy                  Loki cluster
  ─────────────────                 ──────────────────────────────────────────
  collect logs + labels  ─PUSH──>  Distributor
                                        │  (hash stream labels -> ingester)
                                        ▼
                                    Ingester  (in-memory chunks + WAL)
                                        │  (flush when chunk full / time elapsed)
                                        ▼
                              ┌─────────────────────────┐
                              │   Object Storage (S3)   │
                              │   /chunks/{stream}/{t}  │  <- gzip-compressed log lines
                              └─────────────────────────┘
                                        │
                              ┌─────────────────────────┐
                              │   Index (Cassandra /    │
                              │   BoltDB / TSDB)        │  <- label -> chunk pointers
                              └─────────────────────────┘

Query path (LogQL: {app="api-server"} |= "ERROR"):
  Query Frontend
    -> Index lookup: which chunks match {app="api-server"}?
    -> Fetch chunks from object storage
    -> Decompress + grep for "ERROR"
```

Good for: cost-efficiency at scale, Kubernetes log collection.
Bad for: high-cardinality label sets cause index explosion; full-text search without label pre-filter is slow (must scan all chunks).

### Storage Approach 2: Columnar LSM (VictoriaLogs)

VictoriaLogs stores logs in a columnar format where each field is a separate column with its own compression and sparse index. All fields are auto-indexed — no manual label selection required.

```
Architecture:

  Single node:                        Cluster mode:
  ──────────────                      ─────────────────────────────────
  victorialogs binary                 vlinsert   (ingestion layer)
    │                                     │
    ├── partitions/                    vlstorage  (one node per shard)
    │   └── 2026-03-14/               vlselect   (query layer)
    │       ├── _time   (timestamps)
    │       ├── _msg    (message text)
    │       ├── level   (log level)
    │       ├── app     (app label)
    │       └── ...     (all fields auto-indexed)
    └── WAL

Storage internals:
  - Day-partitioned data
  - Columnar blocks: each field stored as separate column
  - Bloom filters per block -> skip blocks that can't match a term
  - Sparse timestamp index -> skip blocks outside time range
  - Custom encoding per field type (IP = 4 bytes, timestamps = delta, strings = token index)
```

**Query (LogsQL):**
```
# find errors with specific user
_time:[2026-03-14, now] AND level:ERROR AND user_id:123

# aggregation pipe
_time:1h | stats count() by app, level
```

Unlike Loki, VictoriaLogs can filter by any field efficiently without pre-declaring labels. High-cardinality fields (trace_id, user_id, IP) are handled well because the columnar model doesn't explode like an inverted document index.

**VictoriaLogs vs Loki:**

| Aspect             | VictoriaLogs                          | Loki                                 |
|--------------------|---------------------------------------|--------------------------------------|
| Index strategy     | Per-token index, all fields auto-indexed | Label-only index                  |
| High-cardinality   | Handles well (columnar isolation)     | Problematic (index explosion)        |
| Full-text search   | Token index; no label pre-filter needed | Requires label narrowing first    |
| Storage backend    | Local disk (columnar files)           | Object storage (S3/GCS)              |
| Query language     | LogsQL (SQL-like pipes)               | LogQL                                |
| Object storage     | No (disk only currently)              | Yes (primary backend)                |
| Cluster mode       | vlinsert / vlstorage / vlselect       | Distributor / Ingester / Querier     |

### Storage Approach 3: Inverted Index (Elasticsearch / OpenSearch)

Each log line is a document. An inverted index maps every token to documents containing it.

```
Document store:
  doc_1: {timestamp: T1, message: "user 123 logged in",   level: "INFO"}
  doc_2: {timestamp: T2, message: "failed to connect db", level: "ERROR"}

Inverted index (Lucene segment):
  "user"    -> [doc_1]
  "failed"  -> [doc_2]
  "ERROR"   -> [doc_2]

Write path:
  Log line -> parse/tokenize -> Lucene segment (immutable)
           -> periodic segment merge (reduces query fan-out)
           -> index refresh (near-real-time searchable)
```

Good for: full-text search, complex multi-field queries.
Bad for: high write volume; index overhead is large (~2-3x raw data size).

### Storage Approach 4: Columnar Analytics DB (ClickHouse)

Logs as rows in a columnar table. Each column (timestamp, level, message, host, ...) stored and compressed separately.

```sql
CREATE TABLE logs (
    timestamp   DateTime64(9),
    level       LowCardinality(String),  -- dictionary encoding
    service     LowCardinality(String),
    message     String,
    trace_id    String
) ENGINE = MergeTree()
PARTITION BY toDate(timestamp)
ORDER BY (service, timestamp);
```

```
timestamp col:  delta + RLE compression
level col:      dictionary encoding (INFO=0, ERROR=1 -> tiny)
message col:    LZ4 per column block
```

Good for: aggregation queries (`count errors by service`), SQL interface, structured logs. Very fast for analytics.

### Open Source Log Projects

| Project              | Storage Backend            | Index Strategy                  | Best For                       |
|----------------------|----------------------------|---------------------------------|--------------------------------|
| **Loki**             | Object storage (S3/GCS)    | Labels only                     | K8s logs, cost-efficiency      |
| **VictoriaLogs**     | Local columnar disk        | All fields auto-indexed (token) | High-cardinality, fast search  |
| **Elasticsearch**    | Lucene segments            | Full inverted index             | Full-text search, complex queries |
| **OpenSearch**       | Lucene segments            | Full inverted index             | ES fork, open-source           |
| **ClickHouse**       | Columnar MergeTree         | Sparse + columnar               | Structured logs, analytics     |

---

## Trace

### Data Structure

A trace is one end-to-end request represented as a tree of **spans**.

```
Trace ID: abc123
│
├── Span: api-server.HandleRequest  (span_id=s1, parent=nil)
│   start=T0, duration=120ms
│   tags: {http.method=GET, http.url=/user/123, http.status=200}
│   │
│   ├── Span: auth.Verify  (span_id=s2, parent=s1)
│   │   start=T0+1ms, duration=5ms
│   │
│   └── Span: db.Query  (span_id=s3, parent=s1)
│       start=T0+10ms, duration=100ms
│       tags: {db.statement="SELECT * FROM users WHERE id=?"}
│       events: [{time=T0+80ms, name="slow_query_warning"}]
```

Each span:
- `trace_id`, `span_id`, `parent_span_id`
- `service_name`, `operation_name`
- `start_time`, `duration`
- `tags` (key-value attributes)
- `events` (timestamped annotations within the span)
- `status` (OK / Error)

### Storage Approach 1: Object Storage, No Index (Tempo)

Tempo stores spans as compressed Parquet/protobuf blobs in object storage, keyed by trace ID. No search index.

```
Architecture:

  OTel Collector / SDK
        │ (OTLP gRPC/HTTP)
        ▼
    Distributor  (receives spans, routes to ingesters by trace_id)
        │
        ▼
    Ingester     (buffers in memory + WAL, flushes every ~15min)
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  Object Storage (S3/GCS/Azure Blob)     │
  │  /blocks/{block_id}/                    │
  │      traces.parquet  <- spans by trace  │
  │      index.json      <- trace_id index  │
  └─────────────────────────────────────────┘
        │
    Compactor   (merges small blocks, applies retention)
        │
    Querier     (fetches blocks, executes TraceQL)

Query path:
  GET /trace/{trace_id}
    -> Query Frontend -> Querier
    -> Lookup block index -> fetch Parquet from S3
    -> Deserialize + return

  TraceQL: {span.http.status_code = 500 && duration > 200ms}
    -> Scan blocks (no index, brute-force with Parquet column pruning)
```

Good for: near-zero operational cost (just object storage).
Bad for: tag-based search scans all blocks; trace discovery relies on external signals (log line with trace_id, or Prometheus exemplar).

### Storage Approach 2: Wide-Column Store (Jaeger + Cassandra)

Cassandra is optimized for time-ordered writes. Jaeger partitions by trace_id.

```
Architecture:

  OTel Collector / Jaeger Agent
        │ (OTLP or Jaeger Thrift)
        ▼
    Jaeger Collector
        │  (validates, transforms)
        ▼
    ┌──────────────────────────────────────────────┐
    │  Cassandra                                   │
    │                                              │
    │  traces table:                               │
    │    PK: trace_id | CK: span_id               │
    │    cols: operation, service, start, duration │
    │                                              │
    │  service_operation_index:                    │
    │    PK: (service, operation, date)            │
    │    CK: start_time DESC                       │
    │    cols: trace_id   <- reverse lookup        │
    └──────────────────────────────────────────────┘

Query: "slow traces for service=api"
  -> service_operation_index -> trace_ids
  -> traces table by trace_id
  -> reconstruct span tree
```

Good for: proven at large scale, flexible secondary indexes.
Bad for: Cassandra operational overhead; tag-based filtering requires Elasticsearch.

### Storage Approach 3: Columnar LSM, No External Deps (VictoriaTraces)

VictoriaTraces uses the same storage philosophy as VictoriaMetrics/VictoriaLogs: columnar LSM on local disk, no external storage required.

```
Architecture:

  OTel Collector / SDK
        │ (OTLP gRPC/HTTP)
        ▼
    VictoriaTraces
        │
        ├── WAL (crash recovery)
        │
        ├── In-memory buffer
        │
        └── Columnar partitions (local disk)
                ├── trace_id  (indexed for lookup)
                ├── service
                ├── operation
                ├── start_time (sparse index)
                ├── duration   (columnar, filterable)
                └── tags       (key-value columns)

Query APIs:
  - Jaeger Query Service JSON API  <- Grafana Jaeger datasource
  - OTLP export

Cluster mode: independent ingestion / storage / query components
```

Good for: simple ops (no object storage, no Cassandra), Jaeger API compatibility.
Bad for: newer product, smaller community vs Jaeger/Tempo.

### Open Source Trace Projects

| Project            | Storage Backend             | Query API              | Key Characteristic                          |
|--------------------|-----------------------------|------------------------|---------------------------------------------|
| **Tempo**          | Object storage (S3/GCS)     | TraceQL, Jaeger API    | Zero index cost, needs external discovery   |
| **Jaeger**         | Cassandra / Elasticsearch   | Jaeger UI + API        | CNCF graduated, battle-tested               |
| **VictoriaTraces** | Local columnar disk         | Jaeger Query JSON API  | No external deps, VM ecosystem              |
| **Zipkin**         | Cassandra / ES / MySQL      | Zipkin API             | Older, simpler, still widely used           |

---

## Unified Observability Stacks

### Grafana LGTM Stack (Modular)

Each pillar has a dedicated best-of-breed component. **Alloy** (Grafana's OTel Collector distribution) routes telemetry to the right backend.

```
Application / Infrastructure
        │
    Grafana Alloy  (OTel Collector distribution)
    ┌───┴──────────────────────────────────────┐
    │  receivers -> processors -> exporters     │
    └───┬──────────────┬──────────────┬────────┘
        │              │              │
        ▼              ▼              ▼
    Mimir           Loki            Tempo
    (metrics)       (logs)          (traces)
    TSDB            label index     object storage
    + object        + object        only
    storage         storage
        │              │              │
        └──────────────┴──────────────┘
                       │
                   Grafana UI
              (unified dashboards,
               correlate across pillars)
```

Cross-pillar correlation:
- Metric exemplars embed `trace_id` -> click through to Tempo
- Loki log lines embed `trace_id` -> click through to Tempo
- Tempo → derived metrics back to Mimir

### VictoriaMetrics Unified Stack

Single vendor, same storage philosophy across all three pillars (columnar LSM, no external deps).

```
Application / Infrastructure
        │
    OTel Collector / vmagent
    ┌───┴──────────────────────────────────────┐
    │  collect + route telemetry               │
    └───┬──────────────┬──────────────┬────────┘
        │              │              │
        ▼              ▼              ▼
  VictoriaMetrics  VictoriaLogs  VictoriaTraces
  (MetricsQL)      (LogsQL)      (Jaeger API)
  columnar LSM     columnar LSM  columnar LSM
  local disk       local disk    local disk

  Cluster modes available for each component:
  VM:     vminsert / vmstorage / vmselect
  Logs:   vlinsert / vlstorage / vlselect
  Traces: ingester / storage  / querier

        │              │              │
        └──────────────┴──────────────┘
                       │
                   Grafana UI
              (vmui + Grafana datasources)
```

Key advantage: one operational model across all three pillars. Lower ops burden vs LGTM.

### SigNoz (OTel-Native, ClickHouse Backend)

SigNoz uses ClickHouse as a single columnar storage backend for all three pillars.

```
Application / Infrastructure
        │ (OpenTelemetry SDK)
        ▼
    OTel Collector  (receives OTLP, batches, routes)
        │
        ▼
    ClickHouse   (single storage backend)
    ┌────────────────────────────────────────┐
    │  signoz_metrics  (metrics tables)      │
    │  signoz_logs     (logs tables)         │
    │  signoz_traces   (traces tables)       │
    │  MergeTree engine, columnar storage    │
    └────────────────────────────────────────┘
        │
    SigNoz API Server
        │
    SigNoz UI  (React, unified dashboards)
               (alerts, traces, logs, metrics)
```

Key advantage: one database to operate; SQL queries across all pillars; natural joins (e.g., `WHERE trace_id = ?` across logs and traces table).

### Classic ELK + Jaeger Stack

```
Application
  │  logs    -> Filebeat / Fluentd -> Elasticsearch
  │  metrics -> Prometheus
  │  traces  -> OTel Collector -> Jaeger (Cassandra or ES)
  │
  └── Kibana (logs) + Grafana (metrics) + Jaeger UI (traces)
```

Still common in enterprises. Richest full-text search, but highest storage/operational cost.

---

## Comparison Summary

| Aspect            | Metric                        | Log                                        | Trace                                       |
|-------------------|-------------------------------|---------------------------------------------|---------------------------------------------|
| Data shape        | (timestamp, labels, float64)  | (timestamp, stream_labels, string)          | tree of spans with tags/events              |
| Index strategy    | Label inverted index           | Label-only (Loki) / token index (VictoriaLogs) / full-text (ES) | Trace ID (Tempo/VictoriaTraces) / secondary index (Jaeger) |
| Storage type      | Columnar TSDB / object storage | Object storage + label index / columnar LSM | Object storage / columnar LSM / wide-column |
| Query pattern     | Range scan + aggregation       | Filter by label + text search               | Lookup by trace ID; tag scan for discovery  |
| Open source       | Prometheus, VictoriaMetrics    | Loki, VictoriaLogs, Elasticsearch           | Jaeger, Tempo, VictoriaTraces               |
| Collection layer  | Prometheus scraper / vmagent   | Promtail, Fluentd, Fluent Bit, Alloy        | OTel Collector                              |

**Unified stack options:**

| Stack                   | Storage backend              | Ops complexity | Best for                              |
|-------------------------|------------------------------|----------------|---------------------------------------|
| **Grafana LGTM**        | Modular (Mimir+Loki+Tempo)   | Medium         | Flexible, best-of-breed per pillar    |
| **VictoriaMetrics**     | Local columnar LSM (all 3)   | Low            | Unified ops, high perf, no object storage |
| **SigNoz**              | ClickHouse (all 3)           | Low            | OTel-native, SQL across pillars       |
| **Elastic (ELK)**       | Lucene / Elasticsearch       | High           | Enterprise, rich full-text search     |
