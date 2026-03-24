---
title: "SRE Troubleshooting Scenarios"
date: "2026-03-24T10:00:00+08:00"
tags: ["SRE", "linux", "troubleshooting"]
description: "Real-world SRE troubleshooting scenarios: CPU, Memory, Disk I/O, Network — with metric analysis and incident stories"
draft: true
---

## TL;DR — Scenario Summary

| # | Resource | Scenario | Key Symptom | Root Cause |
|---|----------|----------|-------------|------------|
| 1 | Disk I/O | ioutil HIGH + iowait HIGH | Disk saturated, CPU waiting | Classic I/O bottleneck (e.g., full table scan, no index) |
| 2 | Disk I/O | ioutil LOW + iowait HIGH | CPU waiting but local disk is idle | NFS/remote I/O, swap thrashing, slow cloud storage |
| 3 | Disk I/O | ioutil HIGH + iowait LOW | Disk saturated but CPU doesn't care | Async I/O, many cores diluting iowait, background flush |
| 4 | Disk I/O | ioutil LOW + iowait LOW | Everything normal | Healthy system (or workload is in page cache) |
| 5 | CPU | High `us` (user) | Application burning CPU | Computation, infinite loop, regex backtracking |
| 6 | CPU | High `sy` (system) | Kernel burning CPU | Excessive syscalls, context switches, lock contention |
| 7 | CPU | High `si` (softirq) | One core handling all interrupts | Network packet storm, unbalanced RX queues |
| 8 | CPU | High `st` (steal) | VM not getting CPU time | Noisy neighbor, burstable instance credits exhausted |
| 9 | CPU | High load avg + high idle | Load looks bad but CPU is free | Processes in D state waiting for I/O (ties to iowait) |
| 10 | Memory | OOM killer | Process killed unexpectedly | Memory leak, no eviction, missing limits |
| 11 | Memory | Low free, high available | Looks alarming but isn't | Page cache using idle RAM (normal!) |
| 12 | Memory | Swap thrashing | si/so spiking, everything slow | Memory overcommit, cascading failure in k8s |
| 13 | Memory | NUMA imbalance | Latency increase after migration | Cross-socket memory access penalty |
| 14 | Network | High latency, low bandwidth | Connections slow but pipe isn't full | Ephemeral port exhaustion (TIME_WAIT), retransmits |
| 15 | Network | Packet drops under load | Dropped packets during bursts | NIC ring buffer overflow, softirq backlog |
| 16 | Network | Connection timeout | Server alive but clients timeout | Accept queue full (GC pause, slow accept) |
| 17 | Network | Bandwidth saturation | NIC at capacity | Log shipper / debug logging consuming the pipe |

---

## Overview

SRE troubleshooting is about reading metrics, forming hypotheses, and narrowing down root causes. This post covers common (and tricky) scenarios organized by resource type: **Disk I/O**, **CPU**, **Memory**, and **Network**.

Each scenario follows the pattern:
1. **What the metrics look like** — the symptoms
2. **What's actually happening** — the root cause
3. **How to investigate** — the tools and commands
4. **How to fix it** — the resolution

---

## 1. Disk I/O: ioutil vs iowait

These two metrics are the most commonly confused in SRE interviews and real incidents.

### Definitions

| Metric | What It Measures | Source | Range |
|--------|-----------------|--------|-------|
| **%util** (ioutil) | Percentage of time the disk device was busy servicing I/O requests | `iostat -x` | 0-100% |
| **%iowait** (wa) | Percentage of CPU time spent **idle** while waiting for I/O to complete | `top`, `mpstat`, `vmstat` | 0-100% |

```
Key Insight:
- ioutil is about the DISK — "is the disk busy?"
- iowait is about the CPU — "is the CPU waiting for disk?"

They measure DIFFERENT things on DIFFERENT resources.
```

### The 4 Scenarios Matrix

