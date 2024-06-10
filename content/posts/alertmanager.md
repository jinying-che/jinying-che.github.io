---
title: "alertmanager"
date: "2024-05-29T08:54:49+08:00"
tags: ["monitor"]
description: "alertmanager overview"
---

### Architecture
![arch](/images/alertmanager.png)

### Design
##### 1. No dedicated status (e.g. firing or resolved)
differentiate the alert by `EndAt` timestamp
##### 2. group_wait vs group_interval vs repeat_interval
![group](/images/am_group.png)

### Source Code
1. **Entrance**
- api: `api/v2/api.go`
- dispatch: `dispatch/dispatch.go`
