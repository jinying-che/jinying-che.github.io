---
title: "CPU"
date: "2023-10-16T22:54:48+08:00"
tags: ["linux"]
description: "CPU hardware topology, Linux scheduling, NUMA, and practical troubleshooting commands"
---

## Hardware Topology

A CPU is not just one execution unit. A server is a hierarchy of sockets, processor packages, physical cores, hardware threads, caches, memory controllers, and NUMA nodes.

```text
System
|- socket(s), normally one processor package per populated socket
|  |- one or more silicon dies or chiplets
|  |- physical cores
|  |  `- one or more hardware threads (logical CPUs)
|  `- shared and private CPU caches
|- DRAM, attached through CPU memory controllers
`- PCIe devices, such as NVMe SSDs and network adapters
```

On Linux, the smallest schedulable CPU unit is a **logical CPU**. Commands may call it a `CPU`, `processor`, `thread`, or `logical core`; these usually refer to the same OS-visible unit.

![Dual-socket CPU, core, hardware-thread, and NUMA topology](/images/cpu-topology.drawio.svg)

The diagram shows a common dual-socket design where each socket is one NUMA node. This is a useful mental model, not a universal rule: modern processors can expose multiple NUMA nodes per socket, and virtual machines can present an artificial topology.

### Socket and processor package

A **CPU socket** is the motherboard connector that accepts a compatible processor package. In normal server inventory, "two sockets" means the motherboard can hold two processor packages; `lscpu` reports how many populated sockets Linux can see.

The package is the physical CPU installed in the socket. It can contain one monolithic silicon die or several dies/chiplets. The motherboard socket, processor generation, electrical interface, firmware, and chipset must all be compatible.

Examples:

- One socket with one 96-core processor: `1 socket x 96 cores = 96 physical cores`.
- Two sockets with 48-core processors: `2 sockets x 48 cores/socket = 96 physical cores`.
- If each core supports two-way SMT, either system can expose `192 logical CPUs`.

Socket count matters because it affects cost, power, memory capacity and bandwidth, PCIe connectivity, and NUMA behavior. Two systems with the same total core count can perform differently if one must frequently access memory attached to another socket.

### Physical core and logical CPU

A **physical core** is a real execution core implemented in silicon. It has execution pipelines, registers, and usually private L1 and L2 caches.

A **logical CPU** is an execution context that Linux can schedule work onto. With Intel Hyper-Threading or the more general Simultaneous Multithreading (SMT), one physical core exposes two or more logical CPUs. Those sibling logical CPUs share much of the physical core, so they do not provide the throughput of two independent physical cores.

For example, an 8-core processor with two hardware threads per core exposes:

```text
1 socket x 8 cores/socket x 2 threads/core = 16 logical CPUs
```

SMT improves utilization when one thread is stalled, but the gain depends on the workload. It does not double compute capacity. CPU-bound jobs competing for the same execution units may gain little, while mixed or latency-stalled workloads often gain more.

### Hardware thread, OS thread, and process

The word **thread** is overloaded:

| Term | Meaning |
| --- | --- |
| Hardware thread | A logical CPU exposed by a physical core; a place where Linux can run work |
| OS thread | A schedulable software execution flow inside a process |
| Process | A resource container with its own virtual address space, file descriptors, and one or more OS threads |

Linux schedules OS threads, not whole processes, onto logical CPUs. A process with eight runnable threads can therefore run on as many as eight logical CPUs at once. A single-threaded process can run on only one logical CPU at a time, although the scheduler may migrate it between CPUs.

```shell
# Show each thread, the logical CPU it last ran on, and its CPU usage.
ps -eLo pid,tid,psr,pcpu,comm --sort=-pcpu | head

# Show per-thread statistics for one process every second.
pidstat -t -p 1234 1

# Inspect or change the logical CPUs allowed for a process.
taskset -cp 1234
taskset -cp 0-3 1234
```

### Cache hierarchy

CPU caches keep frequently used data closer to the execution cores than DRAM:

| Level | Typical ownership | Relative size and speed |
| --- | --- | --- |
| L1 | Private to one physical core, often split into instruction and data caches | Smallest and fastest |
| L2 | Usually private to one core | Larger and slightly slower |
| L3 / LLC | Shared by a group of cores, often across a die or package | Largest on-chip cache and slower than L1/L2 |
| DRAM | Local to a NUMA node or socket through memory controllers | Much larger and much slower than cache |

Exact cache sharing depends on the processor. Inspect it instead of assuming:

```shell
lscpu -C

# Detailed cache topology for logical CPU 0.
find /sys/devices/system/cpu/cpu0/cache -maxdepth 2 -type f \
  \( -name 'level' -o -name 'type' -o -name 'size' \
  -o -name 'shared_cpu_list' \) -print
