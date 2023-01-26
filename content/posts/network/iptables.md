---
title: "Iptables"
date: "2023-01-26T16:22:21+08:00"
tags: ["network", "linux"]
description: "iptables is a user-space utility program that allows a system administrator to configure the IP packet filter rules of the Linux kernel firewall"
---

iptables is a user-space utility program that allows a system administrator to configure the IP packet filter rules of the Linux kernel firewall, implemented as different [Netfilter](https://www.netfilter.org/) modules. The filters are organized in different tables, which contain chains of rules for how to treat network traffic packets.

## In a nutshell: 
- Relationship: Tables -> Chains -> Rules
  ![package flow through iptables](/images/iptable.png)
## Tables
There are five tables, the *Priority* is: **filter, nat, mangle, raw, security**
> https://www.thegeekstuff.com/2011/01/iptables-fundamentals/ 
> https://linux.die.net/man/8/iptables

```sh
# show filter table by default
iptables -L -v -n 
# which is equal to 
iptables -t filter -L -v -n
```

## Chains
There are five predefined chains (mapping to the five available Netfilter hooks), though a table may not have all chains.
- PREROUTING: Packets will enter this chain before a routing decision is made.
- INPUT: Packet is going to be locally delivered. It does not have anything to do with processes having an opened socket; local delivery is controlled by the "local-delivery" routing table: ip route show table local.
- FORWARD: All packets that have been routed and were not for local delivery will traverse this chain.
- OUTPUT: Packets sent from the machine itself will be visiting this chain.
- POSTROUTING: Routing decision has been made. Packets enter this chain just before handing them off to the hardware.

The system administrator can create as many other chains as desired.
## Rules
- ACCEPT – Firewall will accept the packet.
- DROP – Firewall will drop the packet.
- QUEUE – Firewall will pass the packet to the userspace.
- RETURN – Firewall will stop executing the next set of rules in the current chain for this packet. The control will be returned to the calling chain.

## Cheat Sheet
```sh
# drop ip packet:
#   modify the filter table, insert the rule DROP into the INPUT chain at the specific number (1 by default)
#   -A means append the rule at the end of the chain
sudo iptables -I INPUT -s 10.129.106.98 -j DROP

# delele drop ip packet 
sudo iptables -D INPUT -s 10.129.106.98 -j DROP
```

## Reference
- https://www.netfilter.org/documentation/HOWTO/netfilter-hacking-HOWTO-3.html
- [Linux Advanced Routing & Traffic Control How To](https://lartc.org/)
- https://docs.docker.com/network/iptables/
- https://www.linode.com/docs/guides/control-network-traffic-with-iptables/
- https://www.cyberciti.biz/faq/linux-iptables-drop/