```
                    ioutil HIGH              ioutil LOW
                ┌─────────────────────┬─────────────────────┐
 iowait HIGH    │  Scenario A         │  Scenario B         │
                │  Classic I/O        │  Remote/Network I/O │
                │  bottleneck         │  or Swap            │
                ├─────────────────────┼─────────────────────┤
 iowait LOW     │  Scenario C         │  Scenario D         │
                │  Async I/O /        │  Healthy system     │
                │  Many CPU cores     │                     │
                └─────────────────────┴─────────────────────┘
```

---

### Scenario A: ioutil HIGH + iowait HIGH (Classic I/O Bottleneck)

**Metrics:**
```shell
$ iostat -x 1
Device   r/s    w/s   rkB/s   wkB/s  await  svctm  %util
sda     450.0  120.0  3600.0  960.0   35.2   1.75   99.8   # <-- disk saturated

$ top
%Cpu(s):  5.0 us,  3.0 sy,  0.0 ni, 12.0 id, 78.0 wa, 0.0 hi, 2.0 si, 0.0 st
                                                  ^^^^ iowait 78%
```

**What's happening:** The disk is saturated (util ~100%), and CPU cores are idle waiting for I/O to complete.

**Incident Story: Database full table scan**
> A developer deployed a new API endpoint that queried a 50GB table without proper indexing.
> Every request triggered a full table scan on HDD. The disk hit 100% utilization, `await` spiked to 200ms+.
> All other queries backed up behind the slow I/O, response times went from 5ms to 10s.
> The CPUs were mostly idle (low `us`/`sy`), just waiting for the disk.

**Investigation:**
```shell
# 1. Confirm disk is the bottleneck
$ iostat -x 1                  # check %util and await
$ iotop -oP                    # find which process is doing I/O

# 2. Find the offending queries (if database)
$ pidstat -d 1                 # per-process I/O stats
$ strace -p <pid> -e read,write  # trace actual syscalls

# 3. Check if it's sequential or random I/O
$ iostat -x 1                  # compare r/s, w/s with rkB/s, wkB/s
                               # small r/s with high rkB/s = sequential
                               # high r/s with low rkB/s = random (worse on HDD)
```

**Resolution:** Add the missing index. For immediate mitigation, kill the offending queries and add rate limiting on the new endpoint.

---

### Scenario B: ioutil LOW + iowait HIGH (The Tricky One)

**Metrics:**
```shell
$ iostat -x 1
Device   r/s    w/s   rkB/s   wkB/s  await  svctm  %util
sda      2.0    1.0    16.0    8.0    1.2    0.8    0.2    # <-- disk is fine!

$ top
%Cpu(s):  2.0 us,  1.0 sy,  0.0 ni, 25.0 id, 70.0 wa, 0.0 hi, 2.0 si, 0.0 st
                                                  ^^^^ iowait 70%, but disk is idle??
```

**What's happening:** The CPU is waiting for I/O, but the LOCAL disk is not busy. The I/O wait is caused by something else.

**Possible root causes:**

#### B1: NFS / Network-mounted filesystem
```
App → read() → VFS → NFS client → network → NFS server → remote disk
                                    ^^^
                     The wait happens HERE, not on local disk
```
The process is blocked on `read()`/`write()` to an NFS mount. The local disk shows low utilization because the I/O is happening on a remote server. But the CPU still counts it as iowait because the process is in uninterruptible sleep (D state) waiting for I/O.

```shell
# Investigation
$ mount | grep nfs                    # check for NFS mounts
$ nfsstat -c                          # NFS client stats
$ ps aux | awk '$8 ~ /D/'            # find processes in D state (uninterruptible sleep)
$ cat /proc/<pid>/wchan               # where is the process stuck?
$ nfsiostat 1                         # NFS I/O stats (if available)
```

**Incident Story: NFS server network partition**
> Monitoring flagged iowait at 80% on app servers. On-call checked local disks — all healthy.
> Turned out the NFS server (hosting shared config files) had a flaky network link.
> Every app process that tried to read config was stuck in D state, waiting for NFS.
> CPU was idle but counted as iowait. Local disk was fine.

