---
title: "How Files Are Located on Disk"
date: "2026-03-18T00:00:00+08:00"
tags: ["linux"]
description: "Step-by-step walkthrough of how Linux translates a file path into physical disk blocks, with commands to demonstrate each step"
---

## Overview
How does Linux translate a path like `/home/user/file.txt` into actual bytes on disk?

```
 Path: /home/user/file.txt

 ① Root inode (always inode 2)
       │
       ▼
 ② Read inode 2's data blocks → directory entries of "/"
    ┌──────────────────────────┐
    │  name       │  inode #   │
    ├─────────────┼────────────┤
    │  home       │  131073    │ ◄── found "home"
    │  etc        │  393217    │
    │  var        │  262145    │
    └──────────────────────────┘
       │
       ▼
 ③ Read inode 131073 → directory entries of "/home"
    ┌──────────────────────────┐
    │  name       │  inode #   │
    ├─────────────┼────────────┤
    │  user       │  131074    │ ◄── found "user"
    └──────────────────────────┘
       │
       ▼
 ④ Read inode 131074 → directory entries of "/home/user"
    ┌──────────────────────────┐
    │  name       │  inode #   │
    ├─────────────┼────────────┤
    │  file.txt   │  131088    │ ◄── found "file.txt"
    └──────────────────────────┘
       │
       ▼
 ⑤ Read inode 131088 → extent tree → physical disk blocks
       │
       ▼
 ⑥ Read disk blocks → actual file data
```

A **directory** is just a special file whose data blocks contain a table of `(name → inode number)` mappings. Each path component requires one inode lookup + one directory data read.

## Step 1: Pathname → Inode Number (Dentry Lookup)
Walk each path component to resolve the final inode number.

```shell
# ls -id /
#   -i: print the inode number of each entry
#   -d: list the directory itself, not its contents
$ ls -id /
2 /

# ls -ia /
#   -i: print the inode number of each entry
#   -a: show all entries including hidden (. and ..)
# walk: / → home → user → file.txt
$ ls -ia /
      2 .             393217 etc           131073 home          262145 var  ...

$ ls -ia /home
 131073 .        2 ..   131074 user

$ ls -ia /home/user
 131074 .   131073 ..   131088 file.txt

# stat: display file or file system status
# shows inode number, size, block count, permissions, timestamps, etc.
$ stat /home/user/file.txt
  File: /home/user/file.txt
  Size: 12500         Blocks: 28         IO Block: 4096   regular file
Device: fc01h/64513d  Inode: 131088      Links: 1
```

## Step 2: Inode Number → Inode Location on Disk
Inodes are stored in fixed positions on disk, organized by **block groups**. Given an inode number, the kernel computes exactly where it sits.

```shell
# dumpe2fs: dump ext2/ext3/ext4 filesystem information (reads superblock + group descriptors)
# 2>/dev/null: suppress stderr warnings
# grep -E: extended regex to match multiple patterns
$ dumpe2fs /dev/vda1 2>/dev/null | grep -E "Inode size|Inodes per group"
Inode size:               256
Inodes per group:         8192
```

The calculation:
```
 inode number:    131088
 inodes_per_group: 8192
 inode_size:       256 bytes

 block_group  = (131088 - 1) / 8192 = 15
 local_index  = (131088 - 1) % 8192 = 7695
 byte_offset  = local_index * 256   = 1,969,920 bytes into the inode table
```

```shell
# grep -A 5: show 5 lines After the match
$ dumpe2fs /dev/vda1 2>/dev/null | grep -A 5 "Group 15:"
Group 15: (Blocks 491520-524287)
  Block bitmap at 491520 (+0)
  Inode bitmap at 491536 (+16)
  Inode table at 491552-492063 (+32)   ◄── inode 131088 is in this table
  ...

# dd: copy raw bytes from a device/file
#   if=    : input file (the raw disk device)
#   bs=    : block size (4096 = one filesystem block)
#   skip=  : skip N input blocks before reading (jump to block 491552)
#   count= : copy only N blocks
# od: octal dump, display raw bytes
#   -A d   : show offsets in decimal (not octal)
#   -t x1  : output format: hex, 1 byte per unit
#   -j     : skip N bytes into the input
#   -N     : read only N bytes
$ dd if=/dev/vda1 bs=4096 skip=491552 count=512 2>/dev/null | od -A d -t x1 -j 1969920 -N 256
# (outputs raw inode bytes — size, permissions, extent tree, timestamps, etc.)
```

