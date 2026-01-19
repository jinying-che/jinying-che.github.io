---
title: "alertmanager"
date: "2024-05-29T08:54:49+08:00"
tags: ["monitor"]
description: "alertmanager overview"
---

# Architecture
![arch](/images/alertmanager.png)

# Design
## 1. Alert State Machine
alertmanager maintains the following states for the alert processing:
### unprocessed -> active -> suppressed

```go
// type/type.go
AlertStateUnprocessed AlertState = "unprocessed"
AlertStateActive      AlertState = "active"
AlertStateSuppressed  AlertState = "suppressed"
```

### firing vs resolved
alertmanager only check the firing or resolved status during the notify, differentiate the alert by `EndAt` timestamp, for example:
```go
// notify/notify.go 

// RetryStage filters resolved alerts based on config:
// If we shouldn't send notifications for resolved alerts, but there are only
// resolved alerts, report them all as successfully notified (we still want the
// notification log to log them for the next run of DedupStage).
if !r.integration.SendResolved() {
    firing, ok := FiringAlerts(ctx)
    if !ok {
        return ctx, nil, errors.New("firing alerts missing")
    }
    if len(firing) == 0 {
        return ctx, alerts, nil
    }
    for _, a := range alerts {
        if a.Status() != model.AlertResolved {
            sent = append(sent, a)
        }
    }
} else {
    sent = alerts
}
```

## 2. group_wait vs group_interval vs repeat_interval
![group](/images/am_group.png)

##Source Code
1. **Entrance**
- api: `api/v2/api.go`
- dispatch: `dispatch/dispatch.go`
- silence label parse: `cli/silence_add.go:func (c *silenceAddCmd) add`
