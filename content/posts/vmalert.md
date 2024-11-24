---
title: "vmalert overview"
date: "2024-10-23T09:59:27+08:00"
tags: ["monitor", "victoria metrics"]
description: "a brief introduction to vmalert"
draft: true
---

## General Flow
in cron job: loading rule files -> group -> start -> execute -> remote write | notify -> loop 

## Source Code
https://github.com/VictoriaMetrics/VictoriaMetrics
- `app/vmalert/group.go`

basically check 2 parts:
1. how `Group` is built
2. how `Group` is executed
