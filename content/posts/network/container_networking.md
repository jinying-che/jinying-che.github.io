---
title: "Container Networking"
date: 2021-08-26T10:27:13+08:00
tag: ["network", "container"]
draft: true
---

Network Implementation In Container
<!--more-->

# Before

### VETH
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

### Bridge
> A Linux bridge behaves like a network switch. It forwards packets between interfaces that are connected to it. 
> It's usually used for forwarding packets on routers, on gateways, or between VMs and network namespaces on a host. 
> It also supports STP, VLAN filter, and multicast snooping.

### Iptables
> iptables allows the system administrator to define tables containing chains of rules for the treatment of packets. Each table is associated with a different kind of packet processing. Packets are processed by sequentially traversing the rules in chains. A rule in a chain can cause a goto or jump to another chain, and this can be repeated to whatever level of nesting is desired. (A jump is like a “call”, i.e. the point that was jumped from is remembered.) Every network packet arriving at or leaving from the computer traverses at least one chain.

In a nutshell: 
- Relationship: Tables -> Chains -> Rules
  ![package flow through iptables](/images/iptable.png)
#### tables
There are four tables, the *Priority* is: **raw → mangle → nat → filter**
> For details, please refer to: https://www.thegeekstuff.com/2011/01/iptables-fundamentals/ 

```shell
# show filter table by default
iptables -L -v -n 
# which is equal to 
iptables -t filter -L -v -n
```

#### chains
> There are five predefined chains (mapping to the five available Netfilter hooks), though a table may not have all chains.
> - PREROUTING: Packets will enter this chain before a routing decision is made.
> - INPUT: Packet is going to be locally delivered. It does not have anything to do with processes having an opened socket; local delivery is controlled by the "local-delivery" routing table: ip route show table local.
> - FORWARD: All packets that have been routed and were not for local delivery will traverse this chain.
> - OUTPUT: Packets sent from the machine itself will be visiting this chain.
> - POSTROUTING: Routing decision has been made. Packets enter this chain just before handing them off to the hardware.
>
> The system administrator can create as many other chains as desired.
#### rules
> - ACCEPT – Firewall will accept the packet.
> - DROP – Firewall will drop the packet.
> - QUEUE – Firewall will pass the packet to the userspace.
> - RETURN – Firewall will stop executing the next set of rules in the current chain for this packet. The control will be returned to the calling chain.

# Bridge Networking

# Calico Networking

Reference:
- https://man7.org/linux/man-pages/man4/veth.4.html
- https://developers.redhat.com/blog/2018/10/22/introduction-to-linux-interfaces-for-virtual-networking
- https://github.com/mz1999/blog/blob/master/docs/docker-network-bridge.md
- https://time.geekbang.org/column/article/64948?cid=100015201
- https://en.wikipedia.org/wiki/Iptables
