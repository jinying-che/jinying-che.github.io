---
title: "vmagent"
date: "2025-10-27T16:07:28+08:00"
tags: ["victoriametrics"]
description: "vmagent overview"
draft: true
---

## Troubleshooting
vmagent also exports the status for various targets at the following pages:

- http://vmagent-host:8429/targets. This pages shows the current status for every active target.
- http://vmagent-host:8429/service-discovery. This pages shows the list of discovered targets with the discovered __meta_* labels according to these docs . This page may help debugging target relabeling .
- http://vmagent-host:8429/api/v1/targets. This handler returns JSON response compatible with the corresponding page from Prometheus API .
- http://vmagent-host:8429/ready. This handler returns http 200 status code when vmagent finishes its initialization for all the service_discovery configs . It may be useful to perform vmagent rolling update without any scrape loss.

## References
- https://docs.victoriametrics.com/victoriametrics/vmagent/#monitoring
