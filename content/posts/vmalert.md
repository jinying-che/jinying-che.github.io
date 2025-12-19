---
title: "vmalert overview"
date: "2024-10-23T09:59:27+08:00"
tags: ["monitor", "victoriametrics"]
description: "a brief introduction to vmalert"
draft: true
---

## General
### Reload rule files

## Alerting Rule
in cron job: loading rule files -> group -> start -> execute -> query -> remote write | notify -> loop 

### Alert Status
### Alert Query
### Notification
1. EndAt 

2. resend delay


## Recording Rule

## Source Code
https://github.com/VictoriaMetrics/VictoriaMetrics
- `app/vmalert/group.go`

basically check 2 parts:
1. how `Group` is built
2. how `Group` is executed

