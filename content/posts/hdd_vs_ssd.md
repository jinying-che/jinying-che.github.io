---
title: "HDD vs SSD"
date: "2026-03-17T10:18:40+08:00"
tags: ["hardware", "storage"]
description: "Deep dive into HDD and SSD: how they work, performance characteristics, and when to use which"
draft: true
---

## Overview

Storage drives are one of the biggest bottlenecks in modern computing. Understanding how HDD and SSD work internally helps explain why SSDs feel so much faster and why HDDs still have a place.

## HDD (Hard Disk Drive)

### How It Works

An HDD is a **mechanical** device. Data is stored as magnetic patterns on spinning circular platters.

```
            Spindle
               |
       ========|========     <-- Platter (spinning disk)
      /        |        \
     /    Track 0        \
    |   +-----------+     |
    |   | Sector    |     |   <-- Data stored in sectors
    |   +-----------+     |
     \                   /
      \                 /
       =================
               ^
               |
          Read/Write Head
          (on actuator arm)
```

Key components:
- **Platters**: Glass or aluminum disks coated with magnetic material, spinning at 5400/7200/10000/15000 RPM
- **Read/Write Head**: Floats ~10nm above the platter surface on an air cushion
- **Actuator Arm**: Moves the head across the platter to reach different tracks
- **Spindle Motor**: Spins the platters at constant RPM

### Reading Data — 3 Delays

When the OS requests data at a specific LBA (Logical Block Address), the HDD must:

```
1. Seek         2. Rotational Latency    3. Transfer
   Move head       Wait for sector to        Read the
   to correct      rotate under head         data bits
   track

   ~4-10ms         ~2-6ms (avg half         ~0.05ms/sector
                    rotation)
```

**Total latency for random read ≈ 6-16ms**

This is why random I/O is HDD's weakness — each random read pays the full seek + rotation penalty.

### Sequential vs Random I/O

```
Sequential Read:   Head stays on track, sectors pass under it continuously
                   Throughput: 100-200 MB/s

Random Read:       Each read = seek + rotation + transfer
                   IOPS: ~75-200 (yes, only 75-200 operations per second)
                   Effective throughput for 4KB random reads:
                   150 IOPS × 4KB = 0.6 MB/s   <-- this is why HDDs feel slow
```

## SSD (Solid State Drive)

### How It Works

An SSD has **no moving parts**. Data is stored in NAND flash memory cells as trapped electrons.

```
SSD Architecture:

  Host Interface (SATA / NVMe)
         |
    ┌────┴────┐
    │ SSD     │
    │Controller│  <-- The brain: FTL, wear leveling, garbage collection
    │ (CPU)   │
    └────┬────┘
         |
    ┌────┴──────────────────────┐
    │   DRAM Cache              │  <-- Maps logical → physical addresses
    └────┬──────────────────────┘
         |
    ┌────┴────┬─────────┬─────────┐
    │ Channel │ Channel │ Channel │ ...  (4-8 channels typically)
    │    0    │    1    │    2    │
    └────┬────┘────┬────┘────┬────┘
         │         │         │
      ┌──┴──┐  ┌──┴──┐  ┌──┴──┐
      │NAND │  │NAND │  │NAND │   <-- Flash chips (dies/packages)
      │Chip │  │Chip │  │Chip │
      └─────┘  └─────┘  └─────┘
```

### NAND Flash Cell Types

Each cell stores data by trapping electrons in a floating gate. More bits per cell = more density but less endurance.

```
Voltage levels per cell type:

SLC (1 bit/cell):   |  0  |  1  |                    Fast, durable, expensive
                     +-----------+

MLC (2 bits/cell):  | 00 | 01 | 10 | 11 |            Balanced
                     +---+----+----+-----+

TLC (3 bits/cell):  |000|001|010|011|100|101|110|111|  Common in consumer SSDs
                     +---+---+---+---+---+---+---+---+

QLC (4 bits/cell):  16 voltage levels                  Highest density, lowest endurance
```

| Type | Bits/Cell | Endurance (P/E cycles) | Read Latency | Use Case |
|------|-----------|----------------------|--------------|----------|
| SLC  | 1         | ~100,000             | ~25 μs       | Enterprise, cache |
| MLC  | 2         | ~10,000              | ~50 μs       | Enterprise |
| TLC  | 3         | ~1,000-3,000         | ~75 μs       | Consumer |
| QLC  | 4         | ~100-1,000           | ~100 μs      | Read-heavy, archival |

### NAND Organization Hierarchy

```
SSD
 └── Die (one or more per package)
      └── Plane (typically 2-4 per die)
           └── Block (smallest ERASE unit, e.g., 512 pages)
                └── Page (smallest READ/WRITE unit, e.g., 4-16 KB)
                     └── Cell (stores 1-4 bits)
```

This hierarchy matters because of a critical constraint:

> **You can READ/WRITE at page granularity, but you can only ERASE at block granularity.**

