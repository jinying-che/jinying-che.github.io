---
title: "HDFS (Hadoop Distributed File System)"
date: "2026-04-14T10:12:38+0800"
tags: ["hdfs", "hadoop", "distributed-system"]
description: "HDFS Overview"
draft: true
---

## Background & Motivation

Storing petabytes of data reliably across thousands of commodity servers is hard. Traditional approaches (NFS, SAN) hit scaling ceilings — a single server can only hold so many disks, and shared-storage networks become bottlenecks.

Google published the **GFS (Google File System) paper** in 2003, describing how they solved this at scale. The key insight: **hardware failure is the norm, not the exception** — at thousands of nodes, disks and machines fail daily. The file system must handle this transparently.

HDFS is the open-source implementation of these ideas, built as the storage layer for the Hadoop ecosystem. It was designed under these assumptions:

| Assumption | Implication |
|---|---|
| Hardware failures are routine | Automatic replication and failure detection |
| Files are large (GB to TB) | Optimise for throughput, not latency |
| Write-once, read-many | No random writes — simplifies consistency |
| Moving computation is cheaper than moving data | Co-locate processing with storage (data locality) |

---

## What Is It

HDFS is a **distributed, fault-tolerant file system** designed to run on commodity hardware. It stores files by splitting them into large blocks and replicating those blocks across multiple machines.

Key design choices:

- **Single-writer, multiple-reader model** — no distributed locking, no POSIX compliance
- **Append-only writes** — files can be created and appended to, but not randomly modified
- **High throughput over low latency** — optimised for large streaming reads, not interactive use
- **Data locality** — the scheduler can place computation on the same nodes where the data lives

---

## Architecture

```
                          HDFS Cluster
 ┌───────────┐     ┌──────────────────────────────────────┐
 │           │     │                                      │
 │  Client   │────▶│  NameNode (Master)                   │
 │           │     │  ┌──────────────────────────────┐    │
 │           │     │  │ Namespace: /user/data/file.csv│    │
 │           │     │  │ Block Map:                    │    │
 │           │     │  │   blk_01 → [DN1, DN3, DN4]   │    │
 │           │     │  │   blk_02 → [DN2, DN3, DN5]   │    │
 │           │     │  └──────────────────────────────┘    │
 │           │     │                                      │
 │   ┌───┐  │     │  ┌──────┐ ┌──────┐ ┌──────┐         │
 │   │   │◀─┼─────┼─▶│  DN1 │ │  DN2 │ │  DN3 │ ...     │
 │   │ D │  │     │  │┌────┐│ │┌────┐│ │┌────┐│         │
 │   │ A │  │     │  ││blk ││ ││blk ││ ││blk ││         │
 │   │ T │  │     │  ││ 01 ││ ││ 02 ││ ││ 01 ││         │
 │   │ A │  │     │  │└────┘│ │└────┘│ │└────┘│         │
 │   │   │  │     │  └──────┘ └──────┘ └──────┘         │
 │   └───┘  │     │   ▲  heartbeat + block report        │
 └───────────┘     └───┼──────────────────────────────────┘
                       │
              DataNodes report to NameNode
              Client reads/writes data directly to DataNodes
```

The Client talks to the NameNode for **metadata only** (which blocks, which DataNodes). Actual data flows **directly between Client and DataNodes** — the NameNode never touches file data.

| Component | Role |
|---|---|
| **NameNode** | Master. Manages file system namespace (directory tree, file→block mapping, block→DataNode mapping). Keeps entire namespace in RAM |
| **DataNode** | Stores actual block data on local disks. Sends heartbeat + block report to NameNode periodically |
| **Secondary NameNode / CheckpointNode** | Periodically merges FsImage + EditLog to create a new checkpoint. **Not** a hot standby |
| **Client** | Reads/writes files via HDFS API. Coordinates with NameNode for metadata, transfers data directly with DataNodes |

---

## Core Concepts

### Blocks

Files are split into fixed-size **blocks** (default **128 MB**). Each block is stored as an independent file on DataNode local disks.

```
file.csv (400 MB)
┌──────────┬──────────┬──────────┬──────────┐
│  blk_01  │  blk_02  │  blk_03  │  blk_04  │
│  128 MB  │  128 MB  │  128 MB  │  16 MB   │
└──────────┴──────────┴──────────┴──────────┘
     │           │          │          │
     ▼           ▼          ▼          ▼
   DN1,DN3     DN2,DN4    DN1,DN5    DN3,DN4
   DN5         DN6        DN2        DN6
```

