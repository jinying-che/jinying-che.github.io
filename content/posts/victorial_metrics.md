---
title: "Victorial Metrics"
date: "2024-02-13T07:37:29+08:00"
tags: ["monitor", "Victoria Metrics"]
description: "Victorial Metrics"
---

## Quick Start

**Victoria Metrics**
- An easy way to run VictoriaMetrics locally is to build from the [source code](https://docs.victoriametrics.com/single-server-victoriametrics/#how-to-build-from-sources) as there're lots of vm binaries like vmselect, vmstorage, vminsert, etc. to download, and all of them are maintained in the same [repository](https://github.com/VictoriaMetrics/VictoriaMetrics), and `Makefile` is quite straightforward.
```bash
git clone git@github.com:VictoriaMetrics/VictoriaMetrics.git
make victoria-metrics
mv /bin/victoria-metrics /usr/bin
```

- Run VictoriaMetrics With Systemd
```bash
[Unit]
Description="Victoria Metrics Single"
Documentation=https://https://docs.victoriametrics.com/
After=network.target

[Service]
Type=simple

ExecStart=/usr/bin/victoria-metrics-prod \
        -storageDataPath=/data/vm \
        -httpListenAddr=:8428 \
        -promscrape.config=/etc/prometheus/scrape.yml
ExecStop=/bin/kill -s SIGTERM $MAINPID

Restart=on-failure
SuccessExitStatus=0
LimitNOFILE=65536
StandardOutput=/var/log/vm/out.log
StandardError=/var/log/vm/err.log
SyslogIdentifier=prometheus

[Install]
WantedBy=multi-user.target
```

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
