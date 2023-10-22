---
title: "CPU"
date: "2023-10-16T22:54:48+08:00"
tags: ["linux"]
description: "Linux CPU Overview"
draft: true
---

## Process vs Thread
TBD

## Troubleshooting

![overview](/images/cpu_tools.png)

#### 0 /proc/stat

#### 1. top
```shell
$ top
top - 17:18:53 up 50 days, 16:06,  7 users,  load average: 0.00, 0.00, 0.00
Tasks: 127 total,   1 running, 126 sleeping,   0 stopped,   0 zombie
%Cpu(s):  0.0 us,  0.0 sy,  0.0 ni,100.0 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :    957.5 total,    122.6 free,    162.0 used,    673.0 buff/cache
MiB Swap:   2400.0 total,   2282.0 free,    118.0 used.    622.7 avail Mem

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 782513 root      20   0   17312  11036   8652 S   0.3   1.1   0:00.04 sshd
      1 root      20   0  167728   9424   6504 S   0.0   1.0   3:05.88 systemd
      2 root      20   0       0      0      0 S   0.0   0.0   0:00.66 kthreadd

# man top to get top details, simple put:

# load average : the average number of processes that are either in a runnable or uninterruptable state for the past 1, 5, and 15 minutes. 
# e.g. `load average = 1.5` in 6 cpu system means 1/4 cpu is under laod, 3/4 cpu is idle

# us, user     : time running un-niced user processes
# sy, system   : time running kernel processes
# ni, nice     : time running niced user processes (process priority, a negative nice value means higher priority, whereas a positive nice value means lower priority)
# id, idle     : time spent in the kernel idle handler
# wa, IO-wait  : time waiting for I/O completion
# hi           : time spent servicing hardware interrupts
# si           : time spent servicing software interrupts
# st           : time stolen from this vm by the hypervisor

# PR: The scheduling priority of the task (real priority of a process as seen by the kernel)
# NI: The nice value of the task (a priority hint for the kernel)
# VIRT: The total amount of virtual memory used by the task (physical memory + swap)
# RES: A subset of the virtual address space (VIRT) representing the non-swapped physical memory (only physical memory)
# SHR: A subset of resident memory (RES) that may be used by other processes
# S: Process Status, the status of the task which can be one of:
#       D = uninterruptible sleep
#       I = idle
#       R = running
#       S = sleeping
#       T = stopped by job control signal
#       t = stopped by debugger during trace
#       Z = zombie
```

#### 2. vmstat
vmstat reports information about processes, memory, paging, block IO, traps, disks and cpu activity

