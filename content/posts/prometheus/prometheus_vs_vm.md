---
title: "Prometheus vs VictoriaMetrics: TSDB System Design Deep Dive"
date: "2026-03-14T08:38:26+08:00"
tags: ["tsdb", "prometheus", "victoriametrics"]
description: "A deep comparison of Prometheus TSDB and VictoriaMetrics storage engine design — architecture, write/read path, compression, and the problems VM solves."
draft: true
---

## Overview

Both Prometheus and VictoriaMetrics (VM) are time-series databases (TSDB) built for monitoring and metrics. But they take fundamentally different architectural approaches.

This post compares their **storage engine designs** side by side, focusing on:
- What problems exist in Prometheus TSDB
- How VictoriaMetrics solves them
- The trade-offs each design makes

## Data Model

Both share the same logical data model:

```
Series  = metric name + label set
Sample  = (timestamp int64, value float64)

Example:
  cpu_usage{host="web01", region="us-east"}  →  [(t1, 0.82), (t2, 0.85), ...]
```

The difference is **how they store and index** this data on disk.

---

## Architecture at a Glance

### Prometheus TSDB

```
Write Path:
  scrape → WAL (fsync) → Head Block (in-memory, mutable)
                              │
                              │  every 2 hours
                              ▼
                        Persistent Block (immutable, on disk)
                              │
                              │  compaction
                              ▼
                        Merged Larger Block

Block layout:
  block-ulid/
  ├── meta.json        # time range [mint, maxt], stats
  ├── chunks/
  │   └── 000001       # gorilla-encoded chunk data
  ├── index            # label index + postings (inverted index)
  └── tombstones       # soft-deleted ranges
```

- Each block is **self-contained**: has its own index + chunks
- Blocks are **immutable** once flushed
- Head block holds last **1-3 hours** in memory

### VictoriaMetrics

```
Write Path:
  ingest → RAM buffer (in-memory parts)
                │
                │  every 1-5 seconds
                ▼
          Small Part (compressed, on disk, fsync)
                │
                │  background merge
                ▼
          Big Part (merged, compressed)

Data layout:
  data/
  ├── indexdb/            # persistent inverted index (label → TSID)
  │   └── <partition>/
  └── data/
      └── <YYYY_MM>/     # per-month partition
          ├── small/      # recently flushed parts
          └── big/        # merged parts
              └── <part>/
                  ├── timestamps.bin   # column: timestamps
                  ├── values.bin       # column: values
                  ├── metaindex.bin    # part metadata
                  └── index.bin        # TSID → offset
```

- Data is **column-oriented** (timestamps and values stored separately)
- Organized by **monthly partitions**, not fixed time-range blocks
- **No WAL** — relies on frequent small flushes with fsync

---

## Write Path

### Prometheus

```
sample arrives
     │
     ▼
┌─────────┐   fsync    ┌──────┐
│   WAL   │ ─────────► │ Disk │   durability guarantee
└────┬────┘            └──────┘
     │
     ▼
┌───────────┐
│ Head Block │  in-memory, mutable
│ (1-3 hrs)  │  samples stored as compressed chunks (up to 120 samples/chunk)
└─────┬─────┘
      │  every 2 hours (chunkRange)
      ▼
┌───────────┐
│ Persisted │  immutable block on disk
│   Block   │  includes: chunks/ + index + meta.json
└───────────┘
```

**Double-write cost**: every sample is written to WAL first (for crash recovery), then to the head block. The WAL is replayed on restart to rebuild the head block.

### VictoriaMetrics

```
sample arrives
     │
     ▼
┌──────────────┐
│  RAM Buffer  │  in-memory parts (inmemoryPart)
│  (buffered)  │
└──────┬───────┘
       │  every 1-5 seconds
       ▼
┌──────────────┐
│  Small Part  │  compressed (~50KB), fsync to disk
│  (on disk)   │  immediately durable
└──────┬───────┘
       │  background merge
       ▼
┌──────────────┐
│   Big Part   │  merged from multiple small parts
│  (on disk)   │
└──────────────┘
```

**No WAL needed**: because data is flushed to disk every few seconds (compressed + fsync), crash recovery simply reads the persisted parts. Trade-off: up to ~5 seconds of data loss on crash — acceptable for metrics.

### Comparison

| Aspect | Prometheus | VictoriaMetrics |
|---|---|---|
| Durability mechanism | WAL (write-ahead log) | Frequent fsync of compressed parts |
| Write amplification | 2x (WAL + head) | ~1x (RAM → disk) |
| Flush frequency | Every 2 hours | Every 1-5 seconds |
| Flush size | ~2MB (full block) | ~50KB (small compressed part) |
| Max data loss on crash | 0 (WAL replayed) | ~5 seconds |

