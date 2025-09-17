---
title: "Vmstorage Study Guide"
date: "2025-09-17T18:16:43+08:00"
tags: ["monitoring", "vm"]
description: "how to study vmstorage implementation"
draft: true
---

## Overview

VictoriaMetrics storage is a highly optimized time series database implementation that serves as a drop-in replacement for Prometheus TSDB with significant performance improvements. This document provides a comprehensive study guide for understanding the vmstorage implementation.

## Architecture Overview

### Core Components

VictoriaMetrics storage consists of several key components working together:

1. **Storage** (`lib/storage/storage.go`) - Main storage interface
2. **Table** (`lib/storage/table.go`) - Manages partitions and data organization
3. **Partition** (`lib/storage/partition.go`) - Time-based data containers
4. **IndexDB** (`lib/storage/index_db.go`) - Index database for metadata
5. **TSID** (`lib/storage/tsid.go`) - Time Series ID structure
6. **Block** (`lib/storage/block.go`) - Individual data blocks

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

#### Block Structure
```go
type Block struct {
    bh            blockHeader
    timestamps    []int64
    values        []int64
    headerData    []byte
    timestampsData []byte
    valuesData    []byte
}
```

Blocks contain up to 8,192 data points for a single time series, optimized for compression and query performance.

## Data Organization

### Partition Strategy
- **Daily Partitions**: Data is organized into daily partitions
- **Part Types**: 
  - Inmemory parts (recent data in RAM)
  - Small parts (recent data on disk)
  - Big parts (historical data on disk)

### Storage Hierarchy
```
Storage
├── Table
│   ├── Partition (daily)
│   │   ├── Inmemory Parts
│   │   ├── Small Parts
│   │   └── Big Parts
│   └── IndexDB
│       ├── MetricName → TSID mapping
│       ├── Tag → MetricID mapping
│       └── MetricID → TSID mapping
```

## Data Flow Architecture

### Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        VICTORIAMETRICS DATA FLOW OVERVIEW                       │
└─────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐    ┌─────────────────┐
                    │   WRITE FLOW    │    │    READ FLOW    │
                    │  (Ingestion)    │    │   (Queries)     │
                    └─────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ HTTP Endpoints  │    │ Query Engine    │
                    │ - Prometheus    │    │ - PromQL        │
                    │ - CSV/JSON      │    │ - MetricsQL     │
                    └─────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Storage.AddRows │    │ Search.Init     │
                    │ - Block process │    │ - TSID resolve  │
                    │ - Memory limit  │    │ - Index lookup  │
                    └─────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Partition Mgmt  │    │ Table Search    │
                    │ - Daily parts   │    │ - Find parts    │
                    │ - Shard distrib │    │ - Create iters  │
                    └─────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Raw Rows Buffer │    │ Block Iterator  │
                    │ - Memory shards │    │ - NextMetricBlock│
                    │ - Auto flush    │    │ - Read headers  │
                    └─────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Background Merge│    │ Data Reading    │
                    │ - Inmemory→Small│    │ - Decompress    │
                    │ - Small→Big     │    │ - Return data   │
                    │ - Compression   │    │                 │
                    └─────────────────┘    └─────────────────┘
                            │                        │
                            ▼                        ▼
                    ┌─────────────────────────────────────────┐
                    │              STORAGE LAYER              │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
                    │  │Inmemory │  │  Small  │  │   Big   │ │
                    │  │  Parts  │  │  Parts  │  │  Parts  │ │
                    │  └─────────┘  └─────────┘  └─────────┘ │
                    │  ┌─────────────────────────────────────┐ │
                    │  │           Index Database            │ │
                    │  │  MetricName→TSID, Tag→MetricID     │ │
                    │  └─────────────────────────────────────┘ │
                    └─────────────────────────────────────────┘
