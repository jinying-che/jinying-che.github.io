---
title: "File System"
date: "2023-09-30T15:25:41+08:00"
tags: ["linux"]
description: "File System Overview"
---

## Architecture
![file system](/images/linux_file_system.svg)

## VFS
The Virtual File System (also known as the Virtual Filesystem Switch) is the software layer in the kernel that provides the filesystem interface to userspace programs via system call. It also provides an abstraction within the kernel which allows different filesystem implementations to coexist.

A VFS specifies an interface (or a "contract") between the kernel and a concrete file system. Therefore, it is easy to add support for new file system types to the kernel simply by fulfilling the contract.

#### Superblock
The superblock records various information about the enclosing filesystem, such as block counts, inode counts, supported features, maintenance information, and more.

Show the super block info in Linux:
> all examples in this post are from my vps (OS: Ubuntu 22.04.2 LTS)

```shell
$ df -h
Filesystem      Size  Used Avail Use% Mounted on
tmpfs            96M  1.3M   95M   2% /run
/dev/vda1        24G   12G   11G  52% /
tmpfs           479M     0  479M   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
tmpfs            96M  4.0K   96M   1% /run/user/0

$ dumpe2fs /dev/vda1
dumpe2fs 1.46.5 (30-Dec-2021)
Filesystem volume name:   <none>
Last mounted on:          /
Filesystem UUID:          cc673143-6902-4174-990e-8cba0304cb7a
Filesystem magic number:  0xEF53
Filesystem revision #:    1 (dynamic)
Filesystem features:      has_journal ext_attr resize_inode dir_index filetype needs_recovery extent 64bit flex_bg sparse_super large_file huge_file dir_nlink extra_isize metadata_csum
Filesystem flags:         signed_directory_hash
Default mount options:    user_xattr acl discard
Filesystem state:         clean
Errors behavior:          Continue
Filesystem OS type:       Linux
Inode count:              6537600
Block count:              6553339
Reserved block count:     327666
Free blocks:              3333553
Free inodes:              6325191
First block:              0
Block size:               4096
Fragment size:            4096
...
```
`Source Code`: [super_block c source code](https://github.com/torvalds/linux/blob/b9ddbb0cde2adcedda26045cc58f31316a492215/include/linux/fs.h#L1188)

#### Directory Entry (Dentry)
1. Dentry is used by VFS to represent information about the **directories and files** inside the **memory**
2. Dentries live in RAM and are never saved to disc: they exist only for performance. (RAM cannot save all dentries -> LFU cache)
3. An individual dentry usually has a pointer to an inode
4. It's a fast look-up mechanism to translate a pathname (filename) into a specific **dentry** then **inode**

`Source Code`: [dentry c source code](https://github.com/torvalds/linux/blob/b9ddbb0cde2adcedda26045cc58f31316a492215/include/linux/dcache.h#L82)

#### Index Node 
1. Index node(Inode) is a data structure that stores ownership, permissions, file size, and other metadata-related terms.
2. They live either on the disc (for block device filesystems) or in the memory (for pseudo filesystems). Inodes that live on the disc are copied into the memory when required and changes to the inode are written back to disc.
3. Every file and directory on Linux is represented by a unique inode number used by the system to identify it on the file system. 

```shell
# ls
#   -i, --inode
#     print the index number of each file
$ ls -i workspace/main.go
1067025 workspace/main.go

$ ls -i workspace
1067025 main.go

# stat - display file or file system status
$ stat workspace/main.go
  File: workspace/main.go
  Size: 72              Blocks: 8          IO Block: 4096   regular file
Device: fc01h/64513d    Inode: 1067025     Links: 1
Access: (0644/-rw-r--r--)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2023-10-09 22:12:30.884848072 +0800
Modify: 2023-06-11 22:44:14.194331022 +0800
Change: 2023-06-11 22:44:14.194331022 +0800
 Birth: 2023-06-11 22:44:14.194331022 +0800

$ stat workspace
  File: workspace
  Size: 4096            Blocks: 8          IO Block: 4096   directory
Device: fc01h/64513d    Inode: 1066674     Links: 2
Access: (0755/drwxr-xr-x)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2023-10-09 22:12:33.196939026 +0800
Modify: 2023-10-09 22:12:32.612916118 +0800
Change: 2023-10-09 22:12:32.612916118 +0800
 Birth: 2023-06-11 22:43:01.453639583 +0800
```
`Source Code`: [inode c source code](https://github.com/torvalds/linux/blob/94f6f0550c625fab1f373bb86a6669b45e9748b3/include/linux/fs.h#L639)

#### File
1. The file object is the in-memory representation of an open file.
2. The file object is initialized with a pointer to the dentry and a set of file operation member functions which are taken from the inode data.
3. The file structure is placed into the file descriptor table for the process.
4. Reading, writing and closing files are done by using the userspace **file descriptor** to grab the appropriate file structure.

`Source Code`: [file c source code](https://github.com/torvalds/linux/blob/b9ddbb0cde2adcedda26045cc58f31316a492215/include/linux/fs.h#L992)

## What happens when reading a file in Linux?
TBD Diagram to elaborate on the concepts above

## Block Layer
TBD 

## Troubleshooting
1. df & du
    ```shell
    # df displays the amount of disk space available on the file system containing each file name argument
    $ df -h
    Filesystem      Size  Used Avail Use% Mounted on
    tmpfs            96M  1.3M   95M   2% /run
    /dev/vda1        24G   12G   11G  52% /
    tmpfs           479M     0  479M   0% /dev/shm
    tmpfs           5.0M     0  5.0M   0% /run/lock
    tmpfs            96M  4.0K   96M   1% /run/user/0
    
    # du Summarize disk usage of the set of FILEs, recursively for directories.
    /usr > du -h --max-depth=1 # display the usage of first depth in a human readable format 
    4.0K    ./lib32
    32M     ./sbin
    465M    ./src
    4.0K    ./lib64
    439M    ./share
    ...
    
    # display the usage of this depth and sort the output in a human readable format
    $ du -hs * | sort -rh | head -10 
    5.0G    usr
    3.9G    var
    2.4G    swapfile
    1.1G    snap
    ...
    ```
2. iostat (device level)
    ```shell
    # Display a continuous device report of extended statistics at two second intervals.
    # take note of the following statistics: 
    # - %util: percentage of elapsed time during which I/O requests were issued to the device 
    # - r/s, w/s: read/write requests per second for the device
    # - rKB/s, rWB/s: the number of sectors (kilobytes, megabytes) read/write for the device per second
    # - r_await, w_await: the average time (in milliseconds) for read/write requests issued to the device to be served. This includes the time spent by the requests in queue and the time spent servicing them.
    $ iostat -x -d 2
    Device            r/s     rkB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wkB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dkB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
    loop0            0.00      0.02     0.00   0.00    0.29    47.11    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
    loop1            0.00      0.00     0.00   0.00    0.14    34.80    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
    sr0              0.00      0.00     0.00   0.00    0.00     0.12    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
    vda              0.24      6.06     0.09  28.32    0.37    25.79    2.18     15.93     0.48  17.94    0.38     7.32    0.01      8.63     0.00   0.00    2.14  1258.27    0.20    0.14    0.00   0.10
    
    
    Device            r/s     rkB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wkB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dkB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
    loop0            0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
    loop1            0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
    sr0              0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
    vda              0.00      0.00     0.00   0.00    0.00     0.00    1.00     30.00     6.50  86.67    0.50    30.00    0.50      2.00     0.00   0.00    2.00     4.00    1.00    0.00    0.00   0.20
    ```

3. pidstat (process level)
    ```shell
    # pidstat - Report statistics for Linux tasks.
    $ pidstat -d 1 # report I/O statistics per second 
    11:11:01 PM     0       387      0.00     16.00      0.00       0  systemd-journal
    
    11:11:01 PM   UID       PID   kB_rd/s   kB_wr/s kB_ccwr/s iodelay  Command
    11:11:02 PM     0       387      0.00     36.00      0.00       0  systemd-journal
    
    11:11:02 PM   UID       PID   kB_rd/s   kB_wr/s kB_ccwr/s iodelay  Command
    11:11:03 PM     0       387      0.00     32.00      0.00       0  systemd-journal
    11:11:03 PM     0       825      0.00      4.00      0.00       0  sshd
    
    $ pidstat -d -p 387 1 # report I/O statistics for process 387 per second 
    11:11:24 PM   UID       PID   kB_rd/s   kB_wr/s kB_ccwr/s iodelay  Command
    11:11:25 PM     0       387      0.00     16.00      0.00       0  systemd-journal
    11:11:26 PM     0       387      0.00      0.00      0.00       0  systemd-journal
    11:11:27 PM     0       387      0.00     32.00      0.00       0  systemd-journal
    11:11:28 PM     0       387      0.00      0.00      0.00       0  systemd-journal
    ```

4. iotop
    ```shell
    # iotop - simple top-like I/O monitor
    # NOTE: not handy as kernal config may need to update (at least the CONFIG_TASK_DELAY_ACCT, CONFIG_TASK_IO_ACCOUNTING, CON-FIG_TASKSTATS and CONFIG_VM_EVENT_COUNTERS options need to be enabled in your Linux kernel build configuration.)
    $ iotop
    Total DISK READ :       0.00 B/s | Total DISK WRITE :       7.85 K/s 
    Actual DISK READ:       0.00 B/s | Actual DISK WRITE:       0.00 B/s 
      TID  PRIO  USER     DISK READ  DISK WRITE  SWAPIN     IO>    COMMAND 
    15055 be/3 root        0.00 B/s    7.85 K/s  0.00 %  0.00 % systemd-journald 
    ```

5. strace
    ```shell
    # strace - trace system calls and signals
    # process 654373 is a prometheus node exporter, through the strace (system calls), it's able to roughly understand how does node exporter work 
    
    $ strace -p 654373
    ...
    newfstatat(AT_FDCWD, "/proc", {st_mode=S_IFDIR|0555, st_size=0, ...}, 0) = 0
    statfs("/proc", {f_type=PROC_SUPER_MAGIC, f_bsize=4096, f_blocks=0, f_bfree=0, f_bavail=0, f_files=0, f_ffree=0, f_fsid={val=[0, 0]}, f_namelen=255, f_frsize=4096, f_flags=ST_VALID|ST_NOSUID|ST_NODEV|ST_NOEXEC|ST_RELATIME}) = 0
    newfstatat(AT_FDCWD, "/proc/655152", {st_mode=S_IFDIR|0555, st_size=0, ...}, 0) = 0
    openat(AT_FDCWD, "/proc/655152/stat", O_RDONLY|O_CLOEXEC) = 8
    fcntl(8, F_GETFL)                       = 0x8000 (flags O_RDONLY|O_LARGEFILE)
    fcntl(8, F_SETFL, O_RDONLY|O_NONBLOCK|O_LARGEFILE) = 0
    epoll_ctl(4, EPOLL_CTL_ADD, 8, {events=EPOLLIN|EPOLLOUT|EPOLLRDHUP|EPOLLET, data={u32=1268860600, u64=139673605326520}}) = -1 EPERM (Operation not permitted)
    fcntl(8, F_GETFL)                       = 0x8800 (flags O_RDONLY|O_NONBLOCK|O_LARGEFILE)
    fcntl(8, F_SETFL, O_RDONLY|O_LARGEFILE) = 0
    read(8, "655152 (node_exporter) R 655107 "..., 512) = 308
    read(8, "", 204)                        = 0
    close(8)                                = 0
    openat(AT_FDCWD, "/proc/stat", O_RDONLY|O_CLOEXEC) = 8
    fcntl(8, F_GETFL)                       = 0x8000 (flags O_RDONLY|O_LARGEFILE)
    fcntl(8, F_SETFL, O_RDONLY|O_NONBLOCK|O_LARGEFILE) = 0
    epoll_ctl(4, EPOLL_CTL_ADD, 8, {events=EPOLLIN|EPOLLOUT|EPOLLRDHUP|EPOLLET, data={u32=1268860600, u64=139673605326520}}) = 0
    read(8, "cpu  773459 68488 441098 3776333"..., 512) = 512
    ...
    ```
6. lsof
    ```shell
    # lsof - lists on its standard output file information about files opened by processes
    # An open file may be a regular file, a directory, a block special file, a character special file, an executing text reference, a library, a stream or a network file (Internet socket, NFS file or UNIX domain socket.)
    # man lsof for more details 
    $ lsof -p 654373 # list all files opened by node exporter
    COMMAND      PID USER   FD      TYPE   DEVICE SIZE/OFF     NODE NAME
    node_expo 655152 root  cwd       DIR    252,1     4096  1046028 /root/workspace/node_exporter-1.6.1.linux-amd64
    node_expo 655152 root  rtd       DIR    252,1     4096        2 /
    node_expo 655152 root  txt       REG    252,1 20025119  1046289 /root/workspace/node_exporter-1.6.1.linux-amd64/node_exporter
    node_expo 655152 root    0u      CHR    136,5      0t0        8 /dev/pts/5
    node_expo 655152 root    1u      CHR    136,5      0t0        8 /dev/pts/5
    node_expo 655152 root    2u      CHR    136,5      0t0        8 /dev/pts/5
    node_expo 655152 root    3u     IPv6 10182875      0t0      TCP *:9100 (LISTEN)
    node_expo 655152 root    4u  a_inode     0,14        0    12477 [eventpoll]
    node_expo 655152 root    5r     FIFO     0,13      0t0 10182871 pipe
    node_expo 655152 root    6w     FIFO     0,13      0t0 10182871 pipe
    ```

## Linux Storage Stack
![linux storage stack](/images/Linux-storage-stack-diagram_v6.2/linux_storage_stack.svg)
https://www.thomas-krenn.com/en/wiki/Linux_Storage_Stack_Diagram

## Reference
- https://developer.ibm.com/tutorials/l-linux-filesystem/
- [super block -- kernel doc](https://www.kernel.org/doc/html/latest/filesystems/ext4/globals.html?highlight=file+system+super+block)
- [vfs overview -- kernel doc](https://www.kernel.org/doc/html/latest/filesystems/vfs.html?highlight=inode)
- [What is a Superblock, Dentry, Inode and a File?](https://itslinuxfoss.com/what-is-superblock-inode-dentry-and-file/#:~:text=The%20superblock%20is%20the%20data,of%20bytes%20in%20different%20forms.)