## Step 3: Inode → Physical Disk Blocks (Extent Tree)
The inode contains an **extent tree** that maps logical file offsets to physical disk blocks.

An **extent** = `(logical_start, physical_start, length)` — one extent can cover a contiguous range, so a 1GB sequential file might need only a few extents instead of 262,144 individual block pointers.

```
 Inode
 ┌──────────────────────────────┐
 │  Extent Tree Root            │
 │  ┌────────────────────────┐  │
 │  │ extent 1:              │  │
 │  │   logical block 0-3    │──┼──► disk blocks 4263936-4263939  (16KB)
 │  └────────────────────────┘  │
 └──────────────────────────────┘
```

```shell
# debugfs: ext2/ext3/ext4 filesystem debugger (interactive or one-shot)
#   -R "cmd" : run a single command and exit (non-interactive)
#   "stat <inode>" : show inode details including extent tree
#   /dev/vda1 : the filesystem device to inspect
$ debugfs -R "stat <131088>" /dev/vda1
Inode: 131088   Type: regular    Mode:  0644   Flags: 0x80000
...
Size: 12500
EXTENTS:
(0-3): 4263936-4263939       ◄── logical blocks 0-3 → physical blocks 4263936-4263939

# filefrag: report on file fragmentation
#   -v : verbose, show detailed extent mapping
$ filefrag -v /home/user/file.txt
Filesystem type is: ef53
File size of /home/user/file.txt is 12500 (4 blocks of 4096 bytes)
 ext:     logical_offset:        physical_offset: length:   expected: flags:
   0:        0..       3:    4263936..   4263939:      4:             last,eof

# for a larger, fragmented file you'd see multiple extents:
# ext:     logical_offset:        physical_offset: length:
#   0:        0..    1023:       8001..      9024:   1024:          ◄── 4MB contiguous
#   1:     1024..    2047:      20000..     21023:   1024:   9025   ◄── 4MB elsewhere (fragmented)
```

## Step 4: Physical Block → Read from Disk
Now the kernel knows the exact disk location. It reads the physical blocks.

```shell
# dd: read raw bytes from disk, bypassing the filesystem entirely
#   if=/dev/vda1 : read from the raw disk device
#   bs=4096      : read in 4096-byte blocks (matching filesystem block size)
#   skip=4263936 : skip to physical block 4263936
#   count=4      : read 4 blocks (16KB, enough for our 12500-byte file)
# head -c 12500 : trim to exact file size (discard padding from last block)
$ dd if=/dev/vda1 bs=4096 skip=4263936 count=4 2>/dev/null | head -c 12500
# (outputs the raw file content — same as cat /home/user/file.txt)

# diff: compare two inputs, no output means identical
# <(...) : process substitution, feeds command output as a "file"
$ diff <(dd if=/dev/vda1 bs=4096 skip=4263936 count=4 2>/dev/null | head -c 12500) /home/user/file.txt
# (no output = identical)
```

## Quick Reference
```shell
# putting it all together for any file on your system:

# 1. pathname → inode number
# stat -c "%i" : custom format output, %i = inode number
$ stat -c "%i" /home/user/file.txt
131088

# 2. inode → which block group and where in the inode table
$ dumpe2fs /dev/vda1 2>/dev/null | grep "Inodes per group"
# calculate: group = (inode - 1) / inodes_per_group

# 3. inode → physical disk blocks (extent mapping)
$ filefrag -v /home/user/file.txt
# or
$ debugfs -R "stat <131088>" /dev/vda1

# 4. physical blocks → raw data
$ dd if=/dev/vda1 bs=4096 skip=<physical_block> count=<num_blocks>
```

## Reference
- [ext4 disk layout -- kernel doc](https://www.kernel.org/doc/html/latest/filesystems/ext4/overview.html)
- [ext4 extent tree -- kernel doc](https://www.kernel.org/doc/html/latest/filesystems/ext4/dynamic.html#extent-tree)
