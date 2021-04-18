---
title: "Brief Introduction of Network Hardware"
date: 2021-04-05T23:11:29+08:00
tag: ["network"]
---

The hardware inlucded in this post are Hub, Switch, Router, Modem, AP

<!--more-->

#### Hub and Switch
The purpose of both is to connect the internal network (LAN), they do not know IP
##### Hub 
- It is not intelligent, what it knows is only the ports and the devices that is connected to the ports
- It does not filter any data or has intelligence as to where the data is supposed to be sent
- When a data packet comes into one port, it will rebroadcast the data to every port that has a device connected to it 
- It operates at the [Physical Layer of OSI](https://en.wikipedia.org/wiki/OSI_model#Layer_1:_Physical_Layer)

##### Switch
- It's intelligent and able to learn physical(MAC) address of devices that are connected to it
- When a data packet is sent to a switch, it's only directed to the intended destination port
- It operates at the [Data Link Layer of OSI](https://en.wikipedia.org/wiki/OSI_model#Layer_2:_Data_Link_Layer) (not including the **multilayer** switch)

#### Router
- It routes or forwards data from network to another base on IP address
- It's the **Gateway** of a network, it detemines if the packet was meant for it's own network
- It normally works at the [Network layer of OSI](https://en.wikipedia.org/wiki/OSI_model#Layer_3:_Network_Layer)

> ![Hub vs Switch vs Router](/images/hub_switch_router.png)

#### Modem
Modems (modulators-demodulators) are used to transmit digital signals over analog telephone lines
- Modulators: it modulates **outgoing** digital signals into an analog signal
- Demodulator: it demodulate **incoming** analog signals into a digital signal
- Modems work on both the Physical and Data Link layers.

> ![Modem](/images/modem.png)

#### Access Point
- A Wireless AP relays data **a wired network** and **wireless devices**
- It's basically wireless **hub** or **bridge** that's used by wireless device to connect to an existing wired network
- A Wireless AP connects directly to an organization's router where the router is connected directly to a modem, which gives the wireless device access to the internet 
- An AP works at the second OSI layer, the Data Link layer

> ![Wireless Access Point](/images/ap.png)

---
#### Reference:
- https://blog.netwrix.com/2019/01/08/network-devices-explained/
- https://en.wikipedia.org/wiki/Ethernet_hub
- https://en.wikipedia.org/wiki/OSI_model
- https://www.youtube.com/watch?v=OxiY4yf6GGg
- https://www.youtube.com/watch?v=Mad4kQ5835Y
- https://www.youtube.com/watch?v=1z0ULvg_pW8
