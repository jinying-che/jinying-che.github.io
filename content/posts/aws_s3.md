---
title: "How AWS S3 Works?"
date: "2026-03-17T22:16:23+08:00"
tags: ["aws", "s3"]
description: "A deep dive into how AWS S3 scales to 500+ trillion objects across tens of millions of hard drives"
---

## S3 at Scale

AWS S3 is one of the most heavily used services on the internet. The numbers are staggering:

| Metric | Value |
|--------|-------|
| Objects stored | 500+ trillion (as of S3's 20th birthday, March 2026) |
| Peak requests | 200+ million/s |
| Peak traffic | >1 PB/s |
| Storage capacity | Hundreds of exabytes |
| Storage devices | Tens of millions of HDDs |

The question is: **how does S3 achieve 99.999999999% (11 nines) durability and high availability at this scale?**

---

## Storage Foundation: Hard Disk Drives

Despite the rise of SSDs, S3's backbone is **commodity HDDs**. Why? Cost. At this scale, the price-per-GB advantage of HDDs is massive.

But HDDs have fundamental physical limitations:

| Property | Value |
|----------|-------|
| IOPS | ~120 (unchanged for 30 years) |
| Random I/O throughput | ~32 MB/s |
| Avg read latency (0.5MB random) | ~16ms |
| Seek time | ~8-9ms |
| Rotational latency | ~4ms |

The read latency comes from two mechanical operations:
1. **Seek time (~8-9ms)**: moving the read/write head to the correct track
2. **Rotational latency (~4ms)**: waiting for the disk platter to spin to the right sector

```
          ┌──────────────┐
          │   Spindle     │
          │     ◉─────────┤◄── Read/Write Head
          │   /   \       │
          │  | platter|   │    1. Head seeks to track (8-9ms)
          │   \   /       │    2. Platter rotates to sector (4ms)
          │               │    3. Data is read sequentially
          └──────────────┘
```

This means S3 can't rely on raw disk speed — it must work **around** these limitations through parallelism and smart data placement.

---

## Erasure Coding: The Durability Engine

Traditional distributed storage uses **replication** (e.g., store 3 copies). S3 uses a more efficient approach: **erasure coding**.

### How Erasure Coding Works

To illustrate the concept, consider a simplified **5-of-9 scheme** (5 data shards + 4 parity shards):

```
Original Object
     │
     ▼
┌─────────────────────────────────────────────┐
│          Erasure Coding (5-of-9)            │
├─────┬─────┬─────┬─────┬─────┬────┬────┬────┬────┐
│ D1  │ D2  │ D3  │ D4  │ D5  │ P1 │ P2 │ P3 │ P4 │
│data │data │data │data │data │par │par │par │par │
└──┬──┴──┬──┴──┬──┴──┬──┴──┬──┴──┬─┴──┬─┴──┬─┴──┬─┘
   │     │     │     │     │     │    │    │    │
   ▼     ▼     ▼     ▼     ▼     ▼    ▼    ▼    ▼
 Disk1 Disk2 Disk3 Disk4 Disk5 Disk6 Disk7 Disk8 Disk9
  (spread across min. 3 Availability Zones)
```

- Object is split into **5 data shards + 4 parity shards** = 9 total
- Any **5 of 9 shards** can reconstruct the original object
- Tolerates up to **4 simultaneous shard losses**
- Shards are distributed across **a minimum of 3 AZs** (e.g., 3+3+3), so S3 can survive the loss of an entire AZ

### Production Erasure Coding Configurations

In practice, S3 uses **different erasure coding ratios depending on drive size** (revealed in Andy Warfield's USENIX FAST '23 keynote). Larger drives take longer to rebuild, so they need more parity shards:

| Configuration | Data Shards | Parity Shards | Total | Storage Overhead | Drive Size |
|---|---|---|---|---|---|
| 17+3 | 17 | 3 | 20 | ~1.18x | Smaller drives (fast rebuild) |
| 16+4 | 16 | 4 | 20 | ~1.25x | Mid-size drives |
| 15+5 | 15 | 5 | 20 | ~1.33x | Larger drives (16TB+, slow rebuild) |

A 16TB drive takes far longer to restore than a 4TB drive. During that rebuild window, the data is more vulnerable, so more parity shards compensate for the longer exposure.

### Erasure Coding vs Replication

| | 3x Replication | Erasure Coding (e.g., 16+4) |
|--|----------------|------------------------|
| Storage overhead | 3.0x | ~1.25x |
| Tolerate failures | 2 | 4 |
| Recovery sources | 1 copy | Any 16 of remaining shards |
| Read parallelism | 3 sources | 20 sources |
| Cost efficiency | Low | High |

**Erasure coding uses dramatically less storage while tolerating more failures.** This is how S3 offers 11 nines of durability cost-effectively.

---

## Three Dimensions of Parallelism

S3 overcomes HDD limitations by parallelizing across three dimensions:

### 1. Front-End Servers (Connection-Level)

Clients open **multiple HTTP connections** to different S3 endpoints through connection pools. This prevents any single front-end server from becoming a bottleneck.

```
Client App
  ├── conn1 ──▶ Frontend Server A
  ├── conn2 ──▶ Frontend Server B
  ├── conn3 ──▶ Frontend Server C
  └── conn4 ──▶ Frontend Server D
```

### 2. Hard Drives (Shard-Level)

Each object's erasure-coded shards are distributed across **multiple storage backends** on different drives. A single read can pull shards from 9 different disks in parallel.

```
GET object
  ├── read shard D1 from Disk 1
  ├── read shard D2 from Disk 2
  ├── read shard D3 from Disk 3    ◄── All in parallel
  ├── read shard D4 from Disk 4        (only need 5 of 9)
  └── read shard D5 from Disk 5
```

### 3. Operations (Request-Level)

- **Multipart uploads**: Large files split into ~10 parallel chunks uploaded concurrently
- **Byte-range GETs**: Clients request specific byte ranges in parallel, then reassemble

```
Upload 1GB file (multipart):
  Part 1 (100MB) ──▶ ┐
  Part 2 (100MB) ──▶ │
  Part 3 (100MB) ──▶ ├──▶ S3 assembles final object
  ...              │
  Part 10(100MB) ──▶ ┘

Download with byte-range GET:
  GET bytes=0-99MB       ──▶ ┐
  GET bytes=100MB-199MB  ──▶ ├──▶ Client reassembles
  GET bytes=200MB-299MB  ──▶ ┘
```

---

## Load Balancing: Avoiding Hot Spots

At S3's scale, hot spots can cascade into outages. S3 uses several techniques to prevent them.

### Power of Two Random Choices

When writing data, S3 uses a simple but effective algorithm:

1. Randomly pick **two candidate nodes**
2. Check current load of both
3. Place the shard on the **less loaded** node

```
Write shard:
  Random pick ──▶ Node A (load: 72%)
  Random pick ──▶ Node B (load: 45%)
                          ▲
                    Place shard here (less loaded)
```

This "power of two choices" approach is well-studied in computer science. It dramatically reduces the probability of hot spots compared to purely random placement, while avoiding the overhead of global load tracking.

### Workload Decorrelation at Scale

As the number of independent customers grows, their peak usage patterns naturally **decorrelate**. The peak-to-mean demand ratio collapses:

```
Few customers:     ████████░░░░██████░░░░░░████████   (bursty)
                   ▲ peaks are sharp and unpredictable

Many customers:    ███████████████████████████████████  (smooth)
                   ▲ aggregate demand is nearly flat
```

This is essentially the **law of large numbers** applied to infrastructure — individual workloads are unpredictable, but the aggregate is smooth.

### Data Rebalancing

S3 continuously rebalances data in the background:

- **Newer data** receives higher access frequency; as data ages, access naturally declines
- When new storage racks (each ~20 PB capacity) join the cluster, cold data is migrated to free up I/O capacity on hot nodes
- This ensures even I/O distribution across the fleet

---

## ShardStore: The Storage Backend

Each storage node runs **ShardStore**, S3's custom key-value storage engine written in **Rust** (~40,000 lines). It won the **Best Paper Award at SOSP 2021** for its use of lightweight formal methods.

### Architecture: Value-Less LSM Tree

ShardStore uses a **value-less (key-value separated) LSM tree** — a critical optimization over standard LSM trees. The LSM tree stores only **keys mapped to disk pointers** (offsets), while the actual shard data is stored separately in contiguous disk regions called "extents."

```
Write Path:

 PUT shard
      │
      ├──────────────────────┐
      ▼                      ▼
 ┌──────────┐          ┌──────────┐
 │ MemTable  │          │  Extent   │
 │ key → ptr │          │ (shard    │  ◄── Actual data written
 │ (sorted)  │          │  bytes)   │      sequentially to disk
 └────┬─────┘          └──────────┘
      │ flush
      ▼
 ┌──────────┐
 │  Level 0  │  ◄── Only keys + pointers (small!)
 │  SSTable  │
 └────┬─────┘
      │ compaction
      ▼
 ┌──────────┐
 │  Level 1  │  ◄── Merge-sorted, larger files
 │ SSTables  │
 └────┬─────┘
      ▼
    ...deeper levels...
```

Why value-less? Because shard data is large (MBs) while keys are tiny. Keeping data out of the LSM tree drastically reduces **write amplification** — compaction only moves small key-pointer entries, not the actual shard data.

### Crash Consistency: Soft Updates (No WAL)

Unlike most LSM implementations that use a **Write-Ahead Log (WAL)**, ShardStore uses a **soft-updates** approach:

- Tracks dependencies between disk writes
- Only flushes a write after all its dependencies have been persisted
- Avoids the overhead of redirecting every write through a WAL
- Maintains crash consistency without the extra I/O cost

### Why This Design Works for HDDs

- **Sequential writes** to extents maximize HDD throughput
- **Small LSM tree** (keys + pointers only) fits more in memory, reducing disk reads
- **Compaction** is cheaper since it only moves small entries
- **Bloom filters** optimize read path by skipping levels that don't contain the target key

---

## Request Routing & Networking

### Shuffle Sharding at DNS Level

S3 uses **shuffle sharding** at the DNS resolution layer to isolate failures:

```
Traditional sharding:
  Customer A ──▶ [Server 1, Server 2]
  Customer B ──▶ [Server 1, Server 2]    ◄── If Server 1 dies,
  Customer C ──▶ [Server 1, Server 2]        ALL customers affected

Shuffle sharding:
  Customer A ──▶ [Server 1, Server 3]
  Customer B ──▶ [Server 2, Server 5]    ◄── If Server 1 dies,
  Customer C ──▶ [Server 4, Server 6]        only Customer A affected
```

Each customer gets a **random subset** of servers. The probability that two customers share the exact same set is extremely low, so one customer's failure blast radius doesn't overlap with others.

### Hedge Requests & Straggler Mitigation

Erasure coding makes tail latency mitigation **naturally cheap**. With a 16+4 scheme, S3 can request all 20 shards and take the **first 16 responses**, ignoring the slowest 4:

```
GET object (16+4 erasure coding):
  Request all 20 shards in parallel
  ├── Shard 1  responds at  5ms  ✓
  ├── Shard 2  responds at  6ms  ✓
  ├── ...
  ├── Shard 16 responds at 12ms  ✓  ◄── Got 16, reconstruct now!
  ├── Shard 17 responds at 45ms  ✗  (ignored — straggler)
  ├── Shard 18 responds at 80ms  ✗  (ignored)
  ├── Shard 19 responds at ...   ✗  (cancelled)
  └── Shard 20 timed out         ✗  (cancelled)
```

Additionally, the AWS Common Runtime (CRT) library tracks latency distributions and fires **hedge requests** — if a request exceeds the p95 latency threshold, a duplicate is sent to an alternate host. Whichever responds first wins.

This trades a small amount of extra load for significantly better tail latency. And because data is spread across 20 shards rather than full replicas, hedging is far cheaper than with replication.

---

## Durability: Defense in Depth

11 nines of durability (99.999999999%) means: if you store **1 billion objects**, you can expect to lose **1 object every 100 years**. S3 achieves this through multiple layers:

### 1. Erasure Coding
As discussed — tolerates 4 simultaneous shard losses per object.

### 2. Continuous Integrity Checking
S3 runs **auditor microservices** that continuously inspect every byte across the entire fleet. These services verify checksums, detect bit rot or silent corruption, and automatically trigger repair when degradation is found. S3 also monitors redundancy levels to ensure objects can tolerate concurrent device failures at all times.

As of late 2024, S3 enables **CRC-based checksums by default** on all uploads — the server independently computes and validates a checksum before durably storing the object.

### 3. Durable Chain of Custody
Every operation that touches data (write, move, delete) is tracked and verified. Data doesn't just "exist" — its full lifecycle is auditable.

### 4. Formal Verification
S3 applies multiple formal verification techniques to critical code paths:

- **TLA+**: Used since ~2011 for verifying distributed algorithms. Found a bug in a fault-tolerant network algorithm that could cause data loss — the shortest error trace was **35 high-level steps long**, impossible to find through conventional testing.
- **P language**: Used to verify S3's **strong consistency** model (the 2020 strong-read-after-write feature).
- **Lightweight formal methods (ShardStore)**: Property-based testing with an embedded Rust specification (~13% additional code). Uses **Shuttle**, an open-sourced stateless model checker, to verify crash consistency and concurrency. Before any change ships, **hundreds of millions of scenarios** are checked via AWS Batch. This approach prevented **16 issues from reaching production**.

### 5. Threat Modeling
The team models durability as a security problem — what could cause data loss? Hardware failure, software bugs, operational errors, and even adversarial scenarios are all considered.

---

## Software Deployment at Scale

Rolling out updates to tens of millions of disks is itself an engineering challenge. S3 deploys ShardStore updates using an approach inspired by erasure coding:

- Updates roll out gradually across the fleet
- At no point are enough nodes updating simultaneously to violate durability guarantees
- The system maintains the ability to read from sufficient healthy shards throughout the deployment

This means S3 can ship **continuous updates without downtime**.

---

## Summary

```
┌─────────────────────────────────────────────────────────┐
│                     AWS S3 Architecture                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Client ──▶ DNS (shuffle sharding)                      │
│              │                                          │
│              ▼                                          │
│         Front-End Servers (connection pooling)           │
│              │                                          │
│              ▼                                          │
│         Request Router                                  │
│              │                                          │
│    ┌─────────┼─────────┐                                │
│    ▼         ▼         ▼                                │
│  AZ-1      AZ-2      AZ-3     (Availability Zones)     │
│    │         │         │                                │
│    ▼         ▼         ▼                                │
│  ShardStore nodes (value-less LSM, Rust)                │
│    │         │         │                                │
│    ▼         ▼         ▼                                │
│  HDDs with erasure-coded shards (e.g., 16+4)            │
│                                                         │
│  Cross-cutting concerns:                                │
│  • Power-of-two-choices load balancing                  │
│  • Hedge requests for tail latency                      │
│  • Continuous integrity checking                        │
│  • Background data rebalancing                          │
│  • Formal verification of durability paths              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The genius of S3 isn't any single technique — it's how these well-known distributed systems concepts (erasure coding, LSM trees, shuffle sharding, hedge requests, power-of-two-choices) are **composed together** at unprecedented scale.

## Reference

**Official AWS Sources:**
- [Amazon S3 Data Durability Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DataDurability.html)
- [Amazon S3 FAQs](https://aws.amazon.com/s3/faqs/)
- [Twenty Years of Amazon S3](https://aws.amazon.com/blogs/aws/twenty-years-of-amazon-s3-and-building-whats-next/)
- [How Automated Reasoning Helps Amazon S3 Innovate at Scale](https://aws.amazon.com/blogs/storage/how-automated-reasoning-helps-us-innovate-at-s3-scale/)
- [Workload Isolation Using Shuffle Sharding — AWS Builders' Library](https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/)

**Papers & Talks:**
- [Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3 (SOSP 2021, Best Paper)](https://www.amazon.science/publications/using-lightweight-formal-methods-to-validate-a-key-value-storage-node-in-amazon-s3)
- [Building and Operating a Pretty Big Storage System (Andy Warfield, USENIX FAST '23)](https://www.usenix.org/conference/fast23/presentation/warfield)
- [Building and Operating a Pretty Big Storage System — All Things Distributed](https://www.allthingsdistributed.com/2023/07/building-and-operating-a-pretty-big-storage-system.html)

**Analysis:**
- [How AWS S3 Scales with Tens of Millions of Hard Drives](https://bigdata.2minutestreaming.com/p/how-aws-s3-scales-with-tens-of-millions-of-hard-drives)
