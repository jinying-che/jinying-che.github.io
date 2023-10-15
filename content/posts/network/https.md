---
title: "HTTPS"
date: "2019-06-10T11:19:47+08:00"
tags: ["network"]
description: "HTTPS Overivew"
---

## TL;DR
**HTTPS = HTTP Over TLS**, when we talk about HTTPS, we actually talk about the TLS more specifically.

## Handshake 
The exact steps within a TLS handshake will vary depending upon the kind of key exchange algorithm used and the cipher suites supported by both sides. The RSA key exchange algorithm, while now considered not secure, was used in versions of TLS before 1.3.
#### Handshake TLS 1.2 
Basically it's a *3-Way TCP handshake* + *4 Way TLS handshake*.
![https handshake](/images/https_handshake.png)
```
      Client                                             Server
      
      -------------------- TCP 3-Way Handshke -----------------
      
      SYNC
                                                     SYNC + ACK
      
      ACK

      -------------------- TLS 4-Way Handshake  ---------------

      ClientHello                -------->
                                                    ServerHello
                                                   Certificate*
                                             ServerKeyExchange*
                                            CertificateRequest*
                                 <--------      ServerHelloDone
      Certificate*
      ClientKeyExchange
      CertificateVerify*
      [ChangeCipherSpec]
      Finished                   -------->
                                             [ChangeCipherSpec]
                                 <--------             Finished

      Application Data           <------->     Application Data
```

Understand the classic handshake in 4 general steps:
1. TCP Handshake
2. Certificate Check (**TCP**: client says hello, server says hello)
3. Key Exchange (**Asymmetric Encryption**)
    Basically there're two way for key exchange, the key point is how to generate the **premaster secret** which is used to generate master secret which is used for data transmission eventually:
    1. client generates the premaster secret key, encrypts by the public key, send to server (RSA algorithm)
    2. client and server generate the same premaster secret seperately using client and server params (ECDHE algorithm )
4. Data Transmission (**Symmetric Encryption**)

#### Handshake TLS 1.3 
TBD

## Man-In-The-Middle Attacker
Assume there's an attacker who can detect the info during the TLS handshake, trying to defend the attacker is a better way to understand the HTTPS design more throughly.

1. Attacker is disguised as server? Use **Certificate Authority (CA)** to validate the server
2. Attacker steal the transmission key (master secret)? Use **Asymmetric Encryption (one way encryption)**, even if attacker get the public key, still he's not able to know what client sends to server (e.g. premaster secret) as only the private key can decrypt
3. Attacker get the leaked private key? Use ECDHE algoritm to generate the premaster secret instead of passing from client to server. 

## SSL vs TLS
SSL(Secure Sockets Layer) was the original security protocol developed for HTTP. SSL was replaced by TLS(Transport Layer Security) some time ago. SSL handshakes are now called TLS handshakes, although the "SSL" name is still in wide use.

> SSL v3.1 = TLS v1.0

## Referrence
- https://blog.bytebytego.com/p/how-does-https-work-episode-6
- [RFC5246: TLS1.2](https://datatracker.ietf.org/doc/html/rfc5246)
- [RFC8446: TLS1.3](https://datatracker.ietf.org/doc/html/rfc8446)
- [RFC2818: HTTPS](https://datatracker.ietf.org/doc/html/rfc2818)
