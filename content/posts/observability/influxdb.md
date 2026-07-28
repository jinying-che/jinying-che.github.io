---
title: "InfluxDB"
date: "2026-07-22T16:02:35+0800"
tags: ["influxdb", "monitoring"]
description: "A practical guide to InfluxDB's data model, storage architecture, deployment options, and trade-offs versus Prometheus."
---

## Overview

InfluxDB is a time-series database: a database optimized for values that arrive with timestamps, are usually appended rather than updated, and are commonly queried over time ranges.

InfluxDB provides a richer value model than a monitoring-only metrics system. A point can contain several typed fields, such as a float temperature, an integer error count, a Boolean status, and a string state. Data is normally pushed to InfluxDB using its compact **line protocol**, then queried with SQL or InfluxQL.

The most important fact to understand in 2026 is that **InfluxDB 3 is not just a newer release of the InfluxDB 1/2 storage engine**. InfluxDB 3 replaced the TSM/TSI engine with a columnar engine based on Apache Arrow, DataFusion, and Parquet. This post focuses on the current open-source product, **InfluxDB 3 Core**, and keeps the older architecture in a separate section.

## Version Map

The term "InfluxDB" can refer to products with materially different storage engines and query languages.

| Version               | Logical hierarchy                   | Main query interface         | Storage engine                   | Important note                                       |
| --------------------- | ----------------------------------- | ---------------------------- | -------------------------------- | ---------------------------------------------------- |
| InfluxDB 1.x          | database → measurement              | InfluxQL                     | WAL + cache + TSM + TSI          | Original open-source architecture                    |
| InfluxDB 2.x          | organization → bucket → measurement | Flux; InfluxQL compatibility | WAL + cache + TSM + TSI          | Added tokens, UI, tasks, and the Flux language       |
| InfluxDB 3 Core       | database → table                    | SQL and InfluxQL             | WAL + Arrow/DataFusion + Parquet | Open-source, single-node, optimized for recent data  |
| InfluxDB 3 Enterprise | database → table                    | SQL and InfluxQL             | Parquet engine plus compaction   | Adds long-range query optimization, HA, and replicas |

InfluxDB 3 does **not** support Flux. A migration plan must therefore cover queries and tasks as well as moving data.

## Data Model

InfluxDB 3 organizes data as:

```text
InfluxDB server
└── database                         # called a bucket in InfluxDB 2
    └── table                        # called a measurement in InfluxDB 1/2
        ├── time                     # required nanosecond timestamp
        ├── tags                     # identifying string metadata
        └── fields                   # measured, typed values
```

The native write representation is line protocol:

```text
<table>,<tag_key>=<tag_value> <field_key>=<field_value> <timestamp>
```

For example:

```text
cpu,region=sg,host=web-01 usage_user=21.5,usage_system=7.2,healthy=true 1710000000000000000
```

| Element   | Example                                         | Meaning                                    |
| --------- | ----------------------------------------------- | ------------------------------------------ |
| Table     | `cpu`                                           | Logical group of homogeneous points        |
| Tags      | `region=sg,host=web-01`                         | String metadata that identifies the series |
| Fields    | `usage_user=21.5,usage_system=7.2,healthy=true` | Values being measured                      |
| Timestamp | `1710000000000000000`                           | Unix time; this example uses nanoseconds   |

A **point** is one table, tag set, field set, and timestamp. A **series** is identified by its table and tag set. In InfluxDB 3, a row's primary key consists of the ordered tag set plus its timestamp.

### Tags versus fields

The distinction affects physical layout and query performance:

- Use **tags** for identity and context: `region`, `host`, `sensor_id`, or `device_model`.
- Use **fields** for measured values: `temperature`, `bytes_sent`, `status`, or `price`.
- Tag values are strings.
- Fields can be integers, unsigned integers, floats, strings, or Booleans.

A useful test is: "Does this value identify where the observation came from, or is it the observation?"

```text
sensor_id=abc-123     -> tag: identifies the source
temperature=23.7      -> field: value produced by the source
```

InfluxDB 3 is designed to handle far higher tag cardinality than the older TSI engine. That does not make schema cost disappear: every additional tag widens the primary key and adds sorting and storage work.