---

## Read Path

### Prometheus

```
Query: cpu_usage{host="web01"} [last 6h]
                    │
                    ▼
        ┌───────────────────────┐
        │  For EACH block that  │  must check all blocks
        │  overlaps [now-6h,now]│  overlapping the time range
        └───────────┬───────────┘
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│  Head   │   │ Block A │   │ Block B │
│ (mem)   │   │ (0-2h)  │   │ (2-4h)  │
├─────────┤   ├─────────┤   ├─────────┤
│ label   │   │ label   │   │ label   │  ← each block has
│ index   │   │ index   │   │ index   │    its own index
│ lookup  │   │ lookup  │   │ lookup  │
├─────────┤   ├─────────┤   ├─────────┤
│ chunk   │   │ chunk   │   │ chunk   │
│ decode  │   │ decode  │   │ decode  │
└────┬────┘   └────┬────┘   └────┬────┘
     │              │              │
     └──────────────┼──────────────┘
                    ▼
            ┌──────────────┐
            │  Merge Sort  │  merge by timestamp
            └──────────────┘
```

**Problem**: label → series resolution is done **per block**. A 24h query over 2h blocks requires **12 separate index lookups**.

### VictoriaMetrics

```
Query: cpu_usage{host="web01"} [last 6h]
                    │
                    ▼
        ┌───────────────────────┐
        │    Global IndexDB     │  persistent, shared across all data
        │  label → TSID = 42   │  ONE lookup (often cached)
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Monthly Partition    │  2026-03
        │  find parts with      │  binary search by time range
        │  TSID=42 in range    │
        └───────────┬───────────┘
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│ Part A  │   │ Part B  │   │ Part C  │
│ (small) │   │ (small) │   │ (big)   │
├─────────┤   ├─────────┤   ├─────────┤
│ scan    │   │ scan    │   │ scan    │  column-oriented:
│ ts col  │   │ ts col  │   │ ts col  │  read only the columns
│ val col │   │ val col │   │ val col │  you need
└────┬────┘   └────┬────┘   └────┬────┘
     │              │              │
     └──────────────┼──────────────┘
                    ▼
               ┌────────┐
               │ Merge  │
               └────────┘
```

**Key advantage**: label resolution happens **once** in the global IndexDB, then data access uses the compact integer TSID.

### Comparison

| Aspect | Prometheus | VictoriaMetrics |
|---|---|---|
| Index | Per-block, in-memory | Global, persistent on disk |
| Series resolution | O(num_blocks) lookups | O(1) TSID lookup (cached) |
| Data layout | Row-oriented (ts+val interleaved) | Column-oriented (ts and val separate) |
| Aggregation scan | Must load values even if only counting | Can scan timestamp column only |
| Startup index cost | Rebuild from WAL (slow!) | Already on disk (instant) |

---

## Compression

### Prometheus: Gorilla Encoding

Based on Facebook's [Gorilla paper (VLDB 2015)](https://www.vldb.org/pvldb/vol8/p1816-teller.pdf).

**Timestamps** — delta-of-delta:
```
raw:              1000, 1010, 1020, 1030
deltas:                 10,   10,   10
delta-of-deltas:         0,    0        ← mostly zeros → 1 bit each
```

**Values** — XOR encoding:
```
v0 = 3.14159  (binary: 0100000000001001001000011111101...)
v1 = 3.14160  (binary: 0100000000001001001000011111110...)
XOR(v0, v1) =          0000000000000000000000000000011...
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                        mostly zeros → encode only the diff bits
```

Result: **~1.37 bytes/sample**

### VictoriaMetrics: Enhanced Compression

VM improves on Gorilla with a two-stage pipeline:

```
Stage 1: Domain-specific encoding
  ┌─────────────────────────────────────────┐
  │ • Float → Integer conversion            │
  │   (multiply by 10^X to remove decimals) │
  │ • Delta encoding for counters           │
  │ • Near-constant detection               │
  │   (if values barely change, encode as   │
  │    base + small diffs)                   │
  └──────────────┬──────────────────────────┘
                 │  low-entropy integer stream
                 ▼
Stage 2: General-purpose compression
  ┌─────────────────────────────────────────┐
  │ • ZSTD compression                      │
  │   (excellent at compressing patterns    │
  │    and low-entropy data)                │
  └─────────────────────────────────────────┘
```

Result: **~0.4 bytes/sample** (3.4x better than Gorilla)

### Why VM Compresses Better