Why 128 MB (not 4 KB like ext4)?

- Minimises NameNode memory — fewer blocks = fewer metadata entries
- Reduces seek overhead — large sequential reads amortise disk seek time
- A 100 million block namespace fits in ~20 GB of NameNode RAM

### Replication & Rack-Aware Placement

Each block is replicated (default **3 replicas**). HDFS uses a **rack-aware placement policy**:

```
         Rack 1                  Rack 2
  ┌─────────────────┐    ┌─────────────────┐
  │  DN1    DN2     │    │  DN3    DN4     │
  │ ┌────┐ ┌────┐  │    │ ┌────┐ ┌────┐  │
  │ │rep1│ │    │  │    │ │rep2│ │rep3│  │
  │ └────┘ └────┘  │    │ └────┘ └────┘  │
  └────────┬────────┘    └────────┬────────┘
           │                      │
           └──────────┬───────────┘
                 Rack Switch
```

For replication factor = 3:

1. **1st replica**: on the writer's node (or a random node in the writer's rack if client is remote)
2. **2nd replica**: on a node in a **different rack**
3. **3rd replica**: on a **different node** in that same remote rack

This balances:
- **Write bandwidth** — only one cross-rack transfer needed (not two)
- **Reliability** — survives a full rack failure (at least one replica is on a different rack)
- **Read bandwidth** — two replicas in one rack increase the chance of a local read

### Namespace & Metadata Persistence

The NameNode persists its state using two structures:

| Structure | Description |
|---|---|
| **FsImage** | A complete snapshot of the filesystem namespace (directory tree, file-to-block mappings) |
| **EditLog** | A write-ahead log of every namespace-modifying operation (create, delete, rename, etc.) |

Startup sequence:

```
1. Load FsImage into RAM
2. Replay EditLog transactions on top
3. Write new FsImage (checkpoint)
4. Truncate EditLog
5. Receive BlockReports from DataNodes → build block→DN mapping
6. Exit SafeMode when enough blocks report in
```

The **CheckpointNode** (or Secondary NameNode) performs step 3 periodically so that the EditLog doesn't grow unbounded.

### Heartbeat & BlockReport

DataNodes communicate with the NameNode via periodic messages:

| Message | Interval | Content |
|---|---|---|
| **Heartbeat** | Every **3 seconds** | "I'm alive" + storage capacity, utilisation, in-progress transfers |
| **BlockReport** | Every **6 hours** (default) | Full list of all block replicas on this DataNode |

If the NameNode receives **no heartbeat for 10 minutes**, the DataNode is marked dead and its blocks are re-replicated.

The NameNode **never pushes commands** to DataNodes directly. Instead, it piggybacks instructions onto heartbeat replies:

- Replicate block X to DN7
- Delete block Y
- Re-register yourself
- Shut down

---

## Key Features & Internals

### Write Pipeline

When a client writes a file, blocks are streamed through a **pipeline** of DataNodes:

```
Client         DN1           DN2           DN3
  │             │             │             │
  │──packet 1──▶│──packet 1──▶│──packet 1──▶│
  │             │             │             │
  │◀────────────┼─────────────┼─────ack 1───│
  │             │             │             │
  │──packet 2──▶│──packet 2──▶│──packet 2──▶│
  │             │             │             │
  │◀────────────┼─────────────┼─────ack 2───│
```

1. Client asks NameNode for a list of DataNodes to host the block
2. Client connects to DN1, DN1 connects to DN2, DN2 connects to DN3 → **pipeline**
3. Client pushes data as **64 KB packets**
4. Each DN writes locally and forwards downstream
5. Acks flow back upstream through the pipeline
6. Client can have multiple packets in-flight (window-based flow control)

**Visibility**: by default, data is **not visible to readers until the file is closed**. Calling `hflush()` forces all DataNodes to acknowledge — making data visible to new readers.

### Read Path

```
Client                  NameNode              DataNodes
  │                        │                     │
  │── getBlockLocations ──▶│                     │
  │◀── [blk1@DN1,DN3,DN5] │                     │
  │    [blk2@DN2,DN3,DN6]  │                     │
  │                        │                     │
  │── read blk1 ──────────────────────────────▶ DN1 (closest)
  │◀── data ──────────────────────────────────── DN1
  │                        │                     │
  │── read blk2 ──────────────────────────────▶ DN3 (closest)
  │◀── data ──────────────────────────────────── DN3
```

