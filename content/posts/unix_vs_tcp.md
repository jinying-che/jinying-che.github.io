---
title: "Unix_vs_tcp"
date: 2020-12-04T08:56:48+08:00
draft: true
---
I have seen some arguments in [StackOverFlow](https://stackoverflow.com/questions/14973942/tcp-loopback-connection-vs-unix-domain-socket-performance) about the performance between UDS and TCP. Meanwhile, I also found the UDS case in the Service Mesh in our company which is used for the communication between the **local client** and **agent**. Therefor the real benchmark is needed here to verify who is better.Let me approach in this post, will do it in Golang.

---
Reference: https://lists.freebsd.org/pipermail/freebsd-performance/2005-February/001143.html
