---
title: "KRaft: Kafka without ZooKeeper"
date: "2023-09-28T12:00:00+08:00"
tags: ["kafka"]
description: "Deep dive into KRaft — how Kafka replaced ZooKeeper with Raft-based metadata management"
draft: true
---

## Why Replace ZooKeeper?

```
ZooKeeper Mode:

┌──────────────┐     ┌─────────────────────────────┐
│  ZooKeeper   │     │        Kafka Cluster         │
│  Ensemble    │◄───►│                              │
│  (3-5 nodes) │     │  Broker 0 (Controller)       │
│              │     │  Broker 1                     │
│  Stores:     │     │  Broker 2                     │
│  - broker    │     │                              │
│    registry  │     │  Controller fetches ALL       │
│  - topic     │     │  metadata from ZK on startup  │
│    config    │     │  and caches in memory          │
│  - partition │     │                              │
│    leaders   │     │  Other brokers get metadata   │
│  - ACLs      │     │  from Controller via          │
│              │     │  UpdateMetadata RPC           │
└──────────────┘     └─────────────────────────────┘
```

**Pain points:**

1. **Two systems to operate** — ZooKeeper is a separate distributed system with its own deployment, monitoring, and failure modes
2. **Slow controller failover** — new controller must load ALL metadata from ZK on startup. 200K partitions → failover takes minutes
3. **Extra metadata hop** — Controller → ZK → Controller → broadcast to all brokers adds latency
4. **Mismatched consistency models** — ZK is a CP system (consistent but may lose availability), different from Kafka's own model
5. **Scaling limits** — ZK bottleneck at ~200K partitions

---

## KRaft Architecture

```
┌───────────────────────────────────────────────────┐
│                  Kafka Cluster                      │
│                                                    │
│  ┌─ Controller Quorum (Raft) ──────────────────┐  │
│  │  Active Controller ◄──► Follower Controller  │  │
│  │         ▲            ◄──► Follower Controller│  │
│  │         │                                    │  │
│  │   __cluster_metadata  (internal topic)       │  │
│  │   partition 0: [epoch0][epoch1][epoch2]...   │  │
│  │   (Raft-replicated log of ALL metadata       │  │
│  │    changes: topics, partitions, configs,     │  │
│  │    ACLs, broker registrations)               │  │
│  └──────────────────────────────────────────────┘  │
│         │                                          │
│         │  MetadataFetch (pull-based)              │
│         ▼                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Broker 0│  │ Broker 1│  │ Broker 2│           │
│  │         │  │         │  │         │           │
│  │ local   │  │ local   │  │ local   │           │
│  │ metadata│  │ metadata│  │ metadata│           │
│  │ cache   │  │ cache   │  │ cache   │           │
│  └─────────┘  └─────────┘  └─────────┘           │
└───────────────────────────────────────────────────┘
```

**Key idea**: metadata is stored as a **Raft-replicated log** (`__cluster_metadata` topic), just like Kafka stores regular messages. Kafka manages its own metadata using its own log abstraction.

---

## How KRaft Works

### Metadata as an Event Log

Every metadata change is an event appended to the `__cluster_metadata` log:

```
__cluster_metadata log:

offset 0:  { type: REGISTER_BROKER, brokerId: 0, host: "...", port: 9092 }
offset 1:  { type: REGISTER_BROKER, brokerId: 1, host: "...", port: 9092 }
offset 2:  { type: CREATE_TOPIC, name: "orders", partitions: 3, replication: 3 }
offset 3:  { type: PARTITION_CHANGE, topic: "orders", partition: 0, leader: 0 }
offset 4:  { type: CONFIG_CHANGE, resource: "orders", key: "retention.ms", value: "86400000" }
offset 5:  { type: FENCE_BROKER, brokerId: 2 }   ← broker failed heartbeat
offset 6:  { type: PARTITION_CHANGE, topic: "orders", partition: 2, leader: 1 } ← new leader
...
```

The active controller is the Raft leader for this partition. Followers replicate the log. Brokers tail the log to keep their local metadata cache up to date.

### Controller Election via Raft

```
Raft Consensus (simplified):

1. Controllers form a quorum (e.g., 3 nodes)
2. One is elected leader (Active Controller) via Raft voting
3. Leader appends metadata changes to the log
4. Followers replicate: must acknowledge before commit
5. If leader fails:
   - Followers detect via heartbeat timeout
   - New election: candidate with most up-to-date log wins
   - New leader resumes from last committed offset
   - No data loss (committed = replicated to majority)
```

**Raft guarantees:**
- At most one leader per term
- Committed entries are never lost
- All nodes eventually agree on the same log

