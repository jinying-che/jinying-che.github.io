---
title: "Victorial Metrics"
date: "2024-02-13T07:37:29+08:00"
tags: ["monitor", "Victoria Metrics"]
description: "Victorial Metrics"
draft: true
---

## Storage
### On Disk Layout
```txt
./data
├── big
│   ├── 2024_01
│   │   ├── 17A6101707C91B08
│   │   │   ├── index.bin
│   │   │   ├── metadata.json
│   │   │   ├── metaindex.bin
│   │   │   ├── timestamps.bin
│   │   │   └── values.bin
│   ├── 2024_02
│   ├── ...
│   └── snapshots
│       ├── 20240109092239-179E85E399D5EFDA
│       │   ├── 2023_12
│       │   └── 2024_01
│       └── 20240111104529-179E85E399D5EFDB
│           ├── 2023_12
│           └── 2024_01
├── flock.lock
└── small
    ├── 2024_01
    │   ├── 17A6101707CC58EF
    │   │   ├── index.bin
    │   │   ├── metadata.json
    │   │   ├── metaindex.bin
    │   │   ├── timestamps.bin
    │   │   └── values.bin
    └── snapshots
        ├── 20240109092239-179E85E399D5EFDA
        │   ├── 2023_12
        │   └── 2024_01
        └── 20240111104529-179E85E399D5EFDB
            ├── 2023_12
            └── 2024_01

```
For details, see [doc](https://docs.victoriametrics.com/single-server-victoriametrics/#storage)

### Writing Data Flow

VM vs Prometheus (Disk)
TBD

## Referrence
- https://docs.victoriametrics.com/single-server-victoriametrics/
- https://github.com/VictoriaMetrics/VictoriaMetrics/issues/3268
