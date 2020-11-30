+++ 
draft = false
date = 2020-11-30T08:35:51+08:00
title = "How to profile Golang Program"
description = "Breif indroduction of how to use the go tools to diagnose"
slug = "" 
tags = []
categories = []
externalLink = ""
series = []
+++

First of all, this document is in progress and will keep updated.

Diagnostic by the http call is usually a convinient way in pratice. What we need to do is only two steps before starting the program:
> - `import _ "net/http/pprof"`
> - `http.ListenAndServe("the address that defined in advance", better use privaty ServerMux instead of the default one)`

## Profile
The port 6060 is an example that defined for the http listening. The default time is 30s that go pprof will collect the samples which used to profile without the specificatoin.(I have not find the way to specify btw)
- http://localhost:6060/debug/pprof/goroutine
- http://localhost:6060/debug/pprof/heap
- http://localhost:6060/debug/pprof/threadcreate
- http://localhost:6060/debug/pprof/block
- http://localhost:6060/debug/pprof/mutex
- http://localhost:6060/debug/pprof/profile

Here is a demo of the profilling.
- trigger: 
> `curl localhost:6060/debug/pprof/profile > profile.pprof` (the filename can arbitrary)

- analyse: 
> `go tool pprof -http :6060 ./profile.pprof`

## Trace
- http://localhost:6060/debug/pprof/trace

Here is a demo of the trace.
- trigger: 
> `curl localhost:6060/debug/pprof/trace > profile.trace` 
- analyse: 
> `go tool trace -http :6060 ./profile.trace`

---
## Ref
- https://github.com/google/pprof
- https://golang.org/doc/diagnostics.html
- https://golang.org/pkg/runtime/pprof/
- https://jvns.ca/blog/2017/09/24/profiling-go-with-pprof/