refer to [details](https://jinying-che.github.io/posts/memory/#3-vmstat)

#### 3. pidstat (process level)
`pidstat` report statistics (cpu, memory, disk, stack) for Linux tasks (process), by defaut is cpu utilization without params.

- `-d`  Report I/O statistics
- `-R`  Report realtime priority and scheduling policy information.
- `-r`  Report page faults and memory utilization.
- `-s`  Report stack utilization.
- `-u`  Report CPU utilization
- `-v`  Report values of some kernel tables.
- `-w`  Report task switching activity

```shell
# Display 2 reports of CPU statistics for every active task in the system per second intervals.
$ pidstat 1 2
05:31:13 PM   UID       PID    %usr %system  %guest   %wait    %CPU   CPU  Command
05:31:14 PM     0    798270    0.00    1.00    0.00    0.00    1.00     0  pidstat

05:31:14 PM   UID       PID    %usr %system  %guest   %wait    %CPU   CPU  Command

Average:      UID       PID    %usr %system  %guest   %wait    %CPU   CPU  Command
Average:        0    798270    0.00    0.50    0.00    0.00    0.50     -  pidstat

# -p Select tasks (processes) for which statistics are to be reported 
$ pidstat -p 655152 2 3
05:38:56 PM   UID       PID    %usr %system  %guest   %wait    %CPU   CPU  Command
05:38:58 PM     0    655152    0.00    0.00    0.00    0.00    0.00     0  node_exporter
05:39:00 PM     0    655152    0.00    0.00    0.00    0.00    0.00     0  node_exporter
05:39:02 PM     0    655152    0.00    0.00    0.00    0.00    0.00     0  node_exporter
Average:        0    655152    0.00    0.00    0.00    0.00    0.00     -  node_exporter

# man pidstat for details, simple put

# PID     The identification number of the task being monitored.
# %usr    Percentage of CPU used by the task while executing at the user level (application)
# %system Percentage of CPU used by the task while executing at the system level (kernel).
# %guest  Percentage of CPU spent by the task in virtual machine (running a virtual processor)
# %wait   Percentage of CPU spent by the task while waiting to run.
# %CPU    Total percentage of CPU time used by the task. 
# CPU     Processor number to which the task is attached.
# Command The command name of the task.
```

#### 4. mpstat (cpu level)
mpstat - Report **processors** related statistics.
```shell
# Display 2 reports of statistics for all processors at 1 second intervals.
$ mpstat -P ALL 1 2
11:43:14 PM  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
11:43:15 PM  all    1.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.00
11:43:15 PM    0    1.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.00

11:43:15 PM  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
11:43:16 PM  all    1.02    0.00    1.02    0.00    0.00    0.00    0.00    0.00    0.00   97.96
11:43:16 PM    0    1.02    0.00    1.02    0.00    0.00    0.00    0.00    0.00    0.00   97.96

Average:     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
Average:     all    1.01    0.00    0.51    0.00    0.00    0.00    0.00    0.00    0.00   98.48
Average:       0    1.01    0.00    0.51    0.00    0.00    0.00    0.00    0.00    0.00   98.48

# man mpstat for details, simple put

# %usr     Show the percentage of CPU utilization that occurred while executing at the user level (application).
# %nice    Show the percentage of CPU utilization that occurred while executing at the user level with nice priority.
# %sys     Show the percentage of CPU utilization that occurred while executing at the system level (kernel). Note that this does not include time spent servicing hardware and software interrupts.
# %iowait  Show the percentage of time that the CPU or CPUs were idle during which the system had an  outstanding disk I/O request.
# %irq     Show the percentage of time spent by the CPU or CPUs to service hardware interrupts.
# %soft    Show the percentage of time spent by the CPU or CPUs to service software interrupts.
# %steal   Show the percentage of time spent in involuntary wait by the virtual CPU or CPUs while the hypervisor was servicing another virtual processor.
# %guest   Show the percentage of time spent by the CPU or CPUs to run a virtual processor.
# %gnice   Show the percentage of time spent by the CPU or CPUs to run a niced guest.
# %idle    Show the percentage of time that the CPU or CPUs were idle and the system did not have an  outstanding disk I/O request.
```

#### 5. perf 
Performance analysis tools for Linux (TBD after the actual usage)
```shell
# install perf in linux (with root)
$ apt-get install linux-tools-common linux-tools-generic linux-tools-`uname -r`

$ perf top
Samples: 22K of event 'cycles', 4000 Hz, Event count (approx.): 1228941005 lost: 0/0 drop: 0/734
Overhead  Shared Object                                                   Symbol
  14.88%  perf                                                            [.] __symbols__insert
   9.56%  perf                                                            [.] rb_next
   1.74%  perf                                                            [.] rust_demangle_callback
   1.53%  perf                                                            [.] output_resort
   1.44%  perf                                                            [.] dso__find_symbol
   1.23%  perf                                                            [.] rb_insert_color
   1.04%  [kernel]                                                        [k] clear_page_rep
   0.89%  perf                                                            [.] hist_entry__sort
   0.88%  perf                                                            [.] hpp__sort_overhead
   0.88%  [kernel]                                                        [k] asm_sysvec_apic_timer_interrupt
   0.82%  libslang.so.2.3.2                                               [.] SLsmg_write_chars
   0.66%  libc.so.6                                                       [.] cfree
   0.63%  libc.so.6                                                       [.] 0x00000000000a1747
   0.60%  sshd                                                            [.] 0x000000000006228c
   0.57%  [kernel]                                                        [k] memcpy_toio

# -g Enables call-graph (stack chain/backtrace) recording
$ perf top -g -p 655152
```

#### 6. strace
strace - trace system calls and signals, refer to [details](https://jinying-che.github.io/posts/file_system/#5-strace)
