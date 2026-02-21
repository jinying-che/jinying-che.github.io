---
title: "HTTPS"
date: "2019-06-10T11:19:47+08:00"
tags: ["network"]
description: "HTTPS Overivew"
---

## TL;DR Story
1.  **The Mission:** TLS was created to stop eavesdroppers and hackers from reading or changing data sent over the internet.
2.  **The Secret:** To communicate securely, both the browser (Client) and the website (Server) must agree on a **Symmetric Key** (a secret code) to encrypt their data.
3.  **The Safety:** This "secret code" is never sent over the wire in plain text. Instead, they use **Asymmetric Encryption** (Public/Private keys) or a "mathematical dance" (Diffie-Hellman) to calculate the same key independently on both sides.
4.  **The Trust:** Before sharing keys, the Client must know the Server is real. The Server shows an **ID Card (Certificate)** that is verified by a trusted third party (**Certificate Authority**).
5.  **The Result:** Once the identities are proven and the secret key is created, the two sides can talk at high speed, knowing their conversation is private, secure, and cannot be decoded—even if the server is hacked in the future (**Forward Secrecy**).

## Handshake 
The exact steps within a TLS handshake will vary depending upon the kind of key exchange algorithm used and the cipher suites supported by both sides. The basic process includes `Asymmetric` and `Symmetric` Encryption.
#### Handshake TLS 1.2 
Basically, it is a TCP 3-Way Handshake followed by a TLS 4-Way Handshake. 

It would be better to check the `tls 1.2` handshake log in the real world first as below, learning by doing!
```shell
# --tlsv1.2: Tells curl to start the negotiation at version 1.2.
# --tls-max 1.2: Prevents curl from automatically upgrading to 1.3 even if the server supports it.
curl -v --tlsv1.2 --tls-max 1.2 https://chejinying.com
```
Take a look at the output of the `curl` command, let's dive into the details with the handshake logs
![https handshake](/images/https_handshake.png)

```
 Client                                             Server
 -------------------- TCP 3-Way Handshake -----------------
 SYN                        -------->
                            <--------             SYN + ACK
 ACK                        -------->

 -------------------- TLS 4-Way Handshake  ---------------
 ClientHello (Random + Ciphers)  -------->
                                               ServerHello (Random + Cipher)
                                              Certificate*
                                        ServerKeyExchange*
                                       CertificateRequest*
                            <--------      ServerHelloDone
 Certificate*
 ClientKeyExchange
 CertificateVerify*
 [ChangeCipherSpec]
 Finished (Encrypted Test)  -------->
                                        [ChangeCipherSpec]
                            <--------   Finished (Encrypted Test)

 ------------------- Secure Data Transfer -----------------
 Application Data           <------->     Application Data
```

> Note on Asterisks (`*`): Messages marked with * are optional. For the public website, these three optional steps were skipped because it's not using Mutual TLS(mTLS):
>    1. `CertificateRequest*` (Server asking for your ID)
>    2. `Certificate*` (Client sending its ID)
>    3. `CertificateVerify*` (Client proving it owns the Private Key for its ID)