| Technique | Gorilla | VM |
|---|---|---|
| Timestamp encoding | Delta-of-delta + bit packing | Delta encoding + ZSTD |
| Value encoding | XOR + leading/trailing zero packing | Float→Int conversion + Delta + ZSTD |
| Cross-sample patterns | Not exploited | ZSTD finds repeated patterns across samples |
| Compression ratio | ~1.37 bytes/sample | ~0.4 bytes/sample |

The key insight: Gorilla operates **sample-by-sample** (local compression), while VM's ZSTD pass operates on **blocks of samples** (global compression), catching patterns that Gorilla misses.

---

## Compaction

### Prometheus: Block Compaction

```
Time:   0h    2h    4h    6h    8h
        ├─────┤─────┤─────┤─────┤
        │ B1  │ B2  │ B3  │ B4  │   Level 0: 2-hour blocks

Compact (B1 + B2 → B5):
        ├───────────┤─────┤─────┤
        │    B5     │ B3  │ B4  │   Level 1: 4-hour block

Compact (B5 + B3 + B4 → B6):
        ├─────────────────────────┤
        │           B6            │   Level 2: 8-hour block
```

**Problems**:
- Compaction is **triggered every 2 hours** → CPU/memory spikes at predictable intervals
- Large blocks mean large compaction jobs → higher peak resource usage
- During compaction, both old and new blocks exist → temporary **2x disk usage**

### VictoriaMetrics: MergeTree-style

```
Incoming:  [p1] [p2] [p3] [p4] [p5] [p6] ...   small parts (flushed every 1-5s)
               │         │
               ▼         ▼
Merge:    [  p1+p2+p3  ] [  p4+p5+p6  ]          medium parts
                    │
                    ▼
Merge:    [    p1+p2+p3+p4+p5+p6     ]           big part
```

- Merges happen **continuously** in the background — no 2-hour spikes
- Small parts (~50KB) merge cheaply
- Merges are scoped to a **monthly partition** — independent, parallelizable
- Resource usage is **smooth and predictable**

### Comparison

| Aspect | Prometheus | VictoriaMetrics |
|---|---|---|
| Trigger | Every 2 hours | Continuous background |
| Resource pattern | Spiky (2h intervals) | Smooth |
| Scope | Cross-block merge | Per-partition merge |
| Temporary disk overhead | 2x during compaction | Minimal (small parts) |

---

## The Five Problems VM Solves

### 1. WAL Replay: Slow & Dangerous Restarts

**Prometheus problem**: On restart, Prometheus must replay the entire WAL to rebuild the head block.

```
Startup sequence:
  1. Load WAL segments from disk (could be thousands)
  2. Replay each segment to rebuild in-memory head block
  3. Only then: ready to accept queries

Real-world pain:
  - WAL replay can take 30min - 3+ hours for large instances
  - Replay uses 2-3x normal memory → OOM kills during restart
  - Example: 30Gi steady-state → 50+Gi during replay → OOMKilled
  - 4,415 WAL segments × ~3s each ≈ 3.7 hours to start
```

**VM solution**: No WAL. All data is persisted as compressed parts. Startup reads existing parts — **instant recovery**, no replay needed.

### 2. Memory Usage: Head Block is Expensive

**Prometheus problem**: The head block keeps **all active series** and their recent chunks in memory.

```
Memory breakdown:
  - Each active series: index entry + chunk buffer + labels
  - 1M active series: ~6.5 GB RAM
  - 10M active series: ~14 GB RAM
  - High cardinality explosion: 200+ GB → OOMKilled
```

**VM solution**: Data is flushed to disk every 1-5 seconds. The RAM buffer is small (~50KB flushes). VM uses **~850MB for 1M series** vs Prometheus' **~6.5GB** — roughly **7x less RAM**.

### 3. High Cardinality: Index Doesn't Scale

**Prometheus problem**: The inverted index lives entirely in memory. Series churn (e.g., Kubernetes pod restarts creating new label combinations) constantly grows the index.

```
Series churn example (rolling deployment):
  cpu{pod="app-v1-abc"} → dies
  cpu{pod="app-v1-def"} → dies
  cpu{pod="app-v2-xyz"} → new
  cpu{pod="app-v2-uvw"} → new

Each unique label combination = new series in the index.
Index grows unbounded until head block GC runs (every 2h).
```

**VM solution**:
- Persistent IndexDB on disk — not limited by RAM
- TSID-based design — compact integer IDs instead of full label sets in memory
- Per-month index partitions — old index data is naturally garbage collected

### 4. Compaction Spikes: Predictable Resource Storms