### The Write Amplification Problem

```
Scenario: Update 4KB of data in a block

Block (256 pages):
┌───┬───┬───┬───┬───┬─────┬───┐
│ P0│ P1│ P2│ P3│ P4│ ... │P255│   Original block (all pages valid)
└───┴───┴───┴───┴───┴─────┴───┘
         ^
         Want to update P2

Step 1: Write new P2 to a FREE page in another block
        Mark old P2 as "invalid" (stale)

Step 2: Eventually, garbage collection kicks in:
        - Copy all VALID pages from old block to new block
        - Erase old block
        - Now old block is free again

This means: updating 4KB might cause copying of an entire block (1-4 MB)
            Write Amplification Factor (WAF) = actual writes / host writes
```

### Flash Translation Layer (FTL)

The FTL is firmware in the SSD controller that abstracts NAND complexity from the OS.

Key responsibilities:
- **Logical-to-Physical mapping**: OS sees LBAs, FTL maps them to physical pages (stored in DRAM)
- **Wear leveling**: Distributes writes evenly across all blocks so no single block wears out early
- **Garbage collection**: Reclaims blocks with stale pages in the background
- **Bad block management**: Marks and avoids failed blocks
- **Over-provisioning**: Reserves ~7-28% of NAND for GC and wear leveling headroom

### TRIM

When the OS deletes a file, it only removes the filesystem metadata. The SSD doesn't know those pages are free.

```
Without TRIM:
  OS deletes file → SSD still thinks pages are valid → GC copies stale data → waste

With TRIM:
  OS deletes file → sends TRIM command → SSD marks pages as invalid → GC skips them
```

TRIM helps maintain SSD performance over time by giving the controller accurate information about which pages are actually in use.

## Interface Comparison: SATA vs NVMe

```
SATA SSD:
  CPU ←→ SATA Controller ←→ AHCI ←→ SSD
  - 1 command queue, 32 commands deep
  - Max bandwidth: ~600 MB/s (SATA III)
  - Latency: ~100 μs

NVMe SSD:
  CPU ←→ PCIe Bus ←→ NVMe ←→ SSD
  - 65,535 queues, 65,536 commands each
  - Max bandwidth: ~3,500-7,000+ MB/s (PCIe 3.0 x4 / 4.0 x4)
  - Latency: ~10-20 μs
```

NVMe was designed specifically for flash storage, while AHCI/SATA was designed for spinning disks.

## Head-to-Head Comparison

| Metric | HDD | SATA SSD | NVMe SSD |
|--------|-----|----------|----------|
| Sequential Read | 100-200 MB/s | 500-550 MB/s | 3,000-7,000 MB/s |
| Sequential Write | 100-200 MB/s | 450-520 MB/s | 2,000-5,000 MB/s |
| Random Read (4K) IOPS | 75-200 | 50,000-100,000 | 200,000-1,000,000+ |
| Random Write (4K) IOPS | 75-200 | 40,000-90,000 | 100,000-500,000+ |
| Latency (random read) | 6-16 ms | ~100 μs | ~10-20 μs |
| Power (active) | 6-8 W | 2-3 W | 5-8 W |
| Power (idle) | 4-6 W | 0.05 W | 0.03 W |
| Cost per TB | ~$15-25 | ~$50-80 | ~$60-100 |
| Capacity (max) | 20+ TB | 8 TB | 8 TB |
| Endurance | Nearly unlimited R/W | Limited P/E cycles | Limited P/E cycles |
| Shock resistance | Low (mechanical) | High (no moving parts) | High |

The random I/O difference is the most impactful:
- HDD random read latency: **~10 ms** (10,000,000 ns)
- NVMe random read latency: **~10 μs** (10,000 ns)
- That's a **1000x** difference

## When to Use Which

| Use Case | Recommendation | Reason |
|----------|---------------|--------|
| OS / Boot drive | NVMe SSD | Lots of random I/O (loading libraries, configs, etc.) |
| Database (OLTP) | NVMe SSD | Random reads dominate; latency matters |
| Video editing / large files | SATA SSD or HDD | Sequential I/O; HDD is acceptable for cold storage |
| Backup / archival | HDD | Cost per TB is much lower; sequential writes |
| Log storage | HDD or QLC SSD | Write-heavy but sequential; cost matters |
| Caching layer | SLC/MLC SSD | High endurance needed for frequent writes |

## Key Takeaways

1. **HDD bottleneck is mechanical**: seek time + rotational latency makes random I/O terrible (~100 IOPS)
2. **SSD's advantage is parallelism + no moving parts**: multiple channels, no seek/rotation penalty (~100K-1M IOPS)
3. **NAND has quirks**: read/write at page level, erase at block level → write amplification, need for GC and TRIM
4. **NVMe >> SATA** for SSDs because AHCI was designed for spinning disks (1 queue vs 65K queues)
5. **HDD still wins on cost/TB and capacity** for bulk storage and archival workloads