```

### NUMA

**NUMA** means Non-Uniform Memory Access. A NUMA node groups logical CPUs with memory that is local to them. Local memory access is normally faster and has more available bandwidth than accessing memory attached to another node.

In a common two-socket server:

```text
NUMA node 0 = CPUs near socket 0 + socket 0's local DRAM
NUMA node 1 = CPUs near socket 1 + socket 1's local DRAM
```

A thread can still access remote memory, but traffic crosses the inter-socket link. Performance-sensitive databases, JVMs, and packet-processing applications may suffer when threads run on one node while their memory resides on another.

Linux normally tries to allocate memory on the node where a thread first touches each page. This **first-touch policy** means initialization placement matters: one initialization thread can accidentally place most memory on one node before worker threads spread across the machine.

```shell
# Summarize NUMA nodes, their CPUs, memory, and inter-node distance.
numactl --hardware

# Show per-node memory allocation and remote-access counters.
numastat
numastat -p 1234

# Run a command on node 0 and allocate its memory from node 0.
numactl --cpunodebind=0 --membind=0 ./my-program

# Interleave allocations across all nodes when uniform bandwidth is preferable.
numactl --interleave=all ./my-program
```

CPU pinning and memory binding can improve predictability, but incorrect binding can reduce performance or cause allocation failures. Measure before and after changing the default policy.

## Inspecting a Linux System

### Read the topology summary

`lscpu` is the best first command:

```shell
$ lscpu
Architecture:                         x86_64
CPU(s):                               192
On-line CPU(s) list:                  0-191
Thread(s) per core:                   2
Core(s) per socket:                   48
Socket(s):                            2
NUMA node(s):                         2
NUMA node0 CPU(s):                    0-47,96-143
NUMA node1 CPU(s):                    48-95,144-191
```

Interpretation:

```text
2 sockets x 48 physical cores/socket = 96 physical cores
96 physical cores x 2 threads/core   = 192 logical CPUs
```

`CPU(s)` means logical CPUs, not physical cores. On systems with offline CPUs, the online count can be lower than the configured count.

```shell
# Print the exact mapping. CORE IDs can repeat across sockets, so use
# the SOCKET + CORE pair to identify a physical core.
lscpu -e=CPU,NODE,SOCKET,CORE,ONLINE,MAXMHZ

# Counts visible to ordinary programs.
nproc
getconf _NPROCESSORS_ONLN

# Check whether SMT is active and inspect CPU 0's sibling set.
cat /sys/devices/system/cpu/smt/active
cat /sys/devices/system/cpu/cpu0/topology/thread_siblings_list
```

Example mapping:

```text
CPU NODE SOCKET CORE ONLINE
  0    0      0    0    yes
 96    0      0    0    yes
  1    0      0    1    yes
 97    0      0    1    yes
```

Here logical CPUs `0` and `96` are SMT siblings on the same physical core. Logical CPUs `1` and `97` are another sibling pair.

### Inspect hardware and firmware data

```shell
# Processor-package information from system firmware; usually requires root.
sudo dmidecode --type processor

# A richer hierarchy including caches, NUMA nodes, memory, and PCIe devices.
# Install the hwloc package if lstopo is unavailable.
lstopo-no-graphics

