---
title: "vmalert overview"
date: "2024-10-23T09:59:27+08:00"
tags: ["monitor", "victoriametrics"]
description: "a brief introduction to vmalert"
draft: true
---
## Architecture
![vmalert](/images/vmalert.png)

## General
### Reload rule files

## Alerting Rule
### Flow 
in cron job: loading rule files -> group -> start -> execute -> query -> update alert -> remote write | notify -> loop 

### State Machine
TBD: Graph

## Recording Rule

## Source Code
https://github.com/VictoriaMetrics/VictoriaMetrics
- `app/vmalert/group.go`

basically check 2 parts:
1. how `Group` is built
2. how `Group` is executed