#### B2: Swap thrashing
```
App → access memory page → page fault → read from swap (disk) → very slow
```
When memory is exhausted, the kernel swaps pages to disk. When those pages are needed again, reading them back causes iowait. But the swap I/O might be on a different device than what you're monitoring, or spread thinly enough that `%util` stays low while latency is high.

```shell
# Investigation
$ vmstat 1                             # check si/so (swap in/swap out)
$ free -h                              # check available memory and swap usage
$ sar -W 1                             # swap activity
$ cat /proc/meminfo | grep -i swap     # swap details
```

**Incident Story: Java heap misconfiguration**
> A Java service was configured with `-Xmx` larger than available RAM.
> When heap grew, the OS started swapping. iowait spiked to 60%.
> The disk `%util` was only 15% because swap reads are small and spread out.
> But each swap-in added 5-10ms latency to what should be nanosecond memory accesses.
> GC pauses went from 50ms to 30 seconds.

#### B3: Slow block device (iSCSI, EBS, etc.)
Cloud block storage (AWS EBS, etc.) might have high latency but low utilization because the bottleneck is the network path to the storage backend, not the local device queue.

```shell
# Check await (average I/O latency) vs %util
$ iostat -x 1
# If await is very high (>50ms) but %util is low, the device itself is slow
# This is common with throttled EBS volumes (burstable IOPS exhausted)
```

---

### Scenario C: ioutil HIGH + iowait LOW (Async I/O / Many Cores)

**Metrics:**
```shell
$ iostat -x 1
Device   r/s    w/s   rkB/s    wkB/s  await  svctm  %util
sda     800.0  200.0  6400.0  1600.0   5.2    1.0    99.5   # <-- disk saturated

$ mpstat -P ALL 1
CPU    %usr  %sys  %iowait  %idle
all    45.0  10.0   2.0     43.0    # <-- iowait only 2%!
  0    90.0   5.0   0.0      5.0
  1    80.0  10.0   0.0     10.0
  2     5.0   5.0  10.0     80.0    # <-- only this core sees iowait
  3    10.0  15.0   0.0     75.0
```

**What's happening:** The disk is maxed out, but the CPU barely notices because:

**C1: Many CPU cores dilute iowait**

iowait is a *per-CPU* metric that gets averaged. If you have 64 cores and only 2 are waiting for I/O, the average iowait is `~3%` even though those 2 cores are 100% waiting.

```
64-core server:
- 2 cores waiting for I/O = 100% iowait per core
- Average iowait = 2/64 = 3.1%
- Disk is at 99% util

The overall iowait number HIDES the I/O problem!
```

**C2: Async I/O (io_uring, AIO)**
Applications using async I/O (like modern databases) submit I/O requests and continue doing CPU work while waiting. The process is never in "waiting for I/O" state, so the CPU doesn't count iowait — it's busy doing other work.

```shell
# Example: PostgreSQL with async I/O
# The DB submits multiple read requests, processes results from earlier requests
# while new ones complete. CPU stays busy, no iowait, but disk is saturated.
```

**C3: Background flush / writeback**
The kernel's dirty page writeback (`pdflush`/`flush`) can saturate the disk in the background. User processes don't wait because they write to page cache (memory) first.

```shell
# Investigation
$ cat /proc/sys/vm/dirty_ratio          # % of memory before blocking writes
$ cat /proc/sys/vm/dirty_background_ratio  # % of memory before background flush
$ iotop -oP                              # shows kernel flush threads eating I/O
$ echo 3 > /proc/sys/vm/drop_caches     # (careful!) flush page cache for testing
```

**Incident Story: Log rotation gone wrong**
> A batch job generated 50GB of logs per hour. The kernel buffered writes in page cache (fast, no iowait).
> But the background flush thread was continuously flushing dirty pages to a single HDD.
> Disk was at 99% util. When another service needed to read from the same disk, its latency spiked.
> The average iowait stayed at 3% because most of the 32 cores were doing computation, not waiting for I/O.
> The fix: move logs to a separate disk, tune `dirty_background_ratio`, set up proper log rotation.

---

### Scenario D: ioutil LOW + iowait LOW

