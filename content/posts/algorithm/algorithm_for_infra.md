---
title: "The Most Important Algorithm For Infrastructure"
date: "2026-02-22T18:02:21+08:00"
tags: ["algorithm", "infra"]
description: "Are you wondering the most important and popular algorithm used in infrastructure systems, e.g. Kubernetes, Prometheus, etcd, Elasticsearch, VictoriaMetrics etc."
draft: true
---

## Observability — Metrics, Logs & Tracing

| Component | Key Data Structure / Algorithm | Purpose |
| :--- | :--- | :--- |
| **Metrics Storage (TSDB)** | **LSM-Trees (Log-Structured Merge-Trees)** | Optimized for high-throughput sequential writes by buffering in memory and flushing to sorted disk files. |
| **Data Compression** | **Delta-of-Delta / Gorilla Encoding** | Minimizes storage footprint by storing XOR-ed differences between consecutive timestamps and metric values. |
| **Metric Indexing** | **Inverted Index (Label-to-Series Map)** | Enables sub-second filtering of millions of time series based on label sets (e.g., `app="shopee"`, `env="prod"`). |
| **Data Lifecycle** | **Downsampling Algorithms** | Reduces long-term storage costs by aggregating high-resolution data into lower-resolution summaries (Min/Max/Avg). |
| **Cardinality Estimation** | **HyperLogLog** | Probabilistic algorithm for approximating the count of distinct elements (unique IPs, active series) with minimal memory. Native in Redis and ClickHouse. |
| **Frequency Estimation** | **Count-Min Sketch** | Probabilistic data structure for approximate frequency counting in high-cardinality streams; used in network traffic analysis and analytics pipelines. |
| **Full-Text Log Search** | **Inverted Index (Lucene / Elasticsearch)** | Maps every unique token/word to a list of document IDs for instantaneous keyword searching. |
| **Log / Trace Sampling** | **Reservoir Sampling** | Guarantees a statistically fair, fixed-size sample from an unbounded stream without knowing the total size upfront. |
| **Tracing Hierarchy** | **Directed Acyclic Graphs (DAGs) / N-ary Trees** | Represents the parent-child relationship of spans as a request traverses multiple microservices. |
| **Tracing Throughput** | **Adaptive / Tail-based Sampling** | Algorithms that decide which traces to keep based on traffic volume or the presence of errors/latency. |

## Distributed Systems & Storage

| Component | Key Data Structure / Algorithm | Purpose |
| :--- | :--- | :--- |
| **Disk I/O Optimization** | **Bloom Filters** | A probabilistic data structure used to check if a key exists in a file segment, preventing unnecessary and slow disk reads. |
| **Database Storage Engine** | **B+ Trees** | The standard index structure in relational and key-value databases (PostgreSQL, MySQL InnoDB, etcd) for fast range scans and point lookups. |
| **In-Memory Sorted Sets** | **Skip List** | A probabilistic linked-list structure providing O(log n) search/insert. Powers Redis `ZSET` (sorted sets) and RocksDB's memtable. |
| **Data Integrity Verification** | **Merkle Tree** | A hash tree where each node is a hash of its children, enabling efficient and tamper-proof verification of large data sets. Used in git objects, etcd anti-entropy, Cassandra repair, and S3 object integrity. |
| **Cluster Membership & Failure Detection** | **Gossip Protocol** | An epidemic-style protocol where nodes periodically exchange state with random peers. Used in Consul, Cassandra, and Kubernetes node communication for decentralized health propagation. |
| **Cluster Consensus** | **Raft / Paxos Algorithms** | Ensures a consistent state across a distributed control plane (like `etcd`) during leader elections or network partitions. |

## Kubernetes & Orchestration

| Component | Key Data Structure / Algorithm | Purpose |
| :--- | :--- | :--- |
| **Pod Scheduling** | **Filtering (Predicates) & Scoring (Priorities)** | A two-step algorithm to find feasible nodes and then rank them to find the "best fit" for a workload. |

## Networking & Security

| Component | Key Data Structure / Algorithm | Purpose |
| :--- | :--- | :--- |
| **Distributed Sharding & Discovery** | **Consistent Hashing** | Maps keys to nodes on a virtual ring so that only a minimal subset of keys are remapped when nodes are added/removed. Core to Redis Cluster, Cassandra, and Envoy's upstream selection. |
| **Service Load Balancing** | **Hash Tables (IPVS)** | Provides O(1) lookup for routing packets to service backends, scaling much better than the linear O(n) lists in `iptables`. |
| **Network Security** | **Trie (Prefix Tree)** | Used for high-speed IP prefix matching and CIDR block lookups in routers and firewalls. |
| **Rate Limiting** | **Token Bucket / Leaky Bucket** | Classical algorithms for controlling traffic flow: Token Bucket allows bursts up to a capacity; Leaky Bucket enforces a strictly constant output rate. |
| **Rate Limiting** | **Sliding Window Counter** | Combines a fixed window's efficiency with a rolling time boundary to prevent edge-of-window burst exploitation. Commonly implemented with Redis in API gateways. |
