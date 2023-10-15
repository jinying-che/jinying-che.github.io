---
title: "TCP"
date: 2021-02-01T23:25:26+08:00
tags: ["network"]
description: "TCP overview"
---

TCP is really complex protocol and there's a lot of tutorials online to learn TCP, however as time being, it's probably being outdated, same as my post. Hence I would recommend the official [RFC 793](https://datatracker.ietf.org/doc/html/rfc793#autoid-16) as the only true source. Here's a summary of [RFC 793](https://datatracker.ietf.org/doc/html/rfc793#autoid-16).

### TCP Header
[TCP Header Format](https://datatracker.ietf.org/doc/html/rfc793#autoid-16)
```
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |          Source Port          |       Destination Port        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                        Sequence Number                        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    Acknowledgment Number                      |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |  Data |           |U|A|P|R|S|F|                               |
   | Offset| Reserved  |R|C|S|S|Y|I|            Window             |
   |       |           |G|K|H|T|N|N|                               |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |           Checksum            |         Urgent Pointer        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    Options                    |    Padding    |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                             data                              |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### TCP State Machine
Be noted that 11 [TCP Connection States Diagram](https://datatracker.ietf.org/doc/html/rfc793#autoid-17) indicating state to state transformation not cliet to server communication.

```



                              +---------+ ---------\      active OPEN
                              |  CLOSED |            \    -----------
                              +---------+<---------\   \   create TCB
                                |     ^              \   \  snd SYN
                   passive OPEN |     |   CLOSE        \   \
                   ------------ |     | ----------       \   \
                    create TCB  |     | delete TCB         \   \
                                V     |                      \   \
                              +---------+            CLOSE    |    \
                              |  LISTEN |          ---------- |     |
                              +---------+          delete TCB |     |
                   rcv SYN      |     |     SEND              |     |
                  -----------   |     |    -------            |     V
 +---------+      snd SYN,ACK  /       \   snd SYN          +---------+
 |         |<-----------------           ------------------>|         |
 |   SYN   |                    rcv SYN                     |   SYN   |
 |   RCVD  |<-----------------------------------------------|   SENT  |
 |         |                    snd ACK                     |         |
 |         |------------------           -------------------|         |
 +---------+   rcv ACK of SYN  \       /  rcv SYN,ACK       +---------+
   |           --------------   |     |   -----------
   |                  x         |     |     snd ACK
   |                            V     V
   |  CLOSE                   +---------+
   | -------                  |  ESTAB  |
   | snd FIN                  +---------+
   |                   CLOSE    |     |    rcv FIN
   V                  -------   |     |    -------
 +---------+          snd FIN  /       \   snd ACK          +---------+
 |  FIN    |<-----------------           ------------------>|  CLOSE  |
 | WAIT-1  |------------------                              |   WAIT  |
 +---------+          rcv FIN  \                            +---------+
   | rcv ACK of FIN   -------   |                            CLOSE  |
   | --------------   snd ACK   |                           ------- |
   V        x                   V                           snd FIN V
 +---------+                  +---------+                   +---------+
 |FINWAIT-2|                  | CLOSING |                   | LAST-ACK|
 +---------+                  +---------+                   +---------+
   |                rcv ACK of FIN |                 rcv ACK of FIN |
   |  rcv FIN       -------------- |    Timeout=2MSL -------------- |
   |  -------              x       V    ------------        x       V
    \ snd ACK                 +---------+delete TCB         +---------+
     ------------------------>|TIME WAIT|------------------>| CLOSED  |
                              +---------+                   +---------+
```

| Head | Meaning |
| ------------ | ------- |
| LISTEN       | represents waiting for a connection request from any remote TCP and port |
| SYN-SENT     | represents waiting for a matching connection request after having sent a connection request |
| SYN-RECEIVED | represents waiting for a confirming connection request acknowledgment after having both received and sent a connection request |
| ESTABLISHED  | represents an open connection, data received can be delivered to the user. The normal state for the data transfer phase of the connection |
| FIN-WAIT-1   | represents waiting for a connection termination request from the remote TCP, or an acknowledgment of the connection termination request previously sent |
| FIN-WAIT-2   | represents waiting for a connection termination request from the remote TCP |
| CLOSE-WAIT   | represents waiting for a connection termination request from the local user |
| CLOSING      | represents waiting for a connection termination request acknowledgment from the remote TCP |
| LAST-ACK     | represents waiting for an acknowledgment of the connection termination request previously sent to the remote TCP (which includes an acknowledgment of its connection termination request) |
| TIME-WAIT    | represents waiting for enough time to pass to be sure the remote TCP received the acknowledgment of its connection termination request |
| CLOSED       | represents no connection state at all |

Here may be a more readable diagram.
![tcp state Machine](/images/tcpfsm.png)

#### TCP Open: Three-Way Handshake
![tcp open](/images/tcp_open.svg)

![tcp open](/images/tcp_open_bytebytego.png)

#### TCP Close: Four-Way Handshake
![tcp close](/images/tcp_close_bytebytego.png)


### Reference
- http://www.tcpipguide.com/free/t_TCPConnectionEstablishmentProcessTheThreeWayHandsh-3.htm
- http://www.tcpipguide.com/free/t_TCPConnectionTermination-2.htm
- [RFC 793](https://datatracker.ietf.org/doc/html/rfc793#autoid-16)
- https://draveness.me/whys-the-design-tcp-three-way-handshake/
- https://blog.bytebytego.com/p/everything-you-always-wanted-to-know
- [Alibaba: TCP SYN Queue and Accept Queue Overflow Explained](https://www.alibabacloud.com/blog/tcp-syn-queue-and-accept-queue-overflow-explained_599203)
