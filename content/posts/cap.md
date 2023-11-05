---
title: "CAP"
date: "2023-11-03T10:03:19+08:00"
tags: ["distributed system"]
description: "CAP Overview"
draft: true
---
## Theorem
- **Consistency**: Every read receives the most recent write or an error.
- **Availability**: Every request receives a (non-error) response, without the guarantee that it contains the most recent write.
- **Partition Tolerance**: The system continues to operate despite an arbitrary number of messages being dropped (or delayed) by the network between nodes.

![cap](/images/cap.svg)
In the absence of a **partition**, both availability and consistency can be satisfied, but when the network partition occurs, one is then left with two options: consistency or availability.
- **CP System**: When choosing consistency over availability, the system will return an error or a time out if particular information cannot be guaranteed to be up to date due to network partitioning. (Only make sure **partial service nodes** are available, the system has to shut down the non-consistent node)
- **AP System**: When choosing availability over consistency, the system will always process the query and try to return the most recent available version of the information, even if it cannot guarantee it is up to date due to network partitioning. (All nodes are available, when the partition is resolved, the AP databases typically resync the nodes to repair all inconsistencies in the system.)
- **CA System**: It's impossible to delivery both strong consistency and Availability as the consistency protocol (e.g. 2PC) cannot be satified.

## Consensus Protocol (TBD)
#### 1. Paxos

#### 2. Zab

#### 3. Raft
A Raft cluster contains several servers; five is a typical number, which allows the system to tolerate two failures.

At any given time each server is in one of three states:
- Leader: The leader handles all client requests (if a client contacts a follower, the follower redirects it to the leader).
- Follower: Followers are passive: they issue no requests on their own but simply respond to requests from leaders and candidates.
- Candidate: is used to elect a new leader

In normal operation there is exactly **one leader** and all of the other servers are **followers**.

![Raft State Machine](/images/raft_server_status.png)

> *From Raft Paper: https://raft.github.io/raft.pdf*

Check the [visualization](https://thesecretlivesofdata.com/raft/) for the quick udnerstanding.
#### 4. Gossip

#### 5. 2PC

## Reference
- https://en.wikipedia.org/wiki/CAP_theorem
- https://www.ibm.com/topics/cap-theorem
- https://raft.github.io/