**Healthy system.** Neither the disk nor the CPU is constrained by I/O. This is normal.

But watch out for:
- The disk might be underutilized because the app is **CPU-bound** — it's busy computing and not doing much I/O
- Or the workload is in **page cache** — data is served from memory, no disk access needed

---

## 2. CPU Scenarios

### Scenario: High `us` (user) CPU

**Metrics:**
```shell
$ top
%Cpu(s): 95.0 us,  2.0 sy,  0.0 ni,  3.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
```

**Possible causes:**
- Application code doing heavy computation (expected: data processing, ML inference, compression)
- Infinite loop or algorithm with O(n²) that hit large input
- Regex backtracking (catastrophic backtracking)
- Busy-wait / spin-lock in application code

**Investigation:**
```shell
$ top -H -p <pid>              # find the hot thread
$ perf top -p <pid>            # real-time function-level profiling
$ perf record -g -p <pid>     # record for detailed flame graph
$ perf report                  # view the profile

# For Java specifically:
$ jstack <pid>                 # thread dump
$ async-profiler               # sampling profiler, generates flame graph
```

**Incident Story: Regex catastrophic backtracking**
> An input validation regex like `^(a+)+$` was applied to user input.
> A specially crafted string of 30 characters caused exponential backtracking.
> One API handler pinned a CPU core at 100% `us` for minutes.
> The fix: rewrite the regex to avoid nested quantifiers, add input length limit.

---

### Scenario: High `sy` (system/kernel) CPU

**Metrics:**
```shell
$ top
%Cpu(s):  5.0 us, 85.0 sy,  0.0 ni, 10.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
```

**Possible causes:**
- Excessive context switching (too many threads contending for CPU)
- Frequent syscalls (e.g., `read()`/`write()` on many small buffers instead of batching)
- Lock contention in kernel (futex, mutex)
- Heavy memory allocation/deallocation (kernel managing page tables)
- Frequent `fork()`/`exec()` (spawning processes)

**Investigation:**
```shell
$ vmstat 1                     # check `cs` (context switches)
$ pidstat -w 1                 # per-process context switches
$ perf top                     # look for kernel functions (prefixed with [k])
$ strace -c -p <pid>          # syscall summary (count and time per syscall)

# Example strace output showing excessive syscalls:
# % time     seconds  usecs/call     calls    syscall
# ------  ----------  -----------  --------  --------
#  60.00    12.34000           1  12340000  write     <-- 12M writes!
#  25.00     5.12000           2   2560000  read
```

**Incident Story: 10,000 goroutines writing to stdout**
> A Go service logged every incoming event to stdout (captured by container runtime).
> Under load, 10,000 goroutines each called `fmt.Println()`.
> Each `Println` = `write()` syscall = user→kernel→user context switch.
> `sy` CPU hit 80%, throughput dropped. The app wasn't doing much useful work.
> Fix: use buffered logging with a single writer goroutine flushing periodically.

---

### Scenario: High `si` (software interrupt) CPU

**Metrics:**
```shell
$ top
%Cpu(s):  5.0 us,  5.0 sy,  0.0 ni, 50.0 id,  0.0 wa,  0.0 hi, 35.0 si,  0.0 st
```

**Possible causes:**
- High network packet rate (each packet triggers a softirq for processing)
- Network storm / DDoS
- Unbalanced RX/TX queues (one CPU core handling all network interrupts)

**Investigation:**
```shell
$ cat /proc/softirqs            # check NET_RX, NET_TX counts
$ mpstat -P ALL 1               # see which CPU core has high si
$ sar -n DEV 1                  # network device stats (packets/s)
$ ethtool -S eth0 | grep rx     # NIC-level stats, check for drops
```

**Incident Story: Single-core network bottleneck**
> A load balancer received 500K packets/second. All network interrupts were pinned to CPU 0.
> CPU 0: 95% `si`. Other 31 cores: nearly idle.
> Overall CPU utilization looked fine (~3%), but the system was dropping packets.
> Fix: enable RSS (Receive Side Scaling) with `ethtool -L eth0 combined 8` to distribute
> interrupts across multiple cores. Or use `irqbalance`.

