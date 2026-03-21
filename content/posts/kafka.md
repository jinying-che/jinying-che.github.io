---
title: "Kafka"
date: "2023-09-28T11:14:32+08:00"
tags: ["kafka"]
description: "Kafka Overview"
draft: true
---

## Architecture

```
                         Kafka Cluster
                ┌─────────────────────────┐
                │                         │
 ┌──────────┐   │  ┌─────────┐ ┌─────────┐ │   ┌──────────┐
 │ Producer1 │──▶│  │ Broker0 │ │ Broker1 │ │──▶│Consumer  │
 └──────────┘   │  └─────────┘ └─────────┘ │   │ Group A  │
 ┌──────────┐   │  ┌─────────┐             │   └──────────┘
 │ Producer2 │──▶│  │ Broker2 │             │   ┌──────────┐
 └──────────┘   │  └─────────┘             │──▶│Consumer  │
                │                         │   │ Group B  │
                │  ┌───────────────────┐  │   └──────────┘
                │  │ ZooKeeper/KRaft   │  │
                │  └───────────────────┘  │
                └─────────────────────────┘
```

| Component | Role |
|-----------|------|
| **Broker** | A Kafka server that stores data and serves client requests |
| **Producer** | Publishes messages to topics |
| **Consumer** | Reads messages from topics |
| **Consumer Group** | A set of consumers that cooperatively consume a topic (each partition is consumed by exactly one consumer in the group) |
| **ZooKeeper / KRaft** | Manages cluster metadata, broker registration, leader election. KRaft (Kafka Raft) replaces ZooKeeper since Kafka 3.3+ |

---

## Key Concepts

### Topic & Partition

A **topic** is a logical category of messages. Each topic is split into **partitions** — the unit of parallelism and ordering.

```
Topic: "orders"
┌─────────────────────────────────┐
│ Partition 0: [0][1][2][3][4][5] │  ← append-only log
│ Partition 1: [0][1][2][3]       │
│ Partition 2: [0][1][2][3][4]    │
└─────────────────────────────────┘
```

- Messages within a **single partition** are strictly ordered
- Messages across partitions have **no ordering guarantee**
- Each message in a partition has a unique **offset** (monotonically increasing)

### Offset

The offset is a sequential ID that uniquely identifies each message within a partition.

```
Partition 0:
 offset:  0    1    2    3    4    5
        [msg][msg][msg][msg][msg][msg]
                         ▲
                   consumer current position
```

- Consumers track their own offset (stored in internal topic `__consumer_offsets`)
- This allows consumers to replay (seek back) or skip ahead

### Segment

Each partition is stored on disk as a sequence of **segments**. A segment is a pair of files:

```
partition-0/
├── 00000000000000000000.log       ← message data
├── 00000000000000000000.index     ← offset → physical position mapping
├── 00000000000000000000.timeindex ← timestamp → offset mapping
├── 00000000000000000345.log       ← new segment starts at offset 345
├── 00000000000000000345.index
└── 00000000000000000345.timeindex
```

- Only the **active segment** (latest) is open for writes
- Old segments are immutable and can be deleted or compacted based on retention policy
- The `.index` file uses a sparse index — not every offset is indexed, Kafka binary-searches the index then does a sequential scan in the `.log` file

### Consumer Group

```
Topic "orders" (3 partitions)         Consumer Group "payment-service"
┌──────────────┐
│ Partition 0  │ ──────────────────▶  Consumer A
│ Partition 1  │ ──────────────────▶  Consumer B
│ Partition 2  │ ──────────────────▶  Consumer C
└──────────────┘
```

- Each partition is assigned to exactly **one consumer** within a group
- If consumers > partitions → some consumers sit idle
- If consumers < partitions → some consumers handle multiple partitions
- Different consumer groups consume independently (each group gets all messages)

**Rebalance** happens when consumers join/leave or partitions change. The **Group Coordinator** (a broker) manages partition assignment.

---

## Why Kafka Is Fast

### 1. Sequential I/O (Append-Only Log)

Kafka writes to disk sequentially by appending to the end of a log file. Sequential disk I/O is extremely fast — often faster than random memory access.

```
                    Random I/O            Sequential I/O
HDD                 ~100 IOPS             ~100 MB/s
SSD                 ~10K-100K IOPS        ~500 MB/s - 3 GB/s
```

Kafka leverages the OS **page cache** heavily. The broker process itself doesn't cache data in the JVM heap — it relies on the OS to cache recently written/read data in memory. This avoids GC overhead and double-buffering.

### 2. Zero-Copy & DMA

**DMA (Direct Memory Access)** is a hardware feature that lets devices (disk controller, NIC) transfer data directly to/from RAM **without involving the CPU**:

```
Without DMA:  Disk → CPU reads byte by byte → RAM    (CPU busy entire time)
With DMA:     Disk → DMA controller → RAM             (CPU free to do other work)
```

