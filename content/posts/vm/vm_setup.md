---
title: "VictoriaMetrics Cluster Setup"
date: "2026-03-11T17:03:50+08:00"
tags: ["victoriametrics"]
description: "VictoriaMetrics Cluster Setup in one server with systemd"
---
Setup each VictoriaMetrics component as a systemd service on a single server. This guide covers building from source, configuring services, and verifying the setup.

If you prefer to setup in one step, just go with [docker-compose](https://github.com/VictoriaMetrics/VictoriaMetrics/tree/master/deployment/docker#victoriametrics-cluster). 

## Architecture

```
vmagent :8429  →  vminsert :8480  →  vmstorage :8400 (write port)
                                               :8401 (read port)
Grafana        →  vmselect :8481  →  vmstorage :8401
```

| Component | HTTP/UI | Internal port |
|-----------|---------|---------------|
| vmstorage | `:8482` | `:8400` (from vminsert), `:8401` (from vmselect) |
| vminsert  | `:8480` | — |
| vmselect  | `:8481` | — |
| vmagent   | `:8429` | — |

---

## Step 1: Prerequisites

```bash
go version   # 1.22+ required

sudo useradd --system --no-create-home --shell /usr/sbin/nologin victoriametrics
```

---

## Step 2: Build from Source

Cluster components (`vminsert`, `vmselect`, `vmstorage`) have Makefile targets only on the **`cluster` branch**.

```bash
git fetch origin
git checkout -b cluster origin/cluster
```

**Development build** (no Docker required):
```bash
make all   # builds bin/vminsert, bin/vmselect, bin/vmstorage
```

**Production build** (statically linked, requires Docker for builder container):
```bash
make vminsert-prod vmselect-prod vmstorage-prod
```

**Cross-compile for Linux from macOS:**
```bash
make vminsert-linux-amd64-prod vmselect-linux-amd64-prod vmstorage-linux-amd64-prod
```

**vmagent** is built from `master`:
```bash
# on master branch
make vmagent        # dev build → bin/vmagent
make vmagent-prod   # production build → bin/vmagent-prod
```

**Install binaries:**

`install` copies the file and sets ownership/permissions in one step (equivalent to `cp` + `chmod`).
`-m 755` sets the file permission mode in octal notation:

```
octal  who     permissions
  7    owner   read(4) + write(2) + execute(1)  →  rwx
  5    group   read(4) + execute(1)              →  r-x
  5    others  read(4) + execute(1)              →  r-x
```

Binaries need execute permission for everyone so systemd (running as `victoriametrics`) can launch them,
but only root (owner) can overwrite them.

```bash
# Development build output has no -prod suffix (from `make all`)
sudo install -m 755 bin/vminsert  /usr/local/bin/vminsert
sudo install -m 755 bin/vmselect  /usr/local/bin/vmselect
sudo install -m 755 bin/vmstorage /usr/local/bin/vmstorage
sudo install -m 755 bin/vmagent   /usr/local/bin/vmagent
```

---

## Step 3: Create Directories

Two different owners for two different purposes:
- `/etc/vmagent/` — config, owned by **root** (only admins should modify it)
- `/var/lib/` dirs — runtime data, owned by **victoriametrics** (the service writes here)

```bash
# Config dir: root-owned (admins create/edit configs with sudo)
sudo mkdir -p /etc/vmagent

# Data dirs: service user-owned (vmstorage and vmagent write runtime data here)
sudo mkdir -p /var/lib/vmstorage
sudo mkdir -p /var/lib/vmagent
sudo chown victoriametrics:victoriametrics /var/lib/vmstorage /var/lib/vmagent
```

---

## Step 4: vmagent Scrape Config

Create and edit config files as **root** (`sudo`). The `victoriametrics` service user only needs to read them.

`/etc/vmagent/scrape.yml`:

```bash
sudo vim /etc/vmagent/scrape.yml   # create/edit as root

```

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: vmstorage
    static_configs:
      - targets: ['localhost:8482']

  - job_name: vminsert
    static_configs:
      - targets: ['localhost:8480']

  - job_name: vmselect
    static_configs:
      - targets: ['localhost:8481']

  - job_name: vmagent
    static_configs:
      - targets: ['localhost:8429']
```

---

## Step 5: systemd Service Files

### vmstorage — `/etc/systemd/system/vmstorage.service`

```ini
[Unit]
Description=VictoriaMetrics Storage
After=network.target

[Service]
Type=simple
User=victoriametrics
Group=victoriametrics
ExecStart=/usr/local/bin/vmstorage \
    -storageDataPath=/var/lib/vmstorage \
    -retentionPeriod=1M \
    -httpListenAddr=:8482 \
    -vminsertAddr=:8400 \
    -vmselectAddr=:8401 \
    -loggerFormat=json
TimeoutStopSec=120
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

### vminsert — `/etc/systemd/system/vminsert.service`

```ini
[Unit]
Description=VictoriaMetrics Insert
After=network.target vmstorage.service

[Service]
Type=simple
User=victoriametrics
Group=victoriametrics
ExecStart=/usr/local/bin/vminsert \
    -storageNode=localhost:8400 \
    -httpListenAddr=:8480 \
    -loggerFormat=json
TimeoutStopSec=30
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

### vmselect — `/etc/systemd/system/vmselect.service`

```ini
[Unit]
Description=VictoriaMetrics Select
After=network.target vmstorage.service

[Service]
Type=simple
User=victoriametrics
Group=victoriametrics
ExecStart=/usr/local/bin/vmselect \
    -storageNode=localhost:8401 \
    -httpListenAddr=:8481 \
    -loggerFormat=json
TimeoutStopSec=30
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

### vmagent — `/etc/systemd/system/vmagent.service`

```ini
[Unit]
Description=VictoriaMetrics Agent
After=network.target vminsert.service

[Service]
Type=simple
User=victoriametrics
Group=victoriametrics
ExecStart=/usr/local/bin/vmagent \
    -promscrape.config=/etc/vmagent/scrape.yml \
    -remoteWrite.url=http://localhost:8480/insert/0/prometheus/api/v1/write \
    -remoteWrite.queues=2 \
    -remoteWrite.tmpDataPath=/var/lib/vmagent \
    -httpListenAddr=:8429 \
    -loggerFormat=json
ExecReload=/bin/kill -HUP $MAINPID
TimeoutStopSec=30
Restart=on-failure
RestartSec=5s
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
```

---

## Step 6: Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable vmstorage vminsert vmselect vmagent

# Start in order
sudo systemctl start vmstorage
sudo systemctl start vminsert vmselect
sudo systemctl start vmagent
```

---

## Step 7: Verify

```bash
# Health checks (all should return "OK")
curl http://localhost:8482/health   # vmstorage
curl http://localhost:8480/health   # vminsert
curl http://localhost:8481/health   # vmselect
curl http://localhost:8429/health   # vmagent

# Query data via vmselect
curl "http://localhost:8481/select/0/prometheus/api/v1/query?query=up"

# Check vmagent scrape targets
curl http://localhost:8429/targets

# Follow logs
journalctl -u 'vm*' -f
```

---

## Key Notes

- `vminsert -storageNode` points to vmstorage port **`:8400`** (write)
- `vmselect -storageNode` points to vmstorage port **`:8401`** (read) — different port, different protocol
- `vmagent -remoteWrite.url` uses `accountID=0` (default tenant): `/insert/0/prometheus/api/v1/write`
- vmstorage needs `TimeoutStopSec=120` — it flushes in-memory data on SIGTERM
- Phase 2 scaling: add more `-storageNode` flags to vminsert/vmselect; put vmauth in front as load balancer

## References:
- [How to install grafana](https://grafana.com/docs/grafana/latest/setup-grafana/installation/debian/)