---

### Scenario: High `st` (steal) CPU

**Metrics:**
```shell
$ top
%Cpu(s): 10.0 us,  5.0 sy,  0.0 ni, 30.0 id,  0.0 wa,  0.0 hi,  0.0 si, 55.0 st
```

**What's happening:** The hypervisor is stealing CPU time from this VM to serve other VMs on the same physical host. Your VM wants to run but can't get CPU.

**Possible causes:**
- Noisy neighbor on shared host (another VM consuming all physical CPU)
- VM is over-provisioned relative to physical CPU allocation
- CPU credits exhausted (AWS t2/t3 burstable instances)

**Investigation:**
```shell
$ mpstat 1                     # confirm steal time
$ cat /proc/cpuinfo            # check if vCPU count matches expectations
# Check cloud provider console for CPU credit balance (AWS CloudWatch, etc.)
```

**Incident Story: T3 instance CPU credit exhaustion**
> A batch job ran on a t3.medium (burstable). It consumed CPU credits during peak processing.
> When credits ran out, the instance was throttled to baseline (20% of a vCPU).
> `st` jumped to 80%. The job that normally took 10 minutes now took 2 hours.
> Fix: switch to a compute-optimized instance (c5) for batch workloads, reserve t3 for bursty web traffic.

---

### Scenario: Load Average High but CPU `idle` is also High

**Metrics:**
```shell
$ uptime
load average: 50.00, 48.00, 45.00    # <-- load is 50 on a 4-core machine!

$ top
%Cpu(s):  2.0 us,  1.0 sy,  0.0 ni, 25.0 id, 70.0 wa, 0.0 hi, 2.0 si, 0.0 st
```

**What's happening:** Load average in Linux includes processes in **uninterruptible sleep** (D state), not just runnable processes. Processes waiting for I/O are in D state.

```
Load Average = runnable processes (R) + uninterruptible sleep processes (D)

50 processes in D state (waiting for NFS, disk, etc.)
+ 2 processes actually running
= load average of 52

But CPU is mostly idle because those 50 processes aren't using CPU — they're waiting!
```

This ties back to **Scenario B** (iowait). Always check `iowait` when load average is high but CPU `us`/`sy` are low.

---

## 3. Memory Scenarios

### Scenario: OOM Killer Strikes

**Symptoms:**
```shell
$ dmesg | grep -i oom
[123456.789] Out of memory: Killed process 12345 (java) total-vm:8388608kB, anon-rss:7340032kB

$ journalctl -k | grep -i "out of memory"
```

**What's happening:** The kernel's OOM killer selected and killed a process to free memory.

**Investigation:**
```shell
$ dmesg -T | grep -i oom        # find which process was killed and why
$ free -h                       # current memory state
$ ps aux --sort=-%mem | head    # top memory consumers
$ cat /proc/<pid>/oom_score     # OOM score (higher = more likely to be killed)
$ cat /proc/<pid>/status | grep -i vm  # per-process memory details
```

**Incident Story: Memory leak with slow accumulation**
> A Python service had a memory leak — a global dict that cached user sessions but never evicted.
> Memory usage grew 100MB/day. After 2 weeks, it consumed all 16GB.
> OOM killer struck at 3 AM, killing the service. The restart bought 2 more weeks.
> The team thought the restart "fixed" it until it happened again.
> Root cause: `session_cache[user_id] = session` without any TTL or size limit.
> Fix: use an LRU cache with max size, or use Redis for session storage.

---

### Scenario: High Memory Usage but No OOM (Page Cache)

**Metrics:**
```shell
$ free -h
              total    used    free    shared  buff/cache   available
Mem:           64G     4G      1G      100M      59G          58G
Swap:           0B      0B      0B
```

**What's happening:** `free` shows only 1GB "free" — looks alarming! But `available` is 58GB. The 59GB in `buff/cache` is Linux page cache — it caches disk data in unused RAM and will be reclaimed instantly when apps need memory.