```

### Write Flow (Data Ingestion)

The write flow in VictoriaMetrics follows this path:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           WRITE FLOW DIAGRAM                                │
└─────────────────────────────────────────────────────────────────────────────┘

HTTP Request (Prometheus/CSV/JSON)
           │
           ▼
┌─────────────────────┐
│ API Entry Point     │ ← app/vmstorage/main.go
│ - Data validation   │
│ - Preprocessing     │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Storage.AddRows()   │ ← lib/storage/storage.go:1788
│ - Block processing  │
│ - Memory limiting   │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Storage.add()       │ ← lib/storage/storage.go:1990
│ - MetricRow→rawRow  │
│ - TSID generation   │
│ - Index updates     │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Table.MustAddRows() │ ← lib/storage/table.go:277
│ - Route to partition│
│ - Validate timestamps│
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Partition.AddRows() │ ← lib/storage/partition.go:429
│ - Add to shards     │
│ - Reduce contention │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Raw Rows Processing │ ← lib/storage/partition.go:468
│ - Memory buffering  │
│ - Auto flushing     │
│ - Inmemory parts    │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Background Merging  │ ← lib/storage/merge.go
│ Inmemory → Small    │
│ Small → Big         │
│ Compression         │
└─────────────────────┘
```

**Detailed Steps:**

1. **API Entry Point** (`app/vmstorage/main.go`)
   - HTTP endpoints receive data (Prometheus remote write, CSV, JSON, etc.)
   - Data validation and preprocessing

2. **Storage.AddRows()** (`lib/storage/storage.go:1788`)
   - Main entry point for data ingestion
   - Processes data in blocks to limit memory usage
   - Calls internal `add()` function

3. **Storage.add()** (`lib/storage/storage.go:1990`)
   - Converts MetricRow to rawRow format
   - Generates TSIDs for new time series
   - Updates index databases (idbPrev, idbCurr, idbNext)
   - Handles cardinality limiting and series tracking

4. **Table.MustAddRows()** (`lib/storage/table.go:277`)
   - Routes data to appropriate daily partition
   - Validates timestamp ranges

5. **Partition.AddRows()** (`lib/storage/partition.go:429`)
   - Adds data to rawRowsShards for buffering
   - Distributes load across multiple shards to reduce contention

6. **Raw Rows Processing** (`lib/storage/partition.go:468`)
   - Data buffered in memory shards
   - Automatic flushing when shards reach capacity
   - Conversion to inmemory parts

7. **Background Merging** (`lib/storage/merge.go`)
   - Inmemory parts → Small parts → Big parts
   - Compression and optimization
   - Index updates

### Read Flow (Query Processing)

The read flow follows this path with both cache hit and cache miss scenarios:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    READ FLOW DIAGRAM (Cache Hit & Miss)                     │
└─────────────────────────────────────────────────────────────────────────────┘

Query Request (PromQL/MetricsQL)
           │
           ▼
┌─────────────────────┐
│ Query Initiation    │ ← lib/storage/search.go:155
│ - Search.Init()     │
│ - Validate retention│
│ - Set time range    │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ TSID Resolution     │ ← lib/storage/search.go:194
│ - searchTSIDs()     │
│ - Tag filters → TSIDs│
└─────────────────────┘
           │
           ▼
    ┌─────────────┐
    │ Cache Check │ ← lib/storage/storage.go:1378
    └─────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐   ┌─────────┐
│ CACHE   │   │ CACHE   │
│ HIT     │   │ MISS    │
│ (~1μs)  │   │ (~1-10ms)│
└─────────┘   └─────────┘
    │             │
    ▼             ▼
┌─────────┐   ┌─────────────────────┐
│ Fast    │   │ Index DB Search     │ ← lib/storage/index_db.go:1773
│ Path    │   │ - searchMetricName()│
│ Return  │   │ - MetricID→TSID     │
└─────────┘   │ - Index scan        │
              └─────────────────────┘
                       │
                       ▼
              ┌─────────────────────┐
              │ Fallback Search     │ ← lib/storage/index_db.go:1893
              │ - Previous indexDB  │
              │ - Mergeset scan     │
              │ - Disk I/O          │
              └─────────────────────┘
                       │
                       ▼
              ┌─────────────────────┐
              │ Cache Update        │ ← lib/storage/storage.go:1387
              │ - Store in cache    │
              │ - Future hits       │
              └─────────────────────┘
                       │
                       ▼
              ┌─────────────────────┐
              │ Continue to         │
              │ Table Search        │
              └─────────────────────┘
                       │
                       ▼