# Show online/offline CPU ranges directly from sysfs.
cat /sys/devices/system/cpu/online
cat /sys/devices/system/cpu/offline
```

Firmware tables can be incomplete or wrong, especially in virtual machines. Use `lscpu` and sysfs for the topology Linux actually schedules against.

## Reading a Server Specification

Consider this inventory line:

```text
CPU: Intel 96Core  DRAM: 64GB*16  NVMe: 1.92TB*2  NIC: 25G*1P*1
```

It most likely means:

| Part | Interpretation |
| --- | --- |
| `CPU: Intel 96Core` | 96 physical CPU cores in total, but confirm socket count and SMT separately |
| `DRAM: 64GB*16` | Sixteen 64 GB memory modules: 1,024 GB by inventory arithmetic, commonly described as 1 TB of RAM |
| `NVMe: 1.92TB*2` | Two 1.92 TB NVMe SSDs, 3.84 TB raw capacity before RAID and formatting |
| `NIC: 25G*1P*1` | Likely one 25 Gbit/s NIC with one port; vendor notation should be confirmed |

**DRAM** is the server's volatile working memory. It loses its contents when power is removed. **NVMe** is a protocol for persistent solid-state storage attached through PCIe; it keeps data without power and is much slower than DRAM, but much larger and cheaper per byte.

The specification is incomplete for performance planning. Ask for the processor model, socket count, cores per socket, SMT state, NUMA layout, memory speed and channel population, NVMe model and RAID mode, and NIC port count.

## CPU Utilization and Load

### `/proc/stat`

Linux exports cumulative CPU time counters in `/proc/stat`. The first `cpu` line aggregates all logical CPUs; subsequent lines such as `cpu0` are per logical CPU. Tools including `top`, `vmstat`, and `mpstat` calculate percentages from changes between samples.

```shell
head -5 /proc/stat
```

### `top`

```shell
$ top
top - 17:18:53 up 50 days, 16:06, 7 users, load average: 1.50, 1.20, 0.90
Tasks: 127 total, 1 running, 126 sleeping, 0 stopped, 0 zombie
%Cpu(s): 12.0 us, 3.0 sy, 0.0 ni, 84.0 id, 0.5 wa, 0.0 hi, 0.5 si, 0.0 st
```

The load averages cover the last 1, 5, and 15 minutes. They count runnable tasks plus tasks in uninterruptible sleep, commonly storage I/O. A load of `1.5` on a six-logical-CPU system represents about 25% of CPU capacity only when the load is CPU-bound and evenly schedulable; load average is not itself a CPU utilization percentage.

Important CPU fields:

| Field | Meaning |
| --- | --- |
| `us` | Time running user-space code |
| `sy` | Time running kernel code |
| `ni` | Time running user-space code with adjusted nice priority |
| `id` | Idle time |
| `wa` | Idle time while at least one I/O request was outstanding |
| `hi` | Time servicing hardware interrupts |
| `si` | Time servicing software interrupts |
| `st` | Time a virtual CPU waited while the hypervisor ran something else |

Press `1` in `top` to switch between aggregate and per-logical-CPU statistics. A multithreaded process can exceed `100%` CPU in `top`: on the usual Irix-mode scale, `100%` means one logical CPU fully occupied.

### `vmstat`

`vmstat` combines runnable-task, memory, paging, block-I/O, interrupt, context-switch, and CPU counters. Ignore the first line because it is an average since boot; later lines cover each sampling interval.

```shell
vmstat 1
```

Useful columns are `r` (runnable tasks), `b` (blocked tasks), `us`, `sy`, `id`, `wa`, and `st`. Compare `r` with the number of logical CPUs, but look for a sustained queue rather than reacting to one sample.

### `pidstat`

`pidstat` reports process and thread activity. It is part of the `sysstat` package.

```shell
# CPU statistics for active processes every second.
pidstat 1

# One process, including its threads, every second.
pidstat -t -p 1234 1

# Context switches for all tasks every second.
pidstat -w 1
```

Useful fields include `%usr`, `%system`, `%wait`, `%CPU`, and `CPU`, the logical CPU on which the task ran.

### `mpstat`

`mpstat` shows whether work is balanced across logical CPUs:

```shell
# All logical CPUs, once per second.
mpstat -P ALL 1
```

A low machine-wide average can hide one saturated logical CPU. This is common for single-threaded programs, interrupt affinity, lock contention, and poorly distributed network queues.

### `perf`

`perf` uses kernel performance counters and tracing facilities to explain where CPU time goes.

```shell
# High-level counters for one command.
perf stat ./my-program

# Sample the hottest functions system-wide; usually requires elevated privileges.
sudo perf top

# Record stack samples for one process, then open the report.
sudo perf record -g -p 1234 -- sleep 30
sudo perf report
```

Start with elapsed time, task-clock, context switches, CPU migrations, cycles, instructions, and cache misses. Interpret cache-miss percentages in the context of the workload and processor; there is no universal good value.

### `strace`

`strace` traces system calls and signals. It is useful when apparent CPU trouble is actually repeated I/O, short sleeps, failed calls, or lock-related system calls.

```shell
# Summarize system-call time and counts for an existing process.
sudo strace -c -p 1234
```

Tracing adds overhead, especially with verbose output on busy processes. See the [file-system troubleshooting notes](/posts/file_system/#5-strace) for more examples.

## Practical Checklist

When investigating a CPU problem:

1. Run `lscpu` to establish sockets, physical cores, logical CPUs, and NUMA nodes.
2. Use `uptime`, `top`, or `vmstat 1` to distinguish CPU demand from blocked I/O.
3. Use `mpstat -P ALL 1` to find imbalance or one saturated logical CPU.
4. Use `pidstat -t -p PID 1` to identify busy application threads.
5. Check CPU and memory placement with `taskset -cp PID` and `numastat -p PID`.
6. Use `perf stat` or `perf record` only after identifying the process and symptom.

Keep these quantities separate: **socket/package** describes physical installation, **physical core** describes silicon execution resources, **logical CPU** describes a schedulable hardware context, and **OS thread** describes software work scheduled onto that context.
