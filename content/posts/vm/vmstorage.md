---
title: "vmstorage"
date: "2025-09-17T18:16:43+08:00"
tags: ["monitor", "victoriametrics"]
description: "how to study vmstorage implementation"
---

## Overview

VictoriaMetrics storage is a highly optimized time series database implementation that serves as a drop-in replacement for Prometheus TSDB with significant performance improvements. This document provides a comprehensive study guide for understanding the vmstorage implementation.

## Architecture Overview

### Core Components
VictoriaMetrics storage consists of several key components working together:

| Concept | Purpose |
|---------|---------|
| MetricName | True identifier: `cpu{host="x"}`, global scope, the rest are all node scope |
| MetricID | uint64, the unique id of the metric (time series) |
| TSID | object, also the unique id for a time series, has more fields for sorting purpose |
| indexDB | Inverted index: labels → MetricIDs |
| table | Container for monthly partitions, LSM implementation |
| partition | One month of data with 3-tier LSM |
| part | One day of data, contains multiple blocks |
| Block | ~8K points for one TSID, compressed |

#### TSID vs MetricID

#### Data Structure to Disk Mapping 
Understand the table, partition, part, block hierarchy and how they map to the on-disk structure.
```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Data Structure → Disk Mapping                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Storage                           vmstorage-data/                         │
│  ├── idbCurr (indexDB)      ───►   ├── indexdb/<generation>/               │
│  │   └── tb (mergeset.Table)       │   ├── parts.json                      │
│  │       └── fileParts[]           │   └── <part>/ (items.bin, etc.)       │
│  │                                                                         │
│  └── tb (table)             ───►   └── data/                               │
│      └── ptws[] (partitions)           ├── small/                          │
│          └── partition "2024_07"       │   └── 2024_07/                    │
│              ├── smallParts[]    ───►  │       ├── parts.json              │
│              │   └── part              │       └── <part>/                 │
│              │       ├── metaindex     │           ├── metaindex.bin       │
│              │       ├── indexFile     │           ├── index.bin           │
│              │       ├── timestamps    │           ├── timestamps.bin      │
│              │       └── values        │           └── values.bin          │
│              │                                                             │
│              └── bigParts[]      ───►  └── big/                            │
│                  └── part                  └── 2024_07/                    │
│                      └── ...                   └── <part>/                 │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                                 │
│  ONE PART = One Directory with 5 Files                                                                          │
│  ══════════════════════════════════════                                                                         │
│  data/small/2024_07/<part_id>/                                                                                  │
│  ├── metadata.json ──────► { "RowsCount": 94057, "BlocksCount": 767, "MinTimestamp": ..., "MaxTimestamp": ... } │
│  ├── metaindex.bin ──────► Index of index.bin (small, loaded in memory)                                         │
│  ├── index.bin ──────────► Contains ALL blockHeaders (767 headers in this example)                              │
│  │                         ┌─────────────┬─────────────┬─────────────┬─────────────┬─────┐                      │
│  │                         │ blockHdr[0] │ blockHdr[1] │ blockHdr[2] │ blockHdr[3] │ ... │ (767 total)          │
│  │                         └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────┘                      │
│  │                                │             │             │             │                                   │
│  │                         Each blockHeader contains:                                                           │
│  │                         • TSID (which time series)                                                           │
│  │                         • MinTimestamp, MaxTimestamp                                                         │
│  │                         • RowsCount (≤8192)                                                                  │
│  │                         • TimestampsBlockOffset, TimestampsBlockSize  ──────┐                                │
│  │                         • ValuesBlockOffset, ValuesBlockSize  ──────────────┼──┐                             │
│  │                                │             │             │             │  │  │                             │
│  │                                ▼             ▼             ▼             ▼  │  │                             │
│  ├── timestamps.bin ─────► ┌───────────┬───────────┬───────────┬───────────┐◄─┘  │                              │
│  │                         │  ts[0]    │  ts[1]    │  ts[2]    │  ts[3]    │ ... │ (compressed timestamp data)  │
│  │                         │ ≤8192 ts  │ ≤8192 ts  │ ≤8192 ts  │ ≤8192 ts  │     │                              │
│  │                         └───────────┴───────────┴───────────┴───────────┘     │                              │
│  │                                │             │             │             │     │                             │
│  │                                ▼             ▼             ▼             ▼     │                             │
│  └── values.bin ─────────► ┌───────────┬───────────┬───────────┬───────────┐◄────┘                              │
│                            │  val[0]   │  val[1]   │  val[2]   │  val[3]   │ ...   (compressed value data)      │
│                            │ ≤8192 val │ ≤8192 val │ ≤8192 val │ ≤8192 val │                                    │
│                            └───────────┴───────────┴───────────┴───────────┘                                    │
│                                  │             │             │             │                                    │
│                                  ▼             ▼             ▼             ▼                                    │
│                            ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐                              │
│                            │  BLOCK 0  │ │  BLOCK 1  │ │  BLOCK 2  │ │  BLOCK 3  │  ...  (767 blocks total)     │
│                            │           │ │           │ │           │ │           │                              │
│                            │  TSID: A  │ │  TSID: A  │ │  TSID: B  │ │  TSID: C  │                              │
│                            │  1000 pts │ │  8192 pts │ │  5000 pts │ │  8192 pts │                              │
│                            └───────────┘ └───────────┘ └───────────┘ └───────────┘                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════════   │
│  KEY INSIGHT:                                                                                                   │
│  • One BLOCK = blockHeader + timestamps chunk + values chunk (all for ONE TSID, up to 8192 data points)         │
│  • One PART  = Many BLOCKs stored across 3 files (index.bin, timestamps.bin, values.bin)                        │
│  • Blocks are sorted by TSID within a part                                                                      │
│  • Same TSID can have multiple blocks (if more than 8192 points)                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### LSM Tree
There are TWO separate LSM trees in VictoriaMetrics:
1. indexDB uses mergeset.Table (LSM tree for inverted index)
  - Location: indexdb/<generation>/
  - Tiers: inmemoryParts → fileParts
2. Each partition has its own LSM tree (for time-series data)
  - Location: data/{small,big}/YYYY_MM/
  - Tiers: inmemoryParts → smallParts → bigParts

### Key Data Structures

#### TSID (Time Series ID)
```go
type TSID struct {
    MetricGroupID uint64  // ID of metric group (e.g., "memory_usage")
    JobID         uint32  // ID of job/service
    InstanceID    uint32  // ID of instance/process
    MetricID      uint64  // Unique ID of the metric
}
```

The TSID provides hierarchical identification of time series, enabling efficient grouping and compression.

