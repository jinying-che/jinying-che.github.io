---
title: "Memory"
date: "2023-09-28T16:10:39+08:00"
tags: ["linux"]
description: "Linux Memroy Overview"
---

## Virtual Memory
1. Virtual memory is an abstraction for memory management by operation system 
2. Each process operates the virtual memory (virtual address), which is mapped to physical memory by memory management unit (MMU) in CPU
3. The physical memory is only allocated to process when memory is firstly accessed. (e.g. `mmap()` and `brk()` in C just allocate the virtual memory first, hence you can see `VIRT` in `top` command is usually much higher than `RES`) 
4. Virtual maps to physical memory and disk (swap)
5. Virtual memory for one process includes both user space and kernel space.

![virtual memory](/images/virtual_memory.png)

## Buffer vs Cache

- Buffer: the memory used for the disk (both read and write)
- Cache: the memory used for the file (both read and write)

```
Common Mistake: Buffer is for write only, whereas Cache is for read only --> WRONG!
```

## Reclaim Memory
Operation system will try to reclaim the memory when the resource is lack:
1. LRU（Least Recently Used）
2. Swap the less used memory to disk
3. OOM (Out of Memory): kill the process who takes up lots of memory

## Allocating kernel memory (TBD)
#### Buddy System
The buddy system is a memory allocation algorithm that works by dividing memory into blocks of a fixed size, with each block being a power of two in size. 

**Drawback**: The main drawback in buddy system is internal fragmentation as larger block of memory is acquired then required. For example if a 36 kb request is made then it can only be satisfied by 64 kb segment and remaining memory is wasted. 
#### Slab System
The slab system is a memory allocation algorithm that is designed specifically for kernel memory. It works by dividing memory into fixed-size caches or slabs, each of which contains a set of objects of the same type

## TroubleShooting

#### 1. top/htop
```shell
# top, press M (order by memory)
$ top 
%Cpu(s):  0.7 us,  0.7 sy,  0.0 ni, 98.7 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem : 35.8/957.5    [||||||||||||||||||||||||||||||||||||                                                                ]
MiB Swap:  4.1/2400.0   [||||                                                                                                ]

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
    428 root      rt   0  289312  27100   9072 S   0.3   2.8   4:20.42 multipathd
    745 root      20   0 1209328   7900   1832 S   0.3   0.8  15:47.03 containerd
 359212 root      20   0   15424   9208   7600 S   0.3   0.9   0:00.01 sshd
      1 root      20   0  167692   8560   5560 S   0.0   0.9   1:30.35 systemd
      2 root      20   0       0      0      0 S   0.0   0.0   0:00.37 kthreadd

```
Run `man top`: 
- `VIRT`: The total amount of virtual memory used by the task. It includes all code, data and shared libraries plus pages that have been swapped out and pages that have been mapped but not used.
- `RES`: A subset of the virtual address space (VIRT) representing the non-swapped **physical memory** a task is currently using. 
- `SHR`: A subset of resident memory (RES) that may be used by other processes. 
- `%MEM`: A task's currently resident share of available physical memory.


#### 2. free
```shell
# free displays the total amount of free and used physical and swap memory in the system, as well as the buffers and caches used by the kernel. The information is gathered by parsing /proc/meminfo
$ free

               total        used        free      shared  buff/cache   available
Mem:          980508      183624       74136         348      722748      631876
Swap:        2457596      101948     2355648

```
Run `man free`:

- `total`: Total installed memory (MemTotal and SwapTotal in /proc/meminfo)
- `used`:   Used memory (calculated as total - free - buffers - cache)
- `free`:   Unused memory (MemFree and SwapFree in /proc/meminfo)
- `shared`: Memory used (mostly) by tmpfs (Shmem in /proc/meminfo)
- `buffers`: Memory used by kernel buffers (Buffers in /proc/meminfo)
- `cache`:  Memory used by the page cache and slabs (Cached and SReclaimable in /proc/meminfo)
- `buff/cache`: Sum of buffers and cache
- `available`: Estimation of how much memory is available for starting new applications, without swapping. 

#### 3. vmstat
```shell
# usage: vmstat [options] [delay [count]]
$ vmstat -t 2 5 # report virtual memory statistics per 2 second, total 5 
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu----- -----timestamp-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st                 UTC
 0  0 101948  72904  85464 641460    0    0     6    14   10    1  0  0 100  0  0 2023-09-28 14:41:49
 0  0 101948  72904  85472 641460    0    0     0   226   50   85  0  0 100  0  0 2023-09-28 14:41:51
 0  0 101948  72904  85472 641460    0    0     0     4   60  104  1  1 99  0  0 2023-09-28 14:41:53
 0  0 101948  72904  85472 641460    0    0     0     2   41   62  0  0 100  0  0 2023-09-28 14:41:55
 0  0 101948  72904  85472 641460    0    0     0    12   39   76  1  0 99  0  0 2023-09-28 14:41:57
```
Run `man vmstat`:

- Memory
    - These are affected by the --unit option.
    - swpd: the amount of swap memory used.
    - free: the amount of idle memory.
    - buff: the amount of memory used as buffers.
    - cache: the amount of memory used as cache.
    - inact: the amount of inactive memory.  (-a option)
    - active: the amount of active memory.  (-a option)

- Swap
    - These are affected by the --unit option.
    - si: Amount of memory swapped in from disk (/s).
    - so: Amount of memory swapped to disk (/s).

- IO
    -  bi: Blocks received from a block device (blocks/s).
    -  bo: Blocks sent to a block device (blocks/s).

- System
    - in: The number of interrupts per second, including the clock.
    - cs: The number of context switches per second.

- CPU
    - These are percentages of total CPU time.
    - us: Time spent running non-kernel code.  (user time, including nice time)
    - sy: Time spent running kernel code.  (system time)
    - id: Time spent idle.  Prior to Linux 2.5.41, this includes IO-wait time.
    - wa: Time spent waiting for IO.  Prior to Linux 2.5.41, included in idle.
    - st: Time stolen from a virtual machine.  Prior to Linux 2.6.11, unknown.


#### 4. /proc/meminfo
```shell
# This file reports statistics about memory usage on the system.
$ cat /proc/meminfo
# show the first several rows only
MemTotal:         980508 kB
MemFree:           74136 kB
MemAvailable:     634416 kB
Buffers:           85092 kB
Cached:           571860 kB
SwapCached:         9556 kB
Active:           408724 kB
Inactive:         305408 kB
Active(anon):      21352 kB
Inactive(anon):    45240 kB
Active(file):     387372 kB
Inactive(file):   260168 kB
Unevictable:       27620 kB
Mlocked:           27620 kB
SwapTotal:       2457596 kB
...
```

#### 5. memleak
```shell
# memleak - Print a summary of outstanding allocations and their call stacks to detect memory leaks. Uses Linux eBPF/bcc.
# Install: https://github.com/iovisor/bcc/blob/master/INSTALL.md#installing-bcc
$ /usr/sbin/memleak-bpfcc -p $(pidof systemd) # systemd no memory leak

Attaching to pid 212971, Ctrl+C to quit.
[04:34:51] Top 10 stacks with outstanding allocations:
[04:34:56] Top 10 stacks with outstanding allocations:
[04:35:01] Top 10 stacks with outstanding allocations:
```

## Reference
- https://www.geeksforgeeks.org/operating-system-allocating-kernel-memory-buddy-system-slab-system/
- https://www.kernel.org/doc/html/next/admin-guide/mm/concepts.html
- [BPF Compiler Collection](https://github.com/iovisor/bcc)