**Prometheus problem**: Every 2 hours, compaction + WAL truncation causes resource spikes.

```
Resource usage over time:
  Normal:      ████████░░░░░░░░████████░░░░░░░░████████
  Compaction:  ████████████████████████████████████████████  ← spike!
               ^              ^              ^
               2h mark        4h mark        6h mark

Impact:
  - CPU spike during compaction
  - Memory spike (must read + merge + rewrite blocks)
  - Disk I/O spike
  - Query latency increase during compaction
```

**VM solution**: MergeTree-style continuous background merges. Small parts merge frequently with minimal overhead. **No periodic spikes**, smooth resource consumption.

### 5. Storage Efficiency: 3.4x More Disk

**Prometheus problem**: Gorilla encoding achieves ~1.37 bytes/sample. For long retention (months/years), disk costs add up.

```
Example: 1M active series, 15s scrape interval, 1 year retention
  Prometheus:  1M × (365 × 24 × 3600 / 15) × 1.37 bytes ≈ 2.88 TB
  VM:          1M × (365 × 24 × 3600 / 15) × 0.4 bytes  ≈ 0.84 TB
                                                            ────────
                                                            Saves ~2 TB
```

**VM solution**: Two-stage compression (domain encoding + ZSTD) achieves ~0.4 bytes/sample.

---

## Design Trade-off Summary

```
                    Prometheus              VictoriaMetrics
                    ──────────              ───────────────
Durability:         Strict (WAL, 0 loss)    Relaxed (~5s loss ok)
                         │                        │
                         │                        │
                         ▼                        ▼
Complexity:         Higher write path        Higher storage format
                    (WAL + replay logic)     (column-oriented + IndexDB)
                         │                        │
                         │                        │
                         ▼                        ▼
Optimized for:      Correctness first        Performance first
                    Single-node simplicity   Scale + efficiency
```

| Dimension | Prometheus | VictoriaMetrics | Winner |
|---|---|---|---|
| **Simplicity** | Easier to understand block model | More moving parts (IndexDB, partitions, column files) | Prometheus |
| **Durability** | Zero data loss (WAL) | ~5s data loss acceptable | Prometheus |
| **Memory** | 6.5GB / 1M series | 850MB / 1M series | VM (7x) |
| **Compression** | 1.37 bytes/sample | 0.4 bytes/sample | VM (3.4x) |
| **Startup time** | Minutes to hours (WAL replay) | Seconds (read existing parts) | VM |
| **Resource pattern** | Spiky (2h compaction) | Smooth (continuous merge) | VM |
| **High cardinality** | Degrades badly (in-memory index) | Handles well (persistent IndexDB) | VM |
| **Ecosystem** | Massive, de facto standard | Compatible, growing | Prometheus |
| **Clustering** | Needs Thanos/Cortex | Built-in (vminsert/vmselect/vmstorage) | VM |

---

## References

- [Gorilla: A Fast, Scalable, In-Memory Time Series Database (Facebook, VLDB 2015)](https://www.vldb.org/pvldb/vol8/p1816-teller.pdf)
- [Writing a Time Series Database from Scratch — Fabian Reinartz](https://wiert.me/2020/02/20/writing-a-time-series-database-from-scratch-fabian-reinartz/)
- [Prometheus TSDB: The Head Block — Ganesh Vernekar](https://ganeshvernekar.com/blog/prometheus-tsdb-the-head-block/)
- [Prometheus TSDB: WAL and Checkpoint — Ganesh Vernekar](https://ganeshvernekar.com/blog/prometheus-tsdb-wal-and-checkpoint/)
- [VictoriaMetrics: Achieving Better Compression than Gorilla](https://faun.pub/victoriametrics-achieving-better-compression-for-time-series-data-than-gorilla-317bc1f95932)
- [VictoriaMetrics Architecture — DeepWiki](https://deepwiki.com/ntk148v/til/3.8-victoriametrics-time-series-database)
- [Prometheus vs VictoriaMetrics — Last9](https://last9.io/blog/prometheus-vs-victoriametrics/)
- [Prometheus WAL Replay: Slow Startups — Michal Drozd](https://www.michal-drozd.com/en/blog/prometheus-wal-replay-slow-startup/)
- [High Cardinality TSDB Benchmarks — Aliaksandr Valialkin](https://valyala.medium.com/high-cardinality-tsdb-benchmarks-victoriametrics-vs-timescaledb-vs-influxdb-13e6ee64dd6b)
- [Prometheus Memory Consumption Optimization — Palark](https://palark.com/blog/prometheus-resource-consumption-optimization/)