┌─────────────────────┐
│ Table Search        │ ← lib/storage/table_search.go
│ - tableSearch.Init()│
│ - Find partitions   │
│ - Create iterators  │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Block Iteration     │ ← lib/storage/search.go:250
│ - NextMetricBlock() │
│ - Read block headers│
│ - Resolve metric IDs│
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Data Reading        │ ← lib/storage/search.go:72
│ - MustReadBlock()   │
│ - Decompress data   │
│ - Return to engine  │
└─────────────────────┘
```

**Detailed Steps:**

1. **Query Initiation** (`lib/storage/search.go:155`)
   - Search.Init() called with tag filters and time range
   - Validates time range against retention policy

2. **TSID Resolution** (`lib/storage/search.go:194`)
   - searchTSIDs() converts tag filters to TSID list
   - Uses index databases to resolve metric names to TSIDs
   - Applies cardinality limits and deadline checks

3. **Table Search** (`lib/storage/table_search.go`)
   - tableSearch.Init() with resolved TSIDs
   - Finds relevant partitions and parts
   - Creates block iterators

4. **Block Iteration** (`lib/storage/search.go:250`)
   - Search.NextMetricBlock() iterates through data blocks
   - Reads block headers and metadata
   - Resolves metric names from MetricIDs

5. **Data Reading** (`lib/storage/search.go:72`)
   - BlockRef.MustReadBlock() reads actual data
   - Decompresses timestamps and values
   - Returns data to query engine

**Cache Miss Scenarios:**

1. **New Time Series**: First time a metric is queried
2. **Cache Eviction**: Memory pressure causes cache cleanup
3. **Index Rotation**: New indexDB created, old cache invalidated
4. **Series Deletion**: Deleted series removed from cache
5. **Cold Start**: System restart, cache empty

**Performance Impact:**

- **Cache Hit**: ~1μs (memory lookup)
- **Cache Miss**: ~1-10ms (disk I/O + index scan)
- **Fallback Search**: ~10-100ms (full index scan)

### Key Data Structures in Flow

#### rawRow (Internal Format)
```go
type rawRow struct {
    TSID          TSID
    Timestamp     int64
    Value         float64
    PrecisionBits uint8
}
```

#### MetricRow (External Format)
```go
type MetricRow struct {
    MetricNameRaw []byte
    Timestamp     int64
    Value         float64
}
```

### Performance Optimizations

1. **Sharding**: Raw rows distributed across multiple shards to reduce lock contention
2. **Batching**: Data processed in blocks to limit memory usage
3. **Caching**: Multiple cache layers for TSIDs, metric names, and index blocks
4. **Compression**: Precision bits and advanced compression algorithms
5. **Background Processing**: Asynchronous merging and index updates

## Key Differences from Prometheus TSDB

| Aspect | Prometheus TSDB | VictoriaMetrics Storage |
|--------|----------------|------------------------|
| **Memory Usage** | Higher footprint | 7x less RAM usage |
| **Storage Efficiency** | Standard compression | 7x less storage space |
| **Indexing** | Single index | Multi-level (per-day + global) |
| **Compression** | Standard | Advanced with precision bits |
| **Architecture** | Monolithic | Modular components |
| **Performance** | Good | 20x better ingestion |

## Learning Path

### Phase 1: Core Data Structures (Start Here)

1. **TSID Implementation** (`lib/storage/tsid.go`)
   - Understanding time series identification
   - Hierarchical ID structure
   - Marshaling/unmarshaling

2. **Block Structure** (`lib/storage/block.go`)
   - Data point storage format
   - Compression mechanisms
   - Block operations

3. **Partition Management** (`lib/storage/partition.go`)
   - Time-based data organization
   - Part lifecycle management
   - Merge operations

### Phase 2: Data Flow and Operations

4. **Main Storage Interface** (`lib/storage/storage.go`)
   - Storage initialization
   - Data ingestion API
   - Query operations

5. **Table Operations** (`lib/storage/table.go`)
   - Partition management
   - Background processes
   - Retention handling

6. **vmstorage Main** (`app/vmstorage/main.go`)
   - HTTP API endpoints
   - Configuration management
   - Metrics exposure

### Phase 3: Advanced Features

7. **Index Database** (`lib/storage/index_db.go`)
   - Metadata indexing
   - Search optimization
   - Index rotation

8. **Search System** (`lib/storage/search.go`)
   - Query processing
   - Tag filtering
   - Time range queries

9. **Background Processes**
   - Merge operations (`lib/storage/merge.go`)
   - Deduplication (`lib/storage/dedup.go`)
   - Compression (`lib/storage/encoding/`)

## Key Concepts to Master

### 1. Time Series Identification
- How TSIDs are generated and used
- Relationship between metric names and TSIDs
- Hierarchical grouping benefits

### 2. Data Compression
- Precision bits for value compression
- Timestamp compression techniques
- Block-level optimization

### 3. Index Strategy
- Per-day indexing vs global indexing
- Memory usage optimization
- Search performance trade-offs

### 4. Background Operations
- Merge strategies (inmemory → small → big)
- Deduplication processes
- Retention management

## Performance Characteristics

### Memory Efficiency
- **7x less RAM** than Prometheus
- Optimized caching strategies
- Efficient data structures

### Storage Efficiency
- **7x less disk space** than Prometheus
- Advanced compression algorithms
- Precision-based value storage

### Query Performance
- Optimized index structures
- Efficient time range queries
- Fast tag filtering

## Configuration and Tuning

### Key Configuration Options
```bash
# Storage paths
-storageDataPath=/path/to/data