### Schema-on-write

InfluxDB creates a table schema from the first write and validates later writes against it. This makes ingestion easy, but the first production write is a schema decision:

- The initial tag order becomes the physical primary-key column order.
- Tag definitions for an existing table are immutable.
- A field should keep the same type across writes.
- A name cannot be both a tag and a field in the same table.

Put frequently filtered tags first. If queries usually filter by region and then host, prefer:

```text
cpu,region=sg,host=web-01 usage_user=21.5
```

over:

```text
cpu,host=web-01,region=sg usage_user=21.5
```

### Practical schema rules

1. Keep each table homogeneous: all rows should describe the same kind of event.
2. Avoid wide tables with hundreds of tags and fields.
3. Avoid sparse tables in which most columns are null on most rows.
4. Write related fields with the same timestamp in one point.
5. Use one attribute per tag instead of embedding several attributes in a composite string.
6. Batch points to reduce HTTP and durability overhead.
7. Decide retention when creating the database. In Core, the retention period cannot currently be changed later.

## InfluxDB 3 Core Architecture

InfluxDB 3 is a real-time columnar database written in Rust. Apache Arrow provides its in-memory columnar representation, Apache DataFusion supplies the query engine, and Apache Parquet is the durable analytical file format.

### Write path

![InfluxDB 3 Core write and query architecture](/images/influxdb3-core-architecture.drawio.svg)

The diagram combines the write and query paths because the queryable buffer and persisted Parquet files participate in both.

The write-ahead log provides recovery after a crash. Unless `no_sync` is requested, a successful write waits for WAL persistence. The data then becomes available from the queryable buffer. By default, older buffered data is converted into Parquet files approximately every ten minutes, while the most recent data remains memory-resident.

The "object store" in this design is an abstraction. It can be a directory on local disk or a cloud object store. Using S3 instead of a local directory improves storage durability and allows diskless compute, but it does not turn the single-node Core process into a highly available database.

### Query path

The lower path in the diagram shows DataFusion combining hot rows from the queryable buffer with recent cached files and durable object-store Parquet before applying vectorized operators and encoding the result.

Columnar storage is a good match for time-series analytics. A query such as "average CPU by region for the last hour" reads the time, region, and CPU columns without decoding unrelated fields.

```sql
SELECT
  date_bin(INTERVAL '5 minutes', time) AS window,
  region,
  avg(usage_user) AS avg_usage_user
FROM cpu
WHERE time >= now() - INTERVAL '1 hour'
GROUP BY window, region
ORDER BY window, region;
```

InfluxDB 3 Core also has optional last-value and distinct-value caches for common dashboard and metadata lookups.

### Why Parquet and object storage?

The design makes several deliberate trade-offs:

| Choice                              | Benefit                                              | Cost                                                      |
| ----------------------------------- | ---------------------------------------------------- | --------------------------------------------------------- |
| Immutable Parquet files             | Compression, column pruning, interoperability        | Point updates and deletes are not OLTP-like operations    |
| Arrow in memory                     | Efficient vectorized execution and data interchange  | Queries still require enough memory for their working set |
| DataFusion                          | SQL, joins, windows, and extensible query planning   | Different semantics and migration work from Flux          |
| Object-store persistence            | Cheap durable storage and compute/storage separation | Network reads can increase cold-query latency             |
| Recent in-memory buffers and caches | Low latency for current data                         | Memory sizing matters under heavy ingest and query load   |

### The current Core boundary

InfluxDB 3 Core is optimized for recent data. Its default `query-file-limit` is 432 Parquet files. With the default ten-minute generation, that corresponds to approximately 72 hours, although the exact reachable time range can be smaller depending on ingestion timing.

Increasing the limit can increase memory use, object-store requests, and out-of-memory risk. Retention and queryability are different concepts: Core can retain Parquet files longer than 72 hours while still being a poor fit for broad historical queries. InfluxDB 3 Enterprise adds long-range compaction, historical-query optimization, high availability, and read replicas.

## InfluxDB OSS 1.8.5: TSM1 Storage and Series Indexes

InfluxDB OSS 1.8.5 uses the older Go-based TSM1 engine. InfluxDB 2.x retained the same broad storage family, but the flow below is traced specifically from the `v1.8.5` source.

