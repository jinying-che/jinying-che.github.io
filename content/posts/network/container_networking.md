---
title: "Container Networking"
date: 2021-08-26T10:27:13+08:00
description: "Network Implementation In Container"
tags: ["network"]
---

# Before
---

### VETH
The veth devices are virtual Ethernet devices. They can act as tunnels between network namespaces to create a bridge to a physical network device in another namespace, but can also be used as standalone network devices.

veth device pairs are useful for combining the network facilities of the kernel together in interesting ways.  A particularly interesting use case is to place one end of a veth pair in one network namespace and the other end in another network namespace, thus allowing communication between network namespaces.

### Bridge
A Linux bridge behaves like a network switch. It forwards packets between interfaces that are connected to it. 

It's usually used for forwarding packets on routers, on gateways, or between VMs and network namespaces on a host. 
It also supports STP, VLAN filter, and multicast snooping.

### Iptables
iptables is a user-space utility program that allows a system administrator to configure the IP packet filter rules of the Linux kernel firewall, implemented as different [Netfilter](https://www.netfilter.org/) modules. The filters are organized in different tables, which contain chains of rules for how to treat network traffic packets.

For details, pls refer to another [blog](https://jinying-che.github.io/posts/network/iptables/)

# Bridge Networking

# Calico Networking

## Reference:
- https://man7.org/linux/man-pages/man4/veth.4.html
- https://developers.redhat.com/blog/2018/10/22/introduction-to-linux-interfaces-for-virtual-networking
- https://github.com/mz1999/blog/blob/master/docs/docker-network-bridge.md
- https://time.geekbang.org/column/article/64948?cid=100015201
- https://en.wikipedia.org/wiki/Iptables
