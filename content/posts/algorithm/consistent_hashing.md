---
title: "Consistent Hashing"
date: "2025-10-13T09:39:24+08:00"
tags: ["algorithm"]
description: "understand consistent hashing from scratch"
---

## The Problem: `hash(key) % N`

Simple modular hashing routes keys via `node = hash(key) % N`. When a node dies and N changes (e.g., there's a cache cluster which has 3 nodes, `node 2` dies, total N: 3 → 2), **~(N-1)/N of all keys remap** to different nodes. 

In a cache cluster this causes massive cache misses → thundering herd to database → cascading failure.

```text
Key         N=3    N=2    Moved?
user:1001   1      1      No
user:1002   0      0      No
user:1003   0      1      YES
user:1004   1      0      YES
user:1006   2      0      YES
```

## The Solution: Hash Ring

Instead of `hash % N`, we use a **hash ring** — a circular number line from `0` to `2^32 - 1` where the end wraps back to the start.

**Setup**: hash each node's name (e.g., `hash("cache-1")`) to place it on the ring. To look up a key, hash the key and **walk clockwise** until you hit the first node — that node owns the key.

In the diagram below, `●` marks a node's position on the ring, and `K1/K2/K3` are data keys hashed onto the same ring:

```text
            0 (= 2^32)
            |
     Node A ●
            |  ← K1 is here, walk clockwise → hits Node A
            |
            ○ K2  ← walk clockwise → hits Node B
            |
     Node B ●
            |
            ○ K3  ← walk clockwise → hits Node C
            |
     Node C ●
            |
```

**Why this helps**: when Node C dies, only K3 (keys between Node B and Node C) needs to remap — it walks further clockwise and lands on Node A. K1 and K2 are completely untouched. On average **only 1/N keys move**, not (N-1)/N.

## Key Concepts

### Virtual Nodes (vnodes)

Few physical nodes on the ring → uneven arc lengths → skewed load. Fix: map each physical node to **100-200 virtual nodes** spread across the ring. More points → more uniform distribution. Also enables **weighted routing** (more vnodes = more traffic).

### Hash Function

Needs to be **deterministic and uniform**, not necessarily cryptographic. Good choices: MurmurHash3, xxHash. MD5/SHA work but are slower than needed.

## In Practice: What Else You Need

Consistent hashing alone only solves **key routing**. Production distributed systems pair it with:

- **Replication**: a single node owning a key is a single point of failure. Systems like Cassandra replicate each key to the next R-1 distinct physical nodes clockwise on the ring (e.g., R=3 means key stored on nodes A, B, C). This is built **on top of** the ring, not part of the hashing algorithm itself.
- **[Cluster Membership](../distributed-system/cluster_membership.md)**: the ring assumes all nodes agree on who's in the cluster. In reality you need a protocol to detect joins/failures and propagate that view — e.g., gossip (Cassandra), static config, or a CP store (etcd/ZooKeeper).

## Implementation

See [consistent_hashing.py](https://github.com/jinying-che/jinying-che.github.io/blob/main/consistent_hashing.py) for a complete Python implementation with virtual nodes and binary search lookup.

## Real-World Usage

| System | Role |
|---|---|
| DynamoDB / Cassandra | Partition data across storage nodes |
| Memcached / Redis Cluster | Route cache keys to servers |
| Nginx / HAProxy | Sticky load balancing |

## Trade-offs

| Pros | Cons |
|---|---|
| Only 1/N keys move on topology change | More complex than `hash % N` |
| Even load with vnodes | Memory overhead from vnodes |
| Decentralized ownership computation | Requires separate membership protocol |

---

## References
- https://www.youtube.com/watch?v=UF9Iqmg94tk&t=2s