![Legacy InfluxDB TSM and TSI write and query architecture](/images/influxdb-tsm-tsi-architecture.drawio.svg)

### Write and recovery path

The `PointsWriter` resolves the retention policy, maps each point's timestamp to a shard group and shard, and writes different shards concurrently. Each shard validates fields, creates missing series and field metadata, and then calls its TSM1 engine.

Inside `Engine.WritePointsWithContext`, the live write order is:

1. Add values to the in-memory cache with `Cache.WriteMulti`.
2. Append the same values to the shard's WAL with `WAL.WriteMulti`.
3. Wait for WAL `fsync` before returning success. The default `wal-fsync-delay` is zero, so every write waits for a sync unless the setting is changed.

The cache-first function order does not make an unacknowledged write durable. If the process stops before the WAL sync completes, the caller has not received success and must retry. During restart, the engine replays WAL segments into the cache; queries never read WAL files directly.

Database, retention-policy, and shard metadata are persisted in the node's local `meta.db`. InfluxDB OSS 1.8.5 does not depend on etcd.

### Cache snapshots and TSM compaction

**TSM**, or Time-Structured Merge Tree, stores compressed blocks under composite series-and-field keys ordered by time. By default, a shard snapshots its cache after it exceeds 25 MiB or receives no writes for ten minutes. The snapshot is deduplicated and sorted, written to new TSM files, installed in the `FileStore`, and only then are the covered cache snapshot and closed WAL segments removed.

Separate level and full compactions merge smaller TSM files, improve compression, apply tombstones, and ensure that newer values replace older values for the same timestamp. A full compaction becomes eligible after a shard has been write-cold for four hours by default.

### Series indexes and queries

InfluxDB OSS 1.8.5 supports two series-index implementations:

- `inmem` is the default and keeps the series index in memory.
- `tsi1` is optional. It uses a database-level `SeriesFile` plus partitioned log and memory-mapped index files, allowing high-cardinality metadata to rely less heavily on heap memory. TSI log and index files have their own compaction process, separate from TSM data compaction.

For a query, the configured series index identifies matching series from measurement and tag predicates. Per-field cursors then merge recent values from `Cache.Values` with persisted values from the TSM `FileStore`. When both contain a point at the same timestamp, the cache value takes precedence.

This architecture explains a lot of older InfluxDB advice about series cardinality, TSI sizing, shard groups, and TSM compaction. Do not apply those details mechanically to InfluxDB 3's Parquet engine.

## InfluxDB versus Prometheus

InfluxDB and Prometheus are both time-series systems, but they start from different goals:

- **Prometheus** is an infrastructure and application monitoring system with service discovery, a scrape model, PromQL, rule evaluation, and an alerting ecosystem.
- **InfluxDB** is a more general time-series and event database with typed fields, push ingestion, SQL/InfluxQL, and analytical storage.

| Dimension                      | InfluxDB 3 Core                                                        | Prometheus                                                           |
| ------------------------------ | ---------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Primary purpose                | General time-series and event storage/analytics                        | Systems monitoring and alerting                                      |
| Collection model               | Clients and agents push line protocol                                  | Server discovers and scrapes targets; remote write is also supported |
| Data model                     | Table, tags, multiple typed fields, timestamp                          | Metric name, labels, numeric samples or native histograms            |
| Query language                 | SQL and InfluxQL                                                       | PromQL                                                               |
| Local storage                  | Parquet through a file/object-store abstraction                        | Custom local TSDB with WAL and two-hour blocks                       |
| Long-term storage              | Files can be retained, but Core has a recent-query boundary            | Local retention is single-node; remote storage systems extend it     |
| Cardinality                    | Engine designed for high tag cardinality; wide primary keys still cost | High label cardinality increases memory, index, and storage cost     |
| Joins and relational analytics | SQL supports joins, unions, and window functions                       | PromQL intentionally focuses on time-series vector operations        |
| Alerting                       | Processing Engine plugins and triggers; external integrations          | Recording/alerting rules plus Alertmanager                           |
| Service discovery/exporters    | Usually handled by Telegraf, OpenTelemetry, or application clients     | Major built-in strength, especially in Kubernetes                    |
| Standalone outage behavior     | May depend on its configured object store                              | Each server is intentionally autonomous with local storage           |
| Open-source HA                 | Core is single-node                                                    | Duplicate independent servers; local TSDB itself is not clustered    |