Understand the classic handshake with the key points below:
1. TCP Handshake: Establish a raw connection between the two points.
2. TLS Hello (The Negotiation):
    * ClientHello: The client sends its supported TLS version, a Client Random number, and a list of Cipher Suites.
    * ServerHello: The server chooses the highest version and the best Cipher Suite both support and sends its own Server Random. (can see the agreed Cipher Suite in the curl output, they're actually four algorithms in one package and used in different steps) 

3. Certificate (Server Authentication):
     * Server Sends Chain: The server sends its certificate chain (e.g., `Domain Cert` + `Intermediate Cert`).
     * Client Validation (Offline): The client performs several critical checks before proceeding:
         - **Chain of Trust:** Traces the link back to a pre-installed **Root CA** in its local **Root Store**.
         - **Digital Signature:** Uses the CA's public key to verify that the certificate was truly issued by that CA.
         - **Validity & Domain:** Checks that the certificate is **not expired** and the **Domain Name** matches
4. Server and Client Key Exchange:
    * Proof of Ownership: The server sends its key exchange parameters **signed** with its private key. The cliet uses the public key from the verified certificate to check this signature.
    * The Secret: Both sides need to agree on a Premaster Secret. There are two main ways:
        1. RSA (Classic): Client generates the secret, encrypts it with the server's public key, and sends it. (Not recommended anymore as it lacks "Forward Secrecy").
        2. Diffie-Hellman (ECDHE): Both sides exchange parameters and calculate the same secret independently. This is more secure.
5. Key Derivation & Finished:
    * Both sides combine the Client Random + Server Random + Premaster Secret to create the Master Secret (the
      Symmetric Key).
    * They send a Finished message to verify that the encryption is working correctly before sending real
      application data.

#### Handshake TLS 1.3 

In TLS 1.3, the client "guesses" the key exchange algorithm and sends its parameters immediately. This "optimistic" approach reduces the handshake to a single round trip.

```
Client                                             Server
-------------------- TCP 3-Way Handshake -----------------
SYN                        -------->
                           <--------             SYN + ACK
ACK                        -------->

-------------------- TLS 1-Round Trip Handshake  ----------
ClientHello                -------->
(+ Key Share & Ciphers)
                                              ServerHello
                                             (+ Key Share)
                                     {EncryptedExtensions}* (8)
                                             {Certificate}* (11)
                                           {CERT verify}* (15)
                           <--------            {Finished} (20)
{Finished} (20)            -------->

------------------- Secure Data Transfer -----------------
Application Data           <------->     Application Data

Note: {Messages in braces} are encrypted.
```


Understand the handshake in these 3 logical phases:

Phase 1: Client Request (The "Optimistic" Hello)
 * Key Share: The client sends its Client Random and its half of the Diffie-Hellman Key Share (its public key for the exchange).
 * The Guess: The client "guesses" that the server will support a modern curve (like X25519). By sending the share upfront, it eliminates the need for a separate negotiation round trip.

Phase 2: Server Response (Key Agreement & Proof)
 * Key Agreement: The server sends its Server Random and its own Key Share.
 * Encrypted Response: Because the server now has both shares, it calculates the encryption keys immediately. All following messages are fully encrypted:
     * EncryptedExtensions (8): Server sends protocol-level parameters (like ALPN) securely.
     * Certificate (11): The server sends its ID (now encrypted for privacy).
     * CERT verify (15): The server signs a hash of the handshake with its Private Key to prove it owns the certificate.
     * Finished (20): A final integrity check to confirm the server's handshake is complete.

Phase 3: Client Finish (Key Calculation & Verification)
 * Client Key Calculation: Upon receiving the Server Response, the client finally has the server's share. It immediately calculates the encryption keys.
 * Verification: Using the new keys, the client decrypts the server's Certificate and Finished messages to verify the server's identity.
 * Handshake Confirmation: The client sends its own Finished (20) message to prove it also has the correct keys.
 * Instant Data: Because the keys are now ready, the client can send its first piece of Application Data (HTTP request) at the same time it sends its Finished message.

### TLS 1.2 vs. TLS 1.3 Comparison
| Feature | TLS 1.2 (RFC 5246) | TLS 1.3 (RFC 8446) |
| :--- | :--- | :--- |
| **Handshake Latency** | **2-RTT**: Requires two round-trips before data. | **1-RTT**: Data is sent after one round-trip. |
| **Key Agreement** | **Negotiated**: Handshake exchange happens *after* hello. | **Key Share**: Client sends DH parameters *inside* hello. |
| **Privacy** | **Plain Text**: Server Certificate is visible to ISPs. | **Encrypted**: Server Certificate is hidden from observers. |
| **Security** | Supports weak/old ciphers (RSA, MD5, SHA-1). | **Removed**: All legacy and insecure ciphers are gone. |
| **Forward Secrecy** | **Optional**: Can be disabled by choosing RSA. | **Mandatory**: Ephemeral keys (ECDHE) are required. |
| **Resumption** | Session IDs/Tickets (still requires 1-RTT). | **0-RTT**: Data can be sent in the very first packet. |
| **Integrity (MAC)** | HMAC-SHA256 (Separate step). | **AEAD**: Encryption and integrity are combined. |

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
