---
title: "SSH"
date: "2025-09-09T22:42:19+08:00"
tags: ["network", "ssh"]
description: "how to use ssh and how it works"
---

## Server
### where is sshd config?
```sh
# location 
/etc/ssh/sshd_config

# list all authorized public keys for a user
cat ~/.ssh/authorized_keys

# allow multiple sessions
MaxSessions 10

# enable public key authentication
PubkeyAuthentication yes

# disable password authentication
PasswordAuthentication no
```

### How to check ssh session or connections?
```ssh
# check tcp connection
sudo netstat -tnpa | grep sshd

# check ssh session
sudo who
```

## Client 
> refer to [Generating a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
```sh
# generate ssh key pair
ssh-keygen -t ed25519 -C "your_email@example.com"

# copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server_ip
```

## SSH Handshake
Basically, ssh handshake includes 4 phases (totally 5 RTT): 
- tcp handshake
- algorithms negotiation
- key exchange (for ECDH calculation, similar to TLS)
- authentication (SSH verifies server identity via TOFU `known_hosts`, client identity via public key `authorized_keys`, whereas TLS uses CA to verify server identity)
```
  Client                                        Server
  -------------------- TCP 3-Way Handshake --------------------
  SYN                          -------->
                               <--------                SYN+ACK
  ACK                          -------->

  -------------------- Algorithm Negotiation ------------------
  Banner + SSH_MSG_KEXINIT     -------->
                               <--------  Banner + SSH_MSG_KEXINIT

  -------------------- Key Exchange ---------------------------
  SSH_MSG_KEX_ECDH_INIT        -------->
                               <--------      SSH_MSG_KEX_ECDH_REPLY
                               <--------             SSH_MSG_NEWKEYS
  SSH_MSG_NEWKEYS              -------->

  -------------------- Authentication -------------------------
  SSH_MSG_SERVICE_REQUEST      -------->
                               <--------      SSH_MSG_SERVICE_ACCEPT
  SSH_MSG_USERAUTH_REQUEST     -------->
                               <--------     SSH_MSG_USERAUTH_SUCCESS

  -------------------- Encrypted Session ----------------------
  Application Data             <------->            Application Data
```

 | Term | Meaning |
 |:-----|:--------|
 | `Banner` | Version string exchange (e.g. `SSH-2.0-OpenSSH_9.0`), identifies protocol version and implementation |
 | `SSH_MSG_KEXINIT` | Both sides advertise supported algorithms (kex, cipher, MAC) |
 | `SSH_MSG_KEX_ECDH_INIT` | Client sends its ephemeral EC public key to start DH exchange |
 | `SSH_MSG_KEX_ECDH_REPLY` | Server sends its EC public key + Host Key + Signature |
 | `SSH_MSG_NEWKEYS` | Signal to switch to the newly derived symmetric key |
 | `SSH_MSG_SERVICE_REQUEST` | Client requests the `ssh-userauth` sub-protocol |
 | `SSH_MSG_SERVICE_ACCEPT` | Server confirms the auth service is ready |
 | `SSH_MSG_USERAUTH_REQUEST` | Client sends username + public key + signature |
 | `SSH_MSG_USERAUTH_SUCCESS` | Server confirms authentication passed |

## SSH vs TLS
> for tls details, refer to [https](https://chejinying.com/tech/posts/network/https/)

 | | TLS 1.3 | TLS 1.2 | SSH |
 |---|---|---|---|
 | **RTT after TCP** | 1 RTT | 2 RTT | 4 RTT |
 | **Server Identity** | Certificate signed by CA | Certificate signed by CA | Host Key stored in `~/.ssh/known_hosts` (TOFU, Trust On First Use) |
 | **Client Identity** | Optional mTLS certificate | Optional mTLS certificate | Public key in `~/.ssh/authorized_keys` |
 | **Trust Model** | Centralized CA hierarchy | Centralized CA hierarchy | Trust On First Use (TOFU) |
 | **Key Exchange** | ECDHE inside ClientHello | Negotiated after hello | Separate KEXINIT then ECDH |
 | **Forward Secrecy** | Mandatory | Optional | Yes, ephemeral DH keys |
 | **User Authentication** | No | No | Separate phase (public key / password) |
 | **Encryption Start** | After 1 RTT | After 2 RTT | After key exchange phase |