### Choose Prometheus when

- the main problem is monitoring services, hosts, containers, or Kubernetes;
- pull-based health checking and service discovery are advantages;
- PromQL, exporters, recording rules, and Alertmanager fit the operating model;
- the monitoring system should remain useful when other infrastructure is failing;
- samples are primarily numeric metrics rather than general events.

Prometheus's local TSDB is intentionally standalone. Large-scale, durable, multi-cluster, or long-retention deployments normally add a remote system such as Thanos, Mimir, or VictoriaMetrics rather than clustering the Prometheus local store.

### Choose InfluxDB when

- devices or applications naturally push telemetry;
- each timestamp carries several typed fields;
- SQL joins, windows, and familiar analytical tooling matter;
- the workload includes IoT, industrial, financial, energy, or product event data;
- high-cardinality identifiers are an intentional part of the model;
- Parquet and object-store interoperability are valuable.

For InfluxDB 3 Core specifically, verify that a single node and recent-range queries satisfy the requirement. "InfluxDB supports long retention" does not by itself mean Core is optimized for a six-month dashboard query.

## Summary

InfluxDB is not simply "Prometheus with push ingestion." Its current architecture is a general real-time columnar database:

1. Line protocol expresses a table, identifying tags, typed fields, and time.
2. The write path uses memory and a WAL for low latency and durability.
3. Data is persisted as Parquet and queried through Arrow/DataFusion using SQL or InfluxQL.
4. Schema design still matters: tag order, table width, sparsity, field types, and retention are durable choices.
5. InfluxDB 3 Core is open-source and single-node, with a default recent-query boundary of roughly 72 hours.
6. Prometheus remains the stronger default for infrastructure monitoring and alerting; InfluxDB is often stronger for general pushed telemetry and SQL analytics.

## References

- [InfluxDB 3 Core documentation](https://docs.influxdata.com/influxdb3/core/)
- [Choose an InfluxDB 3 product](https://docs.influxdata.com/influxdb3/which-influxdb-3/)
- [InfluxDB 3 Core data durability and write path](https://docs.influxdata.com/influxdb3/core/reference/internals/durability/)
- [InfluxDB 3 schema design recommendations](https://docs.influxdata.com/influxdb3/core/write-data/best-practices/schema-design/)
- [Query InfluxDB 3 Core](https://docs.influxdata.com/influxdb3/core/get-started/query/)
- [InfluxDB 3 Core configuration options](https://docs.influxdata.com/influxdb3/core/reference/config-options/)
- [InfluxDB OSS v2 TSM storage engine](https://docs.influxdata.com/influxdb/v2/reference/internals/storage-engine/)
- [InfluxDB OSS v1.8.5 release](https://github.com/influxdata/influxdb/releases/tag/v1.8.5)
- [InfluxDB v1.8.5 TSM1 write and snapshot engine](https://github.com/influxdata/influxdb/blob/v1.8.5/tsdb/engine/tsm1/engine.go)
- [InfluxDB v1.8.5 WAL implementation](https://github.com/influxdata/influxdb/blob/v1.8.5/tsdb/engine/tsm1/wal.go)
- [InfluxDB v1.8.5 storage defaults](https://github.com/influxdata/influxdb/blob/v1.8.5/tsdb/config.go)
- [InfluxDB v1.8.5 TSI1 design](https://github.com/influxdata/influxdb/blob/v1.8.5/tsdb/index/tsi1/doc.go)
- [InfluxDB v1.8.5 cache and TSM cursor merge](https://github.com/influxdata/influxdb/blob/v1.8.5/tsdb/engine/tsm1/array_cursor_iterator.gen.go)
- [Prometheus overview](https://prometheus.io/docs/introduction/overview/)
- [Prometheus storage](https://prometheus.io/docs/prometheus/latest/storage/)
- [InfluxDB source repository](https://github.com/influxdata/influxdb)