Traditional data transfer requires **4 copies (2 by DMA, 2 by CPU)**:

```
Disk ──DMA──► Kernel Buffer ──CPU──► User Buffer ──CPU──► Socket Buffer ──DMA──► NIC
               (copy 1)       (copy 2)              (copy 3)              (copy 4)
                               ↑ wasteful            ↑ wasteful
                               CPU just moving bytes from one memory location to another
```

With zero-copy (`sendfile` syscall) — **2 copies, 0 CPU copies**:

```
Disk ──DMA──► Kernel Buffer (Page Cache) ──DMA──► NIC
               (copy 1)                    (copy 2)
                                            ↑
                                  scatter-gather DMA:
                                  NIC reads directly from page cache
                                  CPU just issues sendfile(), then it's free
```

Zero-copy eliminates the two unnecessary CPU copies between kernel space and user space. The data stays in kernel space — DMA handles both transfers (disk→memory and memory→NIC). This is why Kafka's broker CPU barely touches actual message data during consumption.

### 3. Batch I/O Operations

The Kafka protocol is built around a **"message set"** abstraction that naturally groups messages together:

- **Producer side**: messages are accumulated in a batch before sending (controlled by `linger.ms` and `batch.size`)
- **Broker side**: batches are appended to the log in one go
- **Consumer side**: fetches large linear chunks at a time

This amortizes the overhead of network roundtrips and disk I/O.

### 4. End-to-End Batch Compression

Kafka compresses **batches** of messages, not individual messages. This achieves much better compression ratios because similar messages share redundancy.

```
Producer                  Broker                    Consumer
[msg1,msg2,msg3]  ──▶  stored compressed  ──▶  decompress batch
  compress batch          on disk                [msg1,msg2,msg3]
```

Supported codecs: `gzip`, `snappy`, `lz4`, `zstd`

The broker does **not** decompress — it stores and forwards the compressed batch as-is. This saves CPU on the broker.

### 5. Partition-Level Parallelism

Multiple partitions allow multiple producers and consumers to read/write in parallel. Each partition can live on a different broker, distributing I/O across machines.

---

## High Availability

### Replication

Each partition has one **leader** and multiple **followers** (replicas). The **replication factor** determines how many copies exist.

```
Replication Factor = 3

Broker 0            Broker 1            Broker 2
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ P0 (Leader)  │   │ P0 (Follower)│   │ P0 (Follower)│
│ P1 (Follower)│   │ P1 (Leader)  │   │ P1 (Follower)│
│ P2 (Follower)│   │ P2 (Follower)│   │ P2 (Leader)  │
└──────────────┘   └──────────────┘   └──────────────┘
```

- All reads and writes go through the **leader**
- Followers replicate from the leader and stay in sync

### ISR (In-Sync Replicas)

The ISR is the set of replicas that are fully caught up with the leader.

```
Leader: offset 100
Follower A: offset 100  ← in ISR
Follower B: offset  98  ← in ISR (within replica.lag.time.max.ms)
Follower C: offset  80  ← out of ISR (lagging too far behind)
```

- A follower is removed from ISR if it falls behind by more than `replica.lag.time.max.ms` (default 30s)
- `acks=all` means the leader waits for **all ISR members** to acknowledge before confirming the write
- `min.insync.replicas` sets the minimum ISR size required for writes to succeed

### Leader Election

When a leader broker fails:
1. The controller (a special broker) detects the failure
2. A new leader is elected from the ISR
3. Clients are redirected to the new leader

```
Before:  Broker0(Leader) ← Broker1(ISR) ← Broker2(ISR)

Broker0 fails...

After:   Broker1(Leader) ← Broker2(ISR)
```

**Unclean leader election** (`unclean.leader.election.enable`): if disabled (default), only ISR members can become leader, preventing data loss but potentially making the partition unavailable if all ISR members are down.

### acks Configuration

| Setting | Behavior | Durability | Latency |
|---------|----------|-----------|---------|
| `acks=0` | Don't wait for any acknowledgment | Lowest (may lose data) | Fastest |
| `acks=1` | Wait for leader to write | Medium (data loss if leader fails before replication) | Medium |
| `acks=all` | Wait for all ISR replicas to write | Highest | Slowest |

---

## Load Balancing

### Producer-Side: Partition Assignment

Producers decide which partition to send each message to:

| Strategy | How It Works |
|----------|-------------|
| **Key-based** | `hash(key) % num_partitions` — same key always goes to the same partition (guarantees per-key ordering) |
| **Round-robin** | Messages without a key are distributed evenly across partitions |
| **Sticky partitioner** | (Default since Kafka 2.4) Stick to one partition for a batch, then rotate. Reduces latency by filling batches faster |
| **Custom** | Implement `Partitioner` interface for custom logic |

### Consumer-Side: Partition Assignment Strategies

When a consumer group rebalances, partitions are reassigned using a strategy:

