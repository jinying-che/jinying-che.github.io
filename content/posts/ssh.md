---
title: "SSH"
date: "2025-09-09T22:42:19+08:00"
tags: ["protocol", "ssh"]
description: "how to use ssh and how it works"
draft: true
---

## Server
### where is sshd config?
```sh
# location 
/etc/ssh/sshd_config`

# sshd config

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
ssh-copy-id -i ed25519 user@server_ip
```

## SSH Handshake
TBD
