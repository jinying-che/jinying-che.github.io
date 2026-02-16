---
title: "Cluster Membership"
date: "2026-02-16T10:00:00+08:00"
tags: ["distributed-system"]
description: "how nodes in a distributed system agree on who's in the cluster"
draft: true
---

## The Problem

In a distributed system, every node needs to agree on **who is currently in the cluster**. Without agreement, nodes build different views of the system and make inconsistent decisions (e.g., route the same key to different nodes in a [consistent hash ring](../algorithm/consistent_hashing.md)).

### Example: cache cluster without membership

```text
cache-3 crashes at T=0

cache-1:  detects timeout   → removes cache-3 from ring → routes keys to cache-1/cache-2
cache-2:  hasn't noticed    → still routes keys to cache-3 → errors

Same key, different routing. The system is inconsistent.
```

## What Membership Provides

A membership protocol maintains a **consistent member list** across all nodes. It answers:

1. **Who is alive right now?** (failure detection)
2. **Has a new node joined?** (join protocol)
3. **How do all nodes converge on the same view?** (dissemination)

## Common Approaches

### Static Configuration

- Member list hardcoded in config files or environment variables
- Add/remove requires config change + rolling restart
- Simple but doesn't handle failures automatically
- **Used by**: simple setups, some Redis Cluster configs

### Gossip Protocol

- Nodes periodically exchange membership info with random peers
- Failures detected via heartbeat timeout, then gossiped to others
- Eventually consistent — all nodes converge but not instantly
- **Used by**: Cassandra, Consul (Serf), DynamoDB

```text
T=0s:  cache-3 stops sending heartbeats
T=1s:  cache-1 suspects cache-3 (heartbeat timeout)
       → gossips {cache-3: suspected} to cache-2
T=2s:  cache-2 receives gossip → also marks cache-3 suspected
T=5s:  suspicion confirmed → all nodes remove cache-3
       → cluster view converges: {cache-1, cache-2}
```

### SWIM (Scalable Weakly-consistent Infection-style Membership)

- Improvement over basic gossip — combines ping, ping-req (indirect probe), and dissemination
- Faster failure detection, bounded false positive rate
- Piggybacks membership updates on protocol messages (no extra bandwidth)
- **Used by**: Consul (Serf), Memberlist (HashiCorp)

### Centralized Registry (CP Store)

- Nodes register themselves in a strongly consistent store (etcd, ZooKeeper, Consul KV)
- Use leases/sessions with TTL — if a node fails to renew, it's removed
- Strong consistency — all readers see the same member list
- Trade-off: depends on the registry being available
- **Used by**: Kubernetes (etcd), Kafka (ZooKeeper → KRaft), HDFS

## Comparison

| Approach | Consistency | Failure Detection | Complexity | Dependency |
|---|---|---|---|---|
| Static config | Manual | None (external) | Low | None |
| Gossip | Eventually consistent | Heartbeat-based | Medium | None |
| SWIM | Eventually consistent | Ping + indirect probe | Medium | None |
| CP store (etcd/ZK) | Strong | Lease/TTL | Low (client-side) | External store |

## How It Connects to Other Concepts

- **[Consistent Hashing](../algorithm/consistent_hashing.md)**: consumes the member list as input to build the hash ring
- **Replication**: needs to know which nodes hold replicas
- **Leader Election**: needs membership to determine eligible candidates
- **Service Discovery**: membership is essentially service discovery for internal cluster nodes

---

## References

TBD
