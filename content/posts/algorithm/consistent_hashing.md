---
title: "Consistent Hashing"
date: "2025-10-13T09:39:24+08:00"
tags: ["algorithm"]
description: "understand consistent hashing from scratch"
draft: true
---

## What is Consistent Hashing? (Key Points)

**Consistent Hashing** is a distributed hashing technique that minimizes data movement when nodes are added or removed from a distributed system. Here are the key points:

- **Hash Ring**: Maps both data and nodes to a circular hash space
- **Minimal Rebalancing**: Only affects adjacent nodes when adding/removing nodes
- **Load Distribution**: Evenly distributes data across available nodes
- **Fault Tolerance**: Gracefully handles node failures
- **Scalability**: Easy to add/remove nodes without major data redistribution

## Visualization Diagram
TBD

## Detailed Explanation of Key Points

### Hash Ring

The **hash ring** is the core concept of consistent hashing. It's a circular space where:

- **Range**: Uses a finite hash space (e.g., 32-bit or 64-bit)
- **Circular Nature**: The ring wraps around, so the largest hash value connects to the smallest
- **Node Placement**: Each node is assigned one or more positions on the ring based on hash values
- **Key Mapping**: Data keys are hashed and mapped to the ring, then assigned to the next node clockwise. Equivalently, pick the first node with position ≥ the key hash (ranges are (predecessor, node]).

**Why a ring?** The circular nature ensures that every position on the ring has a "next" node, eliminating edge cases at the boundaries.

### Minimal Rebalancing

When nodes are added or removed, only the **adjacent nodes** are affected:

- **Adding a Node**: Only keys that hash between the new node and its predecessor need to be moved
- **Removing a Node**: Only keys that were assigned to the removed node need to be reassigned
- **Efficiency**: In a system with N nodes, only 1/N of the data needs to be moved on average

**Example**: If we have nodes at positions 1000, 5000, 8000, and add a node at 3000:
- Keys hashing to 1001-3000: Move from node at 1000 to new node at 3000
- Keys hashing to 3001-4999: Remain on node at 5000
- Other keys: Remain unchanged

### Load Distribution

Consistent hashing provides **even load distribution** through:

- **Virtual Nodes**: Each physical node is represented by multiple virtual nodes on the ring
- **Hash Function**: Use a fast, well-distributed hash (e.g., MurmurHash3, xxHash); cryptographic strength isn't required
- **Placement**: Virtual node positions are determined by hashing (pseudo-random), which avoids clustering

**Virtual Nodes Example**:
- Physical Node A might have virtual nodes at positions: 1000, 4000, 7000
- Physical Node B might have virtual nodes at positions: 2000, 5000, 8000
- This spreads the load more evenly across physical nodes

### Fault Tolerance

The system handles **node failures** gracefully:

- **Replication**: Each key is stored on multiple nodes (replicas)
- **Automatic Failover**: When a node fails, its keys are automatically served by replicas
- **Health Monitoring**: Failed nodes can be detected and removed from the ring
- **Data Recovery**: When a node comes back online, it can recover data from replicas

**Replica Strategy**: With replication factor R (including the primary), store each key on the primary and the next R-1 distinct physical nodes clockwise (skip duplicates from virtual nodes).

### Scalability

Consistent hashing enables **horizontal scaling**:

- **Add Nodes**: New nodes can be added without stopping the system
- **Remove Nodes**: Nodes can be gracefully removed with minimal data movement
- **Dynamic Scaling**: The system can automatically scale based on load
- **No Central Coordinator (with membership)**: Ownership is computed locally from the ring, but cluster membership still requires a mechanism (e.g., static config, gossip, or a CP store)

## Python Implementation

Here's a complete, runnable implementation of consistent hashing:
TBD link instead

The implementation will demonstrate:
1. Adding nodes to the hash ring
2. Key distribution across nodes
3. Load balancing with virtual nodes
4. Adding a new node and showing minimal rebalancing
5. Removing a node and showing automatic failover

## Real-World Applications

Consistent hashing is used in many distributed systems:

- **Distributed Caches**: Memcached, Redis Cluster
- **Load Balancers**: Nginx, HAProxy
- **Distributed Databases**: Cassandra, DynamoDB
- **CDNs**: Content delivery networks
- **Microservices**: Service discovery and load balancing

## Advantages and Disadvantages

### Advantages:
- **Minimal Data Movement**: Only 1/N of data moves when adding/removing nodes
- **Load Balancing**: Even distribution of data across nodes
- **Fault Tolerance**: Graceful handling of node failures
- **Scalability**: Easy horizontal scaling
- **No Single Point of Failure**: Decentralized design

### Disadvantages:
- **Non-Uniform Load**: Without virtual nodes, load can be uneven
- **Complex Implementation**: More complex than simple modulo hashing
- **Hash Collisions**: Rare but possible with poor hash functions
- **Memory Overhead**: Virtual nodes require additional memory

## Best Practices

1. **Use Virtual Nodes**: Implement virtual nodes for better load distribution
2. **Choose Good Hash Function**: Use cryptographic hash functions (MD5, SHA-1)
3. **Implement Replication**: Store data on multiple nodes for fault tolerance
4. **Monitor Load**: Continuously monitor load distribution across nodes
5. **Handle Failures**: Implement proper failure detection and recovery
6. **Test Thoroughly**: Test with various node addition/removal scenarios

## Conclusion

Consistent hashing is a powerful technique for building scalable, fault-tolerant distributed systems. By minimizing data movement during node changes and providing even load distribution, it enables systems to scale horizontally while maintaining high availability. The implementation provided above demonstrates all the key concepts and can be used as a foundation for building distributed systems.

---

## References
- https://www.youtube.com/watch?v=UF9Iqmg94tk&t=2s