---
title: "Buffer vs Cache"
date: "2026-05-04T16:08:41+08:00"
tags: ["linux"]
description: "Buffer vs Cache in Linux — what each really caches, how free and /proc/meminfo define them, and how to verify"
---

## The Common Misconception

```
Buffer is for write, Cache is for read   →  WRONG
```

Both go through the kernel's page-allocator-backed cache, and both serve **reads and writes**. The real distinction is **what kind of data each one holds**, and **where that data lives on disk**:

- **Buffer** caches **block-device** I/O — filesystem **metadata** (superblock, inode tables, directory blocks, journal, …)
- **Cache** (the `cache` column in `free`) caches **file content** *and* **kernel object slabs** (dentry/inode caches)

Once you internalise that, the rest follows.

## The Strict Definitions

`free`'s output is the friendly summary; `/proc/meminfo` is the source of truth.

```
                  ┌─────────────────────────────────────────────┐
                  │              Disk (/dev/vda1)               │
                  │                                             │
                  │  ┌───────────┐         ┌─────────────────┐  │
                  │  │  Metadata │         │  File Content   │  │
                  │  │ (the map) │         │ (the treasure)  │  │
                  │  └─────┬─────┘         └────────┬────────┘  │
                  └────────┼────────────────────────┼───────────┘
                           │                        │
                           ▼                        ▼
                       ┌────────┐             ┌────────────┐
                       │ Buffer │             │ Page Cache │
                       │        │             │            │
                       │ Buffers│             │   Cached   │ ← /proc/meminfo
                       └────────┘             └────────────┘
                                                    +
                                              ┌────────────────┐
                                              │ Reclaimable    │
                                              │ Slab (dentry / │
                                              │ inode caches)  │
                                              │ SReclaimable   │ ← /proc/meminfo
                                              └────────────────┘
                                              ◄──── "cache" in free ────►
```

| Term | Meaning | Source field |
|---|---|---|
| **Buffer** | Block-device I/O cache (filesystem metadata) | `Buffers` |
| **Page Cache** | File-backed pages: regular file content + tmpfs/shmem | `Cached` |
| **Reclaimable Slab** | Kernel object caches the kernel will hand back under pressure (dentry, inode, …) | `SReclaimable` |
| **`cache` (in `free`)** | Page Cache + Reclaimable Slab | `Cached + SReclaimable` |
| **`buffers` (in `free`)** | Buffer | `Buffers` |

> **Cache ≠ Page Cache.** "Page cache" is a strict kernel subsystem (`Cached`). "Cache" as reported by `free` is broader — it bundles page cache *and* reclaimable kernel slabs.

## Mapping `free` ↔ `/proc/meminfo`

```shell
$ free
              total      used      free    shared  buff/cache   available
Mem:         980508    183624     74136       348      722748      631876

$ cat /proc/meminfo | grep -E "^(Buffers|Cached|SReclaimable):"
Buffers:           85092 kB
Cached:           571860 kB
SReclaimable:      65796 kB
```

The arithmetic:

```
buffers (free)        = Buffers                     =  85092 kB
cache   (free)        = Cached + SReclaimable       = 571860 + 65796 = 637656 kB
buff/cache (free)     = Buffers + Cached + SReclaimable           = 722748 kB ✓
```

(Older `free` versions print `buffers` and `cache` as separate columns; newer ones merge them into `buff/cache`. Use `free -w` to see them split.)

## What's Inside Each Region

| Region | What it caches | Examples | Grows when… |
|---|---|---|---|
| **Buffer** (`Buffers`) | **Raw on-disk metadata blocks** (read via the block device) | Superblock block, **inode table blocks** (raw bytes), **directory data blocks** (raw `(name, inode#)` entries), free-block bitmap, ext4 journal blocks | `mount`, `mkfs`, `fsck`, `dd if=/dev/vda1`, opening many files |
| **Page Cache** (`Cached`) | File-backed pages | `/var/log/syslog` content, mmap'd files, tmpfs / shmem pages | `cat file`, `read()`, `write()`, mmap |
| **Reclaimable Slab** (`SReclaimable`) | **Parsed in-memory kernel structs** the kernel can drop on demand | **`struct dentry`** (no on-disk form — parsed pathname component), **`struct inode`** (parsed from inode-table block, with extra runtime state), other reclaimable kmem | `ls`, `find`, `stat` — anything that walks the filesystem tree |

> **Why the apparent overlap?** "Inode" and "directory" each have **two cache forms**: the raw on-disk block lives in **Buffer**, while the parsed kernel struct (`struct inode`, `struct dentry`) lives in **Reclaimable Slab**. The dentry is special — it has *no* on-disk form; what's on disk is the directory's data block, and the dentry is purely the in-memory parsed result.

```
 Disk                                    Memory
 ────                                    ──────
 [ inode table block ]  ──read()────►  [ Buffer page ]      ← raw bytes
                                              │
                                              │ parse
                                              ▼
                                       [ struct inode ]     ← Reclaimable Slab
                                       (in inode_cache slab)

 [ directory data block ] ──read()──►  [ Buffer page ]      ← raw bytes
                                              │
                                              │ parse
                                              ▼
                                       [ struct dentry ]    ← Reclaimable Slab
                                       (in dentry slab)
```

## A Concrete Example: `cat /home/user/file.txt`

```
 ① lookup inode of "/"           → Buffer       (superblock, root inode block)
                                 → Slab         (dentry "/" + inode struct)
 ② lookup "home" in "/"          → Buffer       (directory data block of "/")
                                 → Slab         (dentry "home" + inode struct)
 ③ lookup "user" in "home"       → Buffer       (directory data block of "home")
                                 → Slab         (dentry "user" + inode struct)
 ④ lookup "file.txt" in "user"   → Buffer       (directory block + inode block)
                                 → Slab         (dentry "file.txt" + inode struct)
 ⑤ inode extent tree → blocks [1024, 1025, 1026]
 ⑥ read blocks 1024–1026         → Page Cache   (the actual file bytes)
     │
     ▼
 copy_to_user() → terminal shows the content
```

Steps ①–④ are split between **Buffer** (raw on-disk metadata blocks) and **Reclaimable Slab** (the in-memory dentry/inode structs the VFS hands back on the next lookup). Step ⑥ is the only **Page Cache** work — the file content the user actually sees.

For a small file, the kernel does *more metadata I/O than content I/O* — it's just invisible to you.

## Verify with `free` + `slabtop`

```shell
# baseline: drop everything
$ echo 3 > /proc/sys/vm/drop_caches && free -w
              total   used    free  shared  buffers   cache  available
Mem:         980508 183624  750000     348     2000   44884     750000

# (1) read a FILE → page cache grows
$ cat /var/log/syslog > /dev/null && free -w
              total   used    free  shared  buffers   cache  available
Mem:         980508 183624  700000     348     2000   94884     750000
#                                                       ↑
#                                                   page cache up

# (2) read raw BLOCK DEVICE → buffer grows
$ dd if=/dev/vda1 of=/dev/null bs=1M count=64 && free -w
              total   used    free  shared  buffers   cache  available
Mem:         980508 183624  634000    348    67000    94884     750000
#                                              ↑
#                                          buffer up

# (3) walk a directory tree → reclaimable slab (dentries/inodes) grows
$ find /usr > /dev/null && free -w
              total   used    free  shared  buffers   cache  available
Mem:         980508 183624  580000    348    67000   148884     750000
#                                                       ↑
#                                          reclaimable slab up

# cross-check with slabtop
$ slabtop -o | head -5
 Active / Total Objects (% used)    : 412350 / 521240 (79.1%)
  OBJS ACTIVE  USE OBJ SIZE  SLABS OBJ/SLAB CACHE SIZE NAME
 94350  76935  81%    0.19K   4493       21    17972K dentry
 32760  31200  95%    1.05K   1170       28    37440K ext4_inode_cache
```

## `drop_caches` Semantics

```shell
echo 1 > /proc/sys/vm/drop_caches   # page cache (incl. buffer pages — see note)
echo 2 > /proc/sys/vm/drop_caches   # dentries + inodes (reclaimable slab)
echo 3 > /proc/sys/vm/drop_caches   # both
```

| Value | Drops | `free` columns affected |
|---|---|---|
| `1` | Page cache pages (which also backs buffers since 2.4+) | `buffers`, `cache` (the page-cache part) |
| `2` | Dentry cache + inode cache (reclaimable slab) | `cache` (the slab part) |
| `3` | Everything above | `buffers` + `cache` |

> Use only for testing/troubleshooting. The kernel reclaims these automatically under memory pressure — manually dropping them in production just makes the next access slower.

## Implementation Note: Buffer Is Backed by Page Cache (≥ Linux 2.4)

Historically, Linux had two **separate** memory pools — the buffer cache (block-aligned) and the page cache (page-aligned) — which led to double-caching of the same data.

Since Linux 2.4, they were unified: a `buffer_head` is just a **descriptor** pointing into a page in the page cache.

```
            Page Cache (one pool of 4KB pages)
            ┌────────────────────────────────────────┐
            │  Page  │  Page  │  Page  │  Page  │ …  │
            └────▲───┴────▲───┴────────┴────▲───┴────┘
                 │        │                 │
            buffer_head buffer_head    (file-content
            (metadata)  (metadata)      page, no bh)
```

That's why `free` reports them together as `buff/cache`, and why `echo 1 > drop_caches` reclaims both — they live in the same pool.

`Source code`: [`buffer_head` (`include/linux/buffer_head.h`)](https://github.com/torvalds/linux/blob/master/include/linux/buffer_head.h), [page cache (`mm/filemap.c`)](https://github.com/torvalds/linux/blob/master/mm/filemap.c)

## Cheat Sheet

| Question | Answer |
|---|---|
| Is "cache" the same as "page cache"? | **No.** `cache` in `free` = `Cached + SReclaimable`. Page cache is just the `Cached` part. |
| What does Buffer cache? | Filesystem **metadata** (superblock, inode tables, directory blocks, journal). |
| What does Page Cache cache? | File **content** (regular files, tmpfs, mmap'd files). |
| What's in `SReclaimable`? | Dentry cache, inode cache, and other reclaimable kernel slabs. |
| Buffer = writes, Cache = reads? | **No.** Both serve reads and writes. The split is by data type, not direction. |
| Are Buffer and Page Cache separate memory pools? | No (since Linux 2.4). Buffer is backed by page cache pages via `buffer_head` descriptors. |
| Should I worry about high `buff/cache`? | No. It's reclaimable. Watch `available`, not `free`. |

## Reference
- [Linux Page Cache — kernel doc](https://www.kernel.org/doc/html/latest/admin-guide/mm/concepts.html#page-cache)
- [`/proc/meminfo` fields — kernel doc](https://www.kernel.org/doc/html/latest/filesystems/proc.html#meminfo)
- [`drop_caches` — kernel doc](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html#drop-caches)
- `man free`, `man proc`, `man slabtop`