```
Common Mistake:
  "free memory is 1GB, we're almost out of memory!" → WRONG

Reality:
  available = free + reclaimable cache = 1G + 57G = 58G
  The system is healthy. Linux is using idle RAM productively.
```

**When to actually worry:**
```shell
$ free -h
              total    used    free    shared  buff/cache   available
Mem:           16G    14.5G    200M     50M       1.3G        800M    # <-- available is LOW
Swap:           4G     3.8G    200M                                    # <-- swap is heavily used
```
When `available` is low AND swap usage is high and growing → real memory pressure.

---

### Scenario: Swap Storm (Thrashing)

**Metrics:**
```shell
$ vmstat 1
procs ---memory--- ---swap-- -----io----
 r  b   free   buff  cache   si    so    bi    bo
 2 45   5120   1024  20480  8500  9200  8500  9200   # <-- si/so very high!
 3 42   4800   1024  20480  9100  8800  9100  8800
```

**What's happening:** The system is continuously swapping pages in and out. Processes need memory pages that were swapped to disk, load them back, and other pages get evicted. The disk becomes the bottleneck for what should be memory-speed operations.

**Symptoms:**
- Very high `si` (swap in) and `so` (swap out) in `vmstat`
- Many processes in `b` (blocked/D state)
- Everything becomes extremely slow (10-1000x slower)
- Load average shoots up (D state processes count)

**Investigation:**
```shell
$ vmstat 1                          # si/so columns
$ sar -W 1                         # pswpin/s, pswpout/s
$ smem -rs swap                    # per-process swap usage
$ for pid in /proc/[0-9]*; do
    echo "$(cat $pid/comm 2>/dev/null): $(grep VmSwap $pid/status 2>/dev/null)"
  done | sort -t: -k2 -rn | head   # find top swap consumers
```

**Incident Story: Overcommit with no swap limit in k8s**
> A Kubernetes node ran 20 pods, each requesting 1GB but with no memory limit.
> Combined actual usage reached 30GB on a 32GB node.
> The node started thrashing — swapping so aggressively that kubelet health checks failed.
> Kubernetes marked the node as NotReady, but couldn't reschedule pods because all nodes were under pressure.
> Cascading failure: other nodes took on evicted pods, also started thrashing.
> Fix: set memory limits on all pods, configure `--eviction-hard` thresholds properly.

---

### Scenario: NUMA Imbalance

**Metrics:**
```shell
$ numastat
                  node0       node1
numa_hit        52345678    12345678    # <-- node0 gets way more hits
numa_miss              0     5000000   # <-- node1 has 5M misses!
numa_foreign     5000000           0
local_node      52345678    12345678
other_node             0     5000000
```

**What's happening:** On multi-socket servers, each CPU socket has its own local memory. Accessing remote memory (another socket's RAM) adds ~100ns latency vs ~60ns for local access.

If processes are allocated on node0 but their memory is on node1, every memory access pays the cross-socket penalty.

**Investigation:**
```shell
$ numactl --hardware          # show NUMA topology
$ numastat -p <pid>           # per-process NUMA stats
$ perf stat -e node-load-misses,node-store-misses -p <pid> sleep 10
```

**Incident Story: Database performance drop after VM migration**
> After live-migrating a database VM to a new host, query latency increased 40%.
> The VM's memory was now spread across NUMA nodes instead of being local.
> Every memory access that crossed nodes added 30-40ns. For a query touching millions of rows,
> this added up to hundreds of milliseconds.
> Fix: pin VM to a single NUMA node with `numactl --membind=0 --cpunodebind=0`.

---

## 4. Network Scenarios

### Scenario: High Latency but Low Bandwidth Usage

**Metrics:**
```shell
$ sar -n DEV 1
IFACE   rxpck/s  txpck/s  rxkB/s  txkB/s  rxdrop/s  txdrop/s
eth0    1200.0   1100.0    150.0   130.0      0.0       0.0    # <-- bandwidth is fine

$ ss -s
TCP:   45000 (estab 12000, closed 30000, timewait 28000)
                                           ^^^^^^^^^^^^^^^^
                                           28K TIME_WAIT!
```

