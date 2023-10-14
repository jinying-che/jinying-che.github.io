---
title: "Kafka"
date: "2023-09-28T11:14:32+08:00"
tags: ["kafka"]
description: "Kafka Overview"
draft: true
---

## Key Design

#### 1. Zero-Copy
Using the zero-copy optimization offered by modern Unix and Linux operating sytems with the [sendfile system call](https://man7.org/linux/man-pages/man2/sendfile.2.html), data is copied into the pagecache exactly once and reused on each consumption instead of being stored in memory and copied out to user-space every time it is read.

#### 2. End-to-end Batch Compression
Efficient compression requires compressing batches of messages together rather than compressing each message individually.

Kafka supports the compression of batches of messages with an efficient batching format. A batch of messages can be grouped together, compressed and sent to the server in this form.

For example, the broker validates that the batch contains the same number of records that the batch header says it does. After validation, the batch of messages is written to disk in compressed form. The batch then remains compressed in the log and is transmitted to the consumer in compressed form. The consumer decompresses any compressed data that it receives.

#### 3. Batches I/O operations
he Kafka protocol is built around a “message set” abstraction that naturally groups messages together. This allows network requests to group messages together and amortize the overhead of the network roundtrip rather than sending a single message at a time. The server in turn appends chunks of messages to its log in one go, and the consumer fetches large linear chunks at a time.

#### 4. Log Compaction
TBD

## Reference
- https://kafka.apache.org/documentation/#maximizingefficiency
