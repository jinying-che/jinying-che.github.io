---
title: "vmstorage"
date: "2025-09-17T18:16:43+08:00"
tags: ["monitor", "victoriametrics"]
description: "how to study vmstorage implementation"
---

## Overview

VictoriaMetrics storage is a highly optimized time series database implementation that serves as a drop-in replacement for Prometheus TSDB with significant performance improvements. This document provides a comprehensive study guide for understanding the vmstorage implementation.

## Architecture Overview
TBD
## Data Model
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

### Data Structure to Disk Mapping 
Understand the table, partition, part and block hierarchy and how they map to the on-disk structure.
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
│  data/small/2024_07/<part_id>/                                                                                  │
│  ├── metadata.json ──────► { "RowsCount": 94057, "BlocksCount": 767, "MinTimestamp": ..., "MaxTimestamp": ... } │
│  ├── metaindex.bin ──────► Index of index.bin (small, loaded in memory)                                         │
│  ├── index.bin ──────────► Contains ALL blockHeaders (767 headers in this example)                              │
│  │                         ┌─────────────┬─────────────┬─────────────┬─────────────┬─────┐                      │
│  │                         │ blockHdr[0] │ blockHdr[1] │ blockHdr[2] │ blockHdr[3] │ ... │ (767 total)          │
│  │                         └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────┘                      │
│  │                                │             │             │             │                                   │
│  │                                ▼             ▼             ▼             ▼                                   │
│  ├── timestamps.bin ─────► ┌───────────┬───────────┬───────────┬───────────┐                                    │
│  │                         │  ts[0]    │  ts[1]    │  ts[2]    │  ts[3]    │ ...  (compressed timestamp data)   │
│  │                         │ ≤8192 ts  │ ≤8192 ts  │ ≤8192 ts  │ ≤8192 ts  │                                    │
│  │                         └───────────┴───────────┴───────────┴───────────┘                                    │
│  │                                │             │             │                                                 │
│  │                                ▼             ▼             ▼                                                 │
│  └── values.bin ─────────► ┌───────────┬───────────┬───────────┬───────────┐                                    │
│                            │  val[0]   │  val[1]   │  val[2]   │  val[3]   │ ...   (compressed value data)      │
│                            │ ≤8192 val │ ≤8192 val │ ≤8192 val │ ≤8192 val │                                    │
│                            └───────────┴───────────┴───────────┴───────────┘                                    │
│                                  │             │             │             │                                    │
│                                  ▼             ▼             ▼             ▼                                    │
│                            ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐                              │
│                            │  BLOCK 0  │ │  BLOCK 1  │ │  BLOCK 2  │ │  BLOCK 3  │  ...  (767 blocks total)     │
│                            └───────────┘ └───────────┘ └───────────┘ └───────────┘                              │
│  ════════════════════════════════════════════════════════════════════════════════════════════════════════════   │
│  KEY INSIGHT:                                                                                                   │
│  • One BLOCK = blockHeader + timestamps chunk + values chunk (all for ONE TSID, up to 8192 data points)         │
│  • One PART  = Many BLOCKs stored across 3 files (index.bin, timestamps.bin, values.bin)                        │
│  • Blocks are sorted by TSID within a part                                                                      │
│  • Same TSID can have multiple blocks (if more than 8192 points)                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### LSM Tree
There are TWO separate LSM trees in VictoriaMetrics:
- indexDB uses mergeset.Table (LSM tree for inverted index)
  - Location: indexdb/<generation>/
  - Tiers: inmemoryParts → fileParts
- Each partition has its own LSM tree (for time-series data)
  - Location: data/{small,big}/YYYY_MM/
  - Tiers: inmemoryParts → smallParts → bigParts

### Key Data Structures

#### TSID (Time Series ID)
The TSID provides hierarchical identification of time series, enabling efficient grouping and compression.

##### TSID vs MetricID
- MetricID is for identification which is a unique identifier of a time series. (MetricID = `uint64(time.Now().UnixNano()) + 1`)
- TSID (including MetricID) is for sorting and grouping (has more fields)
    ```go
    type TSID struct {
        MetricGroupID uint64  // ID of metric group (e.g., "memory_usage")
        JobID         uint32  // ID of job/service
        InstanceID    uint32  // ID of instance/process
        MetricID      uint64  // Unique ID of the metric
    }
    ```
#### IndexDB
1. The indexDB provides inverted index functionality for **time series metadata**. It enables fast lookups from metric names/labels to time series IDs (TSIDs)
2. indexDB uses mergeset.Table (LSM tree for inverted index) as mentioned above
3. see `createGlobalIndexes` function for details
  ```go
  type indexDB struct {
  	name string
  	tb   *mergeset.Table
  
  	s *Storage
  
  	// Cache for fast TagFilters -> MetricIDs lookup.
  	tagFiltersToMetricIDsCache *lrucache.Cache
  
  	// Cache for (date, tagFilter) -> loopsCount, which is used for reducing
  	// the amount of work when matching a set of filters.
  	loopsPerDateTagFilterCache *lrucache.Cache
  
  	// A cache that stores metricIDs that have been added to the index.
  	// The cache is not populated on startup nor does it store a complete set of
  	// metricIDs. A metricID is added to the cache either when a new entry is
  	// added to the global index or when the global index is searched for
  	// existing metricID (see is.createGlobalIndexes() and is.hasMetricID()).
  	//
  	// The cache is used solely for creating new index entries during the data
  	// ingestion (see Storage.RegisterMetricNames() and Storage.add())
  	metricIDCache *metricIDCache
      // ...
  }
  ```
| Name | Purpose |
|------|---------|
| `MetricName → TSID` | Global metric name lookup (disabled by default) |
| `Tag → MetricIDs` | Global inverted index for tag filters |
| `MetricID → TSID` | Lookup TSID by MetricID |
| `MetricID → MetricName` | Lookup full metric name by MetricID |
| `DeletedMetricID` | Track deleted metrics |
| `Date → MetricID` | Per-day metric existence tracking |
| `(Date,Tag) → MetricIDs` | **Per-day inverted index** (main query path) |
| `(Date,MetricName) → TSID` | Per-day metric name to TSID lookup |```

### Write Path

### Read Path