**Root causes:**

#### Connection exhaustion (ephemeral port exhaustion)
```shell
$ ss -s                                     # check TIME_WAIT count
$ sysctl net.ipv4.ip_local_port_range       # check ephemeral port range
$ ss -tn state time-wait | wc -l            # count TIME_WAIT connections
```

**Incident Story: Microservice port exhaustion**
> Service A called Service B 5,000 times/second over HTTP/1.1 without connection pooling.
> Each request opened a new TCP connection → used → closed → sat in TIME_WAIT for 60 seconds.
> 5000 req/s × 60s = 300,000 connections in TIME_WAIT.
> Default port range (32768-60999) = 28,231 ports. Exhausted.
> New connections failed with `EADDRNOTAVAIL`. Latency spiked as the kernel searched for free ports.
> Fix: use HTTP connection pooling (keep-alive), increase port range, enable `net.ipv4.tcp_tw_reuse`.

#### TCP retransmission
```shell
$ ss -ti dst <target_ip>                    # check retransmissions per connection
$ netstat -s | grep retransmit              # system-wide retransmit stats
$ sar -n TCP,ETCP 1                         # TCP stats including retransmits
```

---

### Scenario: Packet Drops Under Load

**Metrics:**
```shell
$ ifconfig eth0                    # or: ip -s link show eth0
eth0: ... RX errors 0  dropped 45231  overruns 0  frame 0
                        ^^^^^^^^^^^
$ ethtool -S eth0 | grep drop
rx_queue_0_drops: 45231
```

**Possible causes and investigation:**

```shell
# 1. Ring buffer too small
$ ethtool -g eth0                     # check current vs max ring buffer size
$ ethtool -G eth0 rx 4096            # increase if needed

# 2. Softirq not processing fast enough
$ cat /proc/net/softnet_stat          # column 2 = drops due to time_squeeze
# Format per CPU: processed, dropped, time_squeeze
# 0000abcd 00000045 00000012    <-- drops!

# 3. Socket receive buffer overflow
$ ss -lnp | grep <port>               # check Recv-Q vs queue size
$ sysctl net.core.rmem_max            # max socket receive buffer
$ sysctl net.core.netdev_max_backlog  # kernel input queue size
```

**Incident Story: Burst traffic dropping packets**
> A metrics collector received data in bursts every 10 seconds from 500 agents.
> During bursts, 500 × 100 metrics = 50,000 packets arrived within 100ms.
> The NIC ring buffer (default 256 entries) overflowed, dropping 15% of packets.
> Between bursts, everything looked fine — average packet rate was low.
> Fix: increase ring buffer (`ethtool -G eth0 rx 4096`), enable RSS for multi-queue,
> increase `net.core.netdev_max_backlog`.

---

### Scenario: Connection Timeout but Server is Running

**Metrics:**
```shell
$ ss -lnt
State  Recv-Q  Send-Q  Local Address:Port   Peer Address:Port
LISTEN    129       128    0.0.0.0:8080      0.0.0.0:*        # <-- Recv-Q > Send-Q!
```

**What's happening:** The listen backlog is full. `Recv-Q` (129) > `Send-Q` (128, the backlog size). The kernel is dropping new SYN packets silently.

```
Client → SYN → Kernel accept queue (full!) → SYN dropped → Client retries → Timeout

The server process is alive but too slow to call accept() on new connections.
```

**Investigation:**
```shell
$ ss -lnt                              # check Recv-Q vs backlog (Send-Q)
$ netstat -s | grep -i listen          # "SYNs to LISTEN sockets dropped"
$ dmesg | grep "TCP: request_sock"     # SYN flood warnings
$ sysctl net.core.somaxconn            # system-wide max backlog
```