| Strategy | Description |
|----------|-------------|
| **Range** | Partitions are divided evenly per topic among consumers. Can cause imbalance with multiple topics |
| **RoundRobin** | All partitions across all topics are assigned round-robin |
| **Sticky** | Like RoundRobin, but tries to minimize partition movement during rebalance |
| **CooperativeSticky** | Incremental rebalance — only moves partitions that need to move, avoiding stop-the-world rebalance |

### Broker-Side: Leader Distribution

Kafka distributes partition leaders across brokers. The controller tries to balance leadership so no single broker handles all read/write traffic.

Each broker has a `broker.rack` config — Kafka can spread replicas across racks for fault tolerance.

---

## Log Compaction

Log compaction ensures that Kafka retains **at least the last known value for each key** within a partition.

```
Before compaction:
offset:  0     1     2     3     4     5     6
key:    [K1]  [K2]  [K1]  [K3]  [K2]  [K1]  [K3]
value:  [v1]  [v2]  [v3]  [v4]  [v5]  [v6]  [v7]

After compaction:
offset:  4     5     6
key:    [K2]  [K1]  [K3]
value:  [v5]  [v6]  [v7]
```

- Only the **latest value per key** is retained
- Offsets are preserved (not reassigned)
- A message with a `null` value (tombstone) tells compaction to eventually delete the key
- Use case: changelogs, CDC (Change Data Capture), state stores

### Retention Policies

| Policy | Config | Behavior |
|--------|--------|----------|
| **Time-based** | `retention.ms` | Delete segments older than the threshold (default 7 days) |
| **Size-based** | `retention.bytes` | Delete oldest segments when partition size exceeds limit |
| **Compaction** | `cleanup.policy=compact` | Keep latest value per key |
| **Both** | `cleanup.policy=compact,delete` | Compact + delete old compacted segments |

---

## Delivery Semantics

| Semantic | Description | How to Achieve |
|----------|-------------|---------------|
| **At-most-once** | Messages may be lost, never redelivered | `acks=0` or commit offset before processing |
| **At-least-once** | Messages are never lost, but may be duplicated | `acks=all` + commit offset after processing |
| **Exactly-once** | Messages are delivered exactly once | Idempotent producer (`enable.idempotence=true`) + transactional API |

### Idempotent Producer

Each producer is assigned a **Producer ID (PID)** and each message gets a **sequence number**. The broker deduplicates based on `(PID, partition, sequence)`.

```
Producer (PID=1)
  msg(seq=0) ──▶ Broker: accept
  msg(seq=1) ──▶ Broker: accept
  msg(seq=1) ──▶ Broker: duplicate, reject  (network retry)
  msg(seq=2) ──▶ Broker: accept
```

### Transactional API

For exactly-once across multiple partitions and topics:
1. Producer begins a transaction
2. Sends messages to multiple partitions
3. Commits or aborts the transaction atomically
4. Consumers with `isolation.level=read_committed` only see committed messages

---

## KRaft (Kafka without ZooKeeper)

Since Kafka 3.3, KRaft mode replaces ZooKeeper for metadata management. ZooKeeper is fully removed in Kafka 4.0. See [KRaft Deep Dive]({{< ref "/posts/kafka/kraft" >}}) for details.

**Key idea**: metadata is stored as a **Raft-replicated log** (`__cluster_metadata` internal topic). A controller quorum (3+ nodes) manages metadata via Raft consensus. Brokers pull metadata updates by tailing this log.

| Aspect | ZooKeeper Mode | KRaft Mode |
|--------|---------------|------------|
| **Metadata store** | External ZooKeeper ensemble | Internal Raft log (`__cluster_metadata`) |
| **Controller** | One broker elected via ZK | Dedicated Raft quorum (3+ controllers) |
| **Metadata sync** | Push (controller → all brokers) | Pull (brokers tail the log) |
| **Controller failover** | Minutes (reload from ZK) | Seconds (follower already has state) |
| **Scalability** | ~200K partitions (ZK bottleneck) | Millions of partitions |
| **Operations** | Two systems (Kafka + ZK) | Single system |

---

## Key Configurations Cheat Sheet

| Config | Default | Description |
|--------|---------|-------------|
| `num.partitions` | 1 | Default partitions per new topic |
| `replication.factor` | 1 | Default replicas per partition |
| `min.insync.replicas` | 1 | Min ISR for `acks=all` writes to succeed |
| `acks` | all | Producer durability level |
| `enable.idempotence` | true | Deduplicate producer retries |
| `retention.ms` | 604800000 (7d) | How long to keep messages |
| `max.poll.records` | 500 | Max records per consumer poll |
| `session.timeout.ms` | 45000 | Consumer heartbeat timeout |
| `replica.lag.time.max.ms` | 30000 | Max lag before removing from ISR |

---

## Reference
- https://kafka.apache.org/documentation/
- https://kafka.apache.org/documentation/#design
- https://kafka.apache.org/documentation/#maximizingefficiency
