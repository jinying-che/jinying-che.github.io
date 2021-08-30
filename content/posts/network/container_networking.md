---
title: "Container_network"
date: 2021-08-26T10:27:13+08:00
tag: ["network", "container"]
draft: true
---

Network Implementation In Container
<!--more-->

### Before

#### VETH
> The veth devices are virtual Ethernet devices.  They can act as
>       tunnels between network namespaces to create a bridge to a
>       physical network device in another namespace, but can also be
>       used as standalone network devices.
>
> veth device pairs are useful for combining the network facilities
>        of the kernel together in interesting ways.  A particularly
>        interesting use case is to place one end of a veth pair in one
>        network namespace and the other end in another network namespace,
>        thus allowing communication between network namespaces.

#### Bridge
> A Linux bridge behaves like a network switch. It forwards packets between interfaces that are connected to it. 
> It's usually used for forwarding packets on routers, on gateways, or between VMs and network namespaces on a host. 
> It also supports STP, VLAN filter, and multicast snooping.
#### iptables


Reference:
- https://man7.org/linux/man-pages/man4/veth.4.html
- https://developers.redhat.com/blog/2018/10/22/introduction-to-linux-interfaces-for-virtual-networking
- https://github.com/mz1999/blog/blob/master/docs/docker-network-bridge.md
- https://time.geekbang.org/column/article/64948?cid=100015201