**Incident Story: GC pause causing accept queue overflow**
> A Java web server had a 5-second GC pause (Stop-The-World).
> During the pause, no threads called `accept()`. The backlog (128) filled in 200ms.
> After the pause, the server recovered — but 3,000 clients had already timed out.
> Monitoring showed: server CPU normal, latency p50 normal, but p99 was 30 seconds.
> Fix: increase backlog to 1024, tune GC to reduce pause times (G1GC → ZGC).

---

### Scenario: Bandwidth Saturation

**Metrics:**
```shell
$ sar -n DEV 1
IFACE   rxkB/s   txkB/s
eth0    122000   122500    # ~1 Gbps on a 1 Gbps NIC — saturated!

$ tc -s qdisc show dev eth0
qdisc fq_codel 0: ... dropped 12345 ...   # <-- kernel is dropping packets
```

**Incident Story: Log shipper saturating the NIC**
> A Fluentd sidecar was configured to forward all container logs to Elasticsearch.
> A bug caused one service to log 10,000 lines/second (debug logging left on).
> The log shipper consumed 800 Mbps of the 1 Gbps NIC.
> Production traffic (200 Mbps) started dropping packets because the NIC was saturated.
> Fix: rate-limit logging per pod, move log shipping to a dedicated network interface.

---

## 5. Troubleshooting Cheat Sheet

```
Symptom                          → First Check              → Then Dig Deeper
─────────────────────────────────────────────────────────────────────────────
High load, low CPU usage         → iowait (top/vmstat)      → iostat -x, NFS, swap
High iowait, low disk util       → NFS/remote I/O, swap     → mount, nfsstat, vmstat si/so
High disk util, low iowait       → async I/O, many cores    → iotop, mpstat -P ALL
High user CPU                    → app computation          → perf top, flame graph
High system CPU                  → context switches, syscall→ vmstat cs, strace -c
High softirq CPU                 → network packets          → /proc/softirqs, sar -n DEV
High steal CPU                   → hypervisor throttling    → cloud console, instance type
OOM killed                       → memory leak              → dmesg, smem, /proc/*/status
Low free memory, high available  → page cache (normal!)     → free -h (check available)
High swap in/out                 → memory pressure          → vmstat si/so, process memory
Packet drops                     → ring buffer, backlog     → ethtool -S, /proc/net/softnet_stat
Connection timeout               → accept queue full        → ss -lnt, check Recv-Q
Port exhaustion                  → TIME_WAIT accumulation   → ss -s, connection pooling
High latency, normal bandwidth   → retransmits, congestion  → ss -ti, netstat -s
```

## 6. Essential Tool Quick Reference

| Tool | What It Shows | Key Flags |
|------|---------------|-----------|
| `top`/`htop` | Overall CPU, memory, per-process | `H` threads, `M` sort by mem |
| `vmstat` | CPU, memory, swap, I/O, context switches | `vmstat 1` for per-second |
| `mpstat` | Per-CPU breakdown | `-P ALL` for all cores |
| `pidstat` | Per-process CPU/mem/IO/ctx switches | `-d` IO, `-w` ctx switch, `-r` mem |
| `iostat` | Disk I/O stats | `-x` extended, shows %util and await |
| `iotop` | Per-process disk I/O (like top for disk) | `-oP` only active processes |
| `free` | Memory overview | `-h` human readable |
| `sar` | Historical system stats (all resources) | `-n DEV` net, `-W` swap, `-d` disk |
| `ss` | Socket statistics | `-s` summary, `-lnt` listening, `-ti` TCP info |
| `perf` | CPU profiling, flame graphs | `top` realtime, `record -g` for later |
| `strace` | Syscall tracing | `-c` summary, `-e trace=network` |
| `ethtool` | NIC configuration and stats | `-S` stats, `-g` ring buffer |
| `dmesg` | Kernel messages (OOM, hardware errors) | `-T` human timestamps |

## Reference
- [Linux Performance](https://www.brendangregg.com/linuxperf.html) by Brendan Gregg
- [USE Method](https://www.brendangregg.com/usemethod.html) — Utilization, Saturation, Errors for every resource
- [Linux Observability Tools](https://www.brendangregg.com/Perf/linux_observability_tools.png)
