---
title: "DNS"
date: "2023-09-20T11:47:31+08:00"
tags: ["network", "dns"]
description: "DNS Overview"
---

[Domain Name System (DNS)](https://en.wikipedia.org/wiki/Domain_Name_System) is the phonebook of the Internet. It translates human-readable domain names (google.com) to machine-readable IP addresses (142.251.46.238).

DNS is not very complex but super useful.

## How does DNS work?
![dns architecutre](/images/dns_architecture.svg)

![dns flow](/images/dns_flow.png)

The basic flow to query dns level by level as follows, the previous server stores the next server address, e.g. Root Nameserver stores TLD Nameserver addresss. 
1. **Brower cache and OS cache**
2. **DNS Resolver**: is responsible for initiating and sequencing the queries that ultimately lead to a full resolution (translation) of the resource sought. DNS resolvers are classified by a variety of query methods, such as **recursive**, **non-recursive**, and **iterative**. A resolution process may use a combination of these methods.
3. **Root Nameserver**: the first step in translating (resolving) human readable host names into IP addresses. It stores the IP addresses of TLD, There are **13** logical Root Nameserver globally, e.g.
    ```txt
    - l.root-servers.net.
    - m.root-servers.net.
    - a.root-servers.net.
    - b.root-servers.net.
    - c.root-servers.net.
    - d.root-servers.net.
    - e.root-servers.net.
    - f.root-servers.net.
    - g.root-servers.net.
    - h.root-servers.net.
    - i.root-servers.net.
    - j.root-servers.net.
    - k.root-servers.net.
    ```
4. **TLD Nameserver** (Top Level Domain Server): It stores the IP addresses of authoritative name servers, e.g.
    ```txt
    - .com
    - .org
    - .edu
    - .net
    - .us
    - .cn
    - ...
    ```
5. **Authoritative Nameserver**: it provides the actual anwser for the dns request.

### Example
Let's try to trace the dns request for `jinying-che.github.io` from my local laptop:
```shell
➜  ~ dig +trace jinying-che.github.io

; <<>> DiG 9.10.6 <<>> +trace jinying-che.github.io
;; global options: +cmd
.                       467805  IN      NS      l.root-servers.net.
.                       467805  IN      NS      m.root-servers.net.
.                       467805  IN      NS      a.root-servers.net.
.                       467805  IN      NS      b.root-servers.net.
.                       467805  IN      NS      c.root-servers.net.
.                       467805  IN      NS      d.root-servers.net.
.                       467805  IN      NS      e.root-servers.net.
.                       467805  IN      NS      f.root-servers.net.
.                       467805  IN      NS      g.root-servers.net.
.                       467805  IN      NS      h.root-servers.net.
.                       467805  IN      NS      i.root-servers.net.
.                       467805  IN      NS      j.root-servers.net.
.                       467805  IN      NS      k.root-servers.net.
.                       467805  IN      RRSIG   NS 8 0 518400 20231002140000 20230919130000 11019 . hSoNzesJLtJnf9gXYqG4SMrn8R78uNEqUgc1xcFKglavg16gnPrvQnuP sLb74PkmHE+uqQ1ZPs31X6XrA8E/yhlF8r4kPQAaEiMhkLXsZ1QPLgfj wHFWsFcVmWZTKJIQO/6H7P6ht0jhX0pLVRVRTZtIPH0uYqz6w9Z8vWuw Haaqm+48d5+cuyn2iNNqxO8omlQLALwaALu6/7hZPQfgkH6+XBPvSagj 6FOV+zun2hwKNCwrJ7elYQCfL7xi0UbjAOt+OOJYJfF9vfJq9qYnt8/O IBrfdRHtsryH/Fmk/wUPhgNEMYLwgz4n1z+a25A7q5ofocId5lsDYAUJ YxLSNA==
;; Received 1097 bytes from 192.168.0.1#53(192.168.0.1) in 11 ms

io.                     172800  IN      NS      a2.nic.io.
io.                     172800  IN      NS      c0.nic.io.
io.                     172800  IN      NS      a0.nic.io.
io.                     172800  IN      NS      b0.nic.io.
io.                     86400   IN      DS      57355 8 2 95A57C3BAB7849DBCDDF7C72ADA71A88146B141110318CA5BE672057 E865C3E2
io.                     86400   IN      RRSIG   DS 8 1 86400 20231003050000 20230920040000 11019 . TnYR1fL2pnUlBTTsJleHjjmxjLs96HwMJOtcHvTzwK31ZBoT+sp76dHq bsQfFgX7FqyTjIzF+z/W7dK1wKnO1ONvhbeWCTZO8SAIMaJU4ZyPAAMo D+xM7YpRHrAYES2wi+cX20kDDKUXauhxiesHqywSMdNK6XugyLluSaz1 J5c2Y0S2r7pZwEPV5v6w9TjzNQOfcfu0NLQx1i7JAbuLExGc7/7pjqxY XB2LH9FtyzgfAkm0ovTu5BRzbUxO/lSURlGIPsI05aFVz6HEhnl04Ujb dmir+S3ffOahHgxjD2al8yIx/FS67ZCi+va2pA6lHdHsktrNnTn2tGZt aUJrzg==
;; Received 637 bytes from 192.112.36.4#53(g.root-servers.net) in 85 ms

github.io.              3600    IN      NS      dns2.p05.nsone.net.
github.io.              3600    IN      NS      ns-1622.awsdns-10.co.uk.
github.io.              3600    IN      NS      dns3.p05.nsone.net.
github.io.              3600    IN      NS      dns1.p05.nsone.net.
github.io.              3600    IN      NS      ns-692.awsdns-22.net.
0d790076pp5pfktg2hrthj5bj6ckckcb.io. 3600 IN NSEC3 1 1 10 332539EE7F95C32A 0D7N522D3BFMA1LA01BUIOBUK6MROGMU  NS SOA RRSIG DNSKEY NSEC3PARAM
0d790076pp5pfktg2hrthj5bj6ckckcb.io. 3600 IN RRSIG NSEC3 8 2 3600 20231011082044 20230920072044 32553 io. hg8Fr2R0FnIfikGso1mx3B66B9QtVVcMoOL108Ahw5D7TUTo/AL+vpP9 AFEa5GMnkenQqbWsp5/xgEuhJxeMbbzF88roBy6hnSoLq21qysLpIQuC Q+TprenA+f7dKiza7RLTTPnv6qN1b50Z/VSsowMK6Fw353h2WLOUAg0G 2I4=
0jehpe7obc68rhh4ntet0u9o44qmosmo.io. 3600 IN NSEC3 1 1 10 332539EE7F95C32A 0JES1F5OD9SG1E4CCRGBS865PMBUV4PC  NS DS RRSIG
0jehpe7obc68rhh4ntet0u9o44qmosmo.io. 3600 IN RRSIG NSEC3 8 2 3600 20231008005435 20230916235435 32553 io. b6iUJ3A5Govhm/HVZIU7ygw7l8tHsUnDFCZaR50HDmYtbmi/g83PASgw 4IgNm42FI2u8oX3HZ2ce8gBK48ts/1bbSCxthUqO2KrSlou+Okh7z+J1 TAeRsC8FkkA/RHu+ymFM1g0BB2cv23Rnftwtl9jsD4JoDKSzhVcKiOx9 WIA=
;; Received 687 bytes from 65.22.160.17#53(a0.nic.io) in 7 ms

jinying-che.github.io.  3600    IN      A       185.199.108.153
jinying-che.github.io.  3600    IN      A       185.199.109.153
jinying-che.github.io.  3600    IN      A       185.199.110.153
jinying-che.github.io.  3600    IN      A       185.199.111.153
;; Received 114 bytes from 198.51.44.5#53(dns1.p05.nsone.net) in 168 ms
```
1. Get NS Record: 13 Root Nameservers from `192.168.0.1`(DNS Resolver) which is configured by `/etc/resolv.conf`
2. Get NS Record: TLD (Top Level Domain) from one of Root Nameserve `g.root-servers.net`
3. Get NS Record: Authoritative Nameserver from one of TLD `a0.nic.io`
4. Get A Record: Actual ip address from one of Authoritative Nameserver `dns1.p05.nsone.net`


## DNS Record
There're a lot of [DNS Record types](https://en.wikipedia.org/wiki/List_of_DNS_record_types), the follows are the common record from the client perspective:
| Record | Function |
| ------ | -------- |
| A | Address record: Returns a 32-bit IPv4 address |
| AAAA | IPv6 address record: Returns a 128-bit IPv6 address |
| NS | Name server record: Delegates a DNS zone to use the given authoritative name servers |
| CNAME | Canonical name record: Alias of one name to another: the DNS lookup will continue by retrying the lookup with the new name |

## Configuration
There're two way to query the ip address by domain, typically whenever a system needs to resolve a name, it first checks the `/etc/hosts` file. If no entry matched, it sends a query to the configured DNS server (by `/etc/resolv.conf`).

```shell
# /etc/resolv.conf defines the namesever address
$ cat /etc/resolv.conf
nameserver 114.114.114.114

# /etc/hosts defines the domain and ip address pair directly
$ cat /etc/hosts
127.0.0.1 localhost      

# The order in which (/etc/hosts and /etc/resolv.conf) file is checked 
# is defined in the /etc/nsswitch.conf file
cat /etc/nsswitch.conf | grep host 
hosts:          files dns
```

## Protocol
DNS originally used the `UDP` as transport over IP. Reliability, security, and privacy concerns spawned the use of the `TCP` as well as numerous other protocol developments.

## Referrence
- https://www.cloudflare.com/learning/dns/what-is-dns/
- https://en.wikipedia.org/wiki/Domain_Name_System
- https://blog.bytebytego.com/p/how-does-the-domain-name-system-dns
- https://draveness.me/dns-coredns/
- https://draveness.me/whys-the-design-dns-udp-tcp/
- https://time.geekbang.org/column/article/81850
- [RFC 1035](https://datatracker.ietf.org/doc/html/rfc1035)
- [DNS Record Names](https://en.wikipedia.org/wiki/List_of_DNS_record_types)
- [/etc/hosts vs /etc/resolv.conf vs etc/nsswitch.conf](https://www.computernetworkingnotes.com/linux-tutorials/the-etc-hosts-etc-resolv-conf-and-etc-nsswitch-conf-files.html)