# Retention settings
-retentionPeriod=1y

# Memory limits
-storage.minFreeDiskSpaceBytes=10MB

# Cache tuning
-storage.cacheSizeStorageTSID=0
-storage.cacheSizeStorageMetricName=0

# Index optimization
-disablePerDayIndex=false
```

### Performance Tuning
- Cache size configuration
- Merge concurrency settings
- Precision bits adjustment
- Retention policy optimization

## API Endpoints

### Data Ingestion
- `/api/v1/import/prometheus` - Prometheus remote write
- `/api/v1/import/csv` - CSV data import
- `/api/v1/import/json` - JSON line format

### Query Operations
- `/api/v1/query` - Instant queries
- `/api/v1/query_range` - Range queries
- `/api/v1/series` - Series discovery

### Management
- `/snapshot/create` - Create snapshots
- `/internal/force_merge` - Force merge
- `/internal/force_flush` - Force flush

## Monitoring and Metrics

### Key Metrics to Monitor
- `vm_rows_received_total` - Ingested data points
- `vm_rows_added_to_storage_total` - Successfully stored
- `vm_active_merges` - Background merge activity
- `vm_cache_*` - Cache performance metrics
- `vm_free_disk_space_bytes` - Storage capacity

### Health Checks
- Disk space monitoring
- Memory usage tracking
- Query performance metrics
- Background process health

## Best Practices

### Deployment
1. Use SSD storage for better performance
2. Configure appropriate retention periods
3. Monitor disk space and memory usage
4. Set up proper backup strategies

### Performance Optimization
1. Tune cache sizes based on workload
2. Adjust precision bits for your data
3. Configure merge concurrency appropriately
4. Use per-day indexing for high churn scenarios

### Maintenance
1. Regular snapshot creation
2. Monitor background merge processes
3. Clean up old snapshots
4. Monitor cardinality limits

## Troubleshooting Common Issues

### High Memory Usage
- Check cache configuration
- Monitor cardinality growth
- Review precision bits settings

### Slow Queries
- Verify index configuration
- Check cache hit rates
- Review query patterns

### Storage Issues
- Monitor disk space
- Check retention settings
- Verify merge processes

## Advanced Topics

### Custom Compression
- Understanding precision bits
- Value encoding strategies
- Timestamp compression

### Index Optimization
- Per-day vs global indexing
- Memory usage trade-offs
- Search performance tuning

### Cluster Considerations
- Data distribution strategies
- Replication mechanisms
- Load balancing approaches

## Resources for Further Study

### Documentation
- [VictoriaMetrics Documentation](https://docs.victoriametrics.com/)
- [Storage Architecture Guide](https://docs.victoriametrics.com/victoriametrics/storage/)
- [Performance Tuning](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/#performance-tuning)

### Code References
- `lib/storage/` - Core storage implementation
- `app/vmstorage/` - Storage service implementation
- `lib/encoding/` - Compression and encoding utilities

### Benchmarks and Comparisons
- [VictoriaMetrics vs Prometheus](https://valyala.medium.com/prometheus-vs-victoriametrics-benchmark-on-node-exporter-metrics-4ca29c75590f)
- [Storage Efficiency Studies](https://medium.com/@valyala/when-size-matters-benchmarking-victoriametrics-vs-timescale-and-influxdb-6035811952d4)

## Conclusion

VictoriaMetrics storage represents a significant advancement over traditional TSDB implementations, offering superior performance, efficiency, and scalability. The modular architecture makes it easier to understand and maintain, while the advanced compression and indexing strategies provide substantial benefits for large-scale deployments.

Understanding the core concepts of TSID structure, partition management, and background operations is essential for effective use and optimization of VictoriaMetrics storage.
