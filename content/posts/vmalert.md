---
title: "vmalert overview"
date: "2024-10-23T09:59:27+08:00"
tags: ["monitor", "victoria metrics"]
description: "a brief introduction to vmalert"
draft: true
---

## Alerting Rule
in cron job: loading rule files -> group -> start -> execute -> query -> remote write | notify -> loop 

1. reload rule files
2. 

## Recording Rule

## Source Code
https://github.com/VictoriaMetrics/VictoriaMetrics
- `app/vmalert/group.go`

basically check 2 parts:
1. how `Group` is built
2. how `Group` is executed