1. Client asks NameNode for block locations — returned **sorted by network distance** (same node > same rack > different rack)
2. Client reads from the **closest replica**
3. If a read fails or checksum mismatch is detected, the client falls back to the next replica and reports the corrupt block to the NameNode

### High Availability (HA)

The single NameNode is a single point of failure. HDFS HA solves this:

```
┌──────────────┐      ┌──────────────┐
│  Active NN   │      │ Standby NN   │
│  (serving)   │      │ (hot spare)  │
└──────┬───────┘      └──────┬───────┘
       │                     │
       │   ┌─────────────┐   │
       └──▶│ JournalNodes│◀──┘
            │ (JN1,JN2,JN3)│
            └─────────────┘
                  │
         Shared EditLog (quorum write)
```

- **Active NameNode** writes EditLog entries to a quorum of **JournalNodes** (typically 3 or 5)
- **Standby NameNode** tails the JournalNodes, replaying edits to keep its namespace in sync
- On failover, the Standby takes over — already up-to-date, so recovery is fast
- **Fencing** ensures only one NameNode is active at a time (prevents split-brain)

### Federation

A single NameNode keeps all metadata in RAM — this limits the namespace to what fits in one machine's memory.

**HDFS Federation** allows multiple independent NameNodes, each managing its own **namespace volume**:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│   NN1    │  │   NN2    │  │   NN3    │
│ /user    │  │ /logs    │  │ /tmp     │
│ (pool-1) │  │ (pool-2) │  │ (pool-3) │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │              │              │
     ▼              ▼              ▼
  ┌──────────────────────────────────┐
  │   DataNodes (shared storage)     │
  │   Each DN stores blocks from     │
  │   all Block Pools                │
  └──────────────────────────────────┘
```

- Each NameNode manages a **Block Pool** — its own set of blocks on the shared DataNodes
- NameNodes are **independent** — one crashing doesn't affect others
- Enables horizontal namespace scaling

### Balancer

Over time, DataNode utilisation becomes uneven (new nodes are empty, old nodes are full). The **Balancer** redistributes blocks:

- Moves replicas from over-utilised DataNodes to under-utilised ones
- Preserves replication factor and rack diversity
- Bandwidth-throttled to avoid impacting application I/O
- Goal: each node's utilisation is within a configurable threshold of the cluster average

### Data Integrity

HDFS protects against silent data corruption:

- **Write-time**: client computes checksums (CRC32C) for each chunk and sends them with the data
- **Read-time**: client verifies checksums — if mismatch, reports corrupt replica to NameNode and reads another
- **Block scanner**: each DataNode runs a background scanner that verifies all local blocks periodically (~every 2 weeks). At Yahoo!'s scale, this caught ~20 corrupt replicas per scan cycle

---

## Getting Started / Demo

Spin up a single-node HDFS using Docker:

```shell
# Pull the Hadoop image
docker run -d --name hdfs \
  -p 9870:9870 -p 9000:9000 \
  apache/hadoop:3 \
  bash -c "hdfs namenode -format && hdfs namenode & hdfs datanode"

# Wait ~15 seconds for startup, then exec into the container
docker exec -it hdfs bash
```

Basic HDFS shell commands:

```shell
# Create a directory
hdfs dfs -mkdir -p /user/demo

# Upload a local file
echo "hello hdfs" > /tmp/test.txt
hdfs dfs -put /tmp/test.txt /user/demo/

# List files
hdfs dfs -ls /user/demo/
# Found 1 items
# -rw-r--r--   3 root supergroup  11 2026-04-14 02:12 /user/demo/test.txt

# Read file content
hdfs dfs -cat /user/demo/test.txt
# hello hdfs

# Check file block locations
hdfs fsck /user/demo/test.txt -files -blocks -locations

# Get file to local
hdfs dfs -get /user/demo/test.txt /tmp/downloaded.txt

# Remove file
hdfs dfs -rm /user/demo/test.txt

# Check cluster status
hdfs dfsadmin -report
```

The **NameNode Web UI** is available at `http://localhost:9870` — it shows live cluster status, DataNode health, and namespace browsing.

---

## References

- [Apache HDFS Architecture (Official)](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [The Hadoop Distributed File System — AOSA Book](https://aosabook.org/en/v1/hdfs.html)
- [GFS: The Google File System (2003 Paper)](https://research.google/pubs/the-google-file-system/)
- [HDFS Federation](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/Federation.html)
- [HDFS High Availability](https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HDFSHighAvailabilityWithQJM.html)