### Broker Metadata Sync (Pull-Based)

This is a fundamental design change from ZooKeeper mode:

```
ZooKeeper mode (push):
  Controller pushes UpdateMetadata RPC to ALL brokers
  → 1000 brokers × 1M partitions = huge fan-out

KRaft mode (pull):
  Each broker fetches from __cluster_metadata at its own pace
  → Like a consumer tailing a topic
  → Each broker tracks its own metadata offset
  → No fan-out problem

Broker 0: "I'm at offset 1042, give me new records"
Controller: "Here's offsets 1043-1050"
Broker 0: applies changes to local cache, now at 1050
```

---

## Deployment Modes

### Combined Mode (Small Clusters)

Each node runs both controller and broker in the same process:

```
┌─────────────────────┐
│ Node 0              │
│ Controller + Broker  │
│                     │
│ Node 1              │
│ Controller + Broker  │
│                     │
│ Node 2              │
│ Controller + Broker  │
└─────────────────────┘
```

### Isolated Mode (Production)

Controllers and brokers run on separate nodes:

```
┌─────────────────┐     ┌─────────────────┐
│ Controller 0    │     │ Broker 0         │
│ Controller 1    │     │ Broker 1         │
│ Controller 2    │     │ Broker 2         │
│ (lightweight,   │     │ ...              │
│  no data)       │     │ Broker N         │
└─────────────────┘     └─────────────────┘

Controllers: only manage metadata, no client data
Brokers: only serve produce/consume, no Raft voting
→ Clean separation of concerns
```

---

## Controller Failover — Why KRaft Is Faster

```
ZooKeeper mode failover:
  1. Old controller dies
  2. ZK detects (session timeout ~6-18s)
  3. New controller elected
  4. New controller loads ALL metadata from ZK    ← SLOW
     200K partitions → minutes to load
  5. New controller pushes metadata to all brokers
  Total: minutes for large clusters

KRaft mode failover:
  1. Old active controller dies
  2. Raft detects (heartbeat timeout, fast)
  3. New leader elected from quorum
  4. New leader already has metadata log in memory  ← INSTANT
     (was replicating as a follower the whole time)
  5. Brokers continue tailing the log
  Total: seconds
```

The key difference: in ZK mode the new controller starts cold (must reload all state). In KRaft mode the follower controllers are **hot standbys** — they already have the full metadata log replicated locally.

---

## Raft vs KRaft

KRaft is Kafka's implementation **built on top of** the Raft consensus algorithm.

| | Raft | KRaft |
|---|---|---|
| **What** | General-purpose consensus algorithm (paper, 2014) | Kafka's metadata consensus layer |
| **Scope** | Replicate any log across nodes | Replicate `__cluster_metadata` across controllers |
| **Used by** | etcd, CockroachDB, TiKV, Consul, etc. | Kafka only |
| **Specifics** | Abstract algorithm | Uses Kafka's log storage format, pull-based metadata sync |

KRaft adapts Raft with Kafka-specific optimizations — e.g., it reuses Kafka's log storage format for the metadata log, and brokers consume metadata updates by tailing that log like a regular Kafka consumer.

---

## Comparison Summary

| Aspect | ZooKeeper Mode | KRaft Mode |
|--------|---------------|------------|
| **Metadata store** | External ZooKeeper ensemble | Internal Raft log (`__cluster_metadata`) |
| **Controller** | One broker elected via ZK | Dedicated Raft quorum (3+ controllers) |
| **Metadata sync** | Push (controller → all brokers) | Pull (brokers tail the log) |
| **Controller failover** | Minutes (reload from ZK) | Seconds (follower already has state) |
| **Scalability** | ~200K partitions (ZK bottleneck) | Millions of partitions |
| **Operations** | Two systems (Kafka + ZK) | Single system |
| **Startup** | Slow (full metadata load from ZK) | Fast (replay local metadata log) |
| **Consistency** | ZK (CP) + Kafka (mixed) | Single Raft-based model |

---

## Reference
- [KIP-500: Replace ZooKeeper with a Self-Managed Metadata Quorum](https://cwiki.apache.org/confluence/display/KAFKA/KIP-500%3A+Replace+ZooKeeper+with+a+Self-Managed+Metadata+Quorum)
- [Apache Kafka KRaft Documentation](https://kafka.apache.org/documentation/#kraft)
- [Raft Paper: In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf)
- [KIP-631: The Quorum-based Kafka Controller](https://cwiki.apache.org/confluence/display/KAFKA/KIP-631%3A+The+Quorum-based+Kafka+Controller)
