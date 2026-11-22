---
title: "SSH"
date: "2025-09-09T22:42:19+08:00"
tags: ["network", "ssh"]
description: "how to use ssh and how it works"
---

## Server

### Configure and reload sshd safely

The server reads `/etc/ssh/sshd_config` and, on many distributions, included files under `/etc/ssh/sshd_config.d/`. These are **server** settings; client settings belong in `~/.ssh/config`.

```text
# /etc/ssh/sshd_config (or an included configuration file)
PubkeyAuthentication yes
MaxSessions 10

# Disable password-based login only after testing key-based access
PasswordAuthentication no
KbdInteractiveAuthentication no
```

`MaxSessions` limits shell, login, and subsystem channels **per SSH connection**, not the total number of connected clients. Keep your current session open while changing authentication settings, and verify a new login from another terminal before closing it.

```sh
# Validate syntax and host keys before reloading
sudo /usr/sbin/sshd -t

# Inspect effective settings (Match rules may depend on the connection)
sudo /usr/sbin/sshd -T
sudo /usr/sbin/sshd -T -C user=alice,host=client.example.com,addr=192.0.2.10

# Debian/Ubuntu service name; run only after validation succeeds
sudo systemctl reload ssh
# Fedora/RHEL commonly use: sudo systemctl reload sshd
```

### Maintain authorized SSH clients

Each server account has its own `~/.ssh/authorized_keys` by default. Run these commands as the account that clients log into; `~` means the current account's home directory.

```sh
# Inspect allowed public keys and their fingerprints
cat ~/.ssh/authorized_keys
ssh-keygen -lf ~/.ssh/authorized_keys

# Correct permissions on an existing key setup
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
ls -ld ~ ~/.ssh ~/.ssh/authorized_keys

# Back up the allowlist before editing it
cp -p ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak
```

Use a separate key for each device or automation job, with a descriptive comment such as `alice-laptop`. To rotate a key, add the new public key, test it in a separate connection, then remove the old key's line. To revoke a lost client's access, remove its public key from every relevant account and server. Never copy a client's private key to the server. Check that the account owns its SSH files and that its home directory is not writable by other users.

For automation, restrict a key's capabilities when possible. For example, this `authorized_keys` entry permits only one command from one source address and disables forwarding and PTY allocation:

```text
from="192.0.2.10",restrict,command="/usr/local/bin/backup-status" ssh-ed25519 AAAA... backup-job
```

Replace the example address, command, and public key with real values. Removing a key prevents future authentication; it does **not** disconnect existing sessions.

### Inspect connections, sessions, and authentication logs

```sh
# Established TCP connections, including their owning processes
sudo ss -tnp state established
# Listening sockets (look for sshd and your configured port)
sudo ss -ltnp

# Logged-in terminal users and their activity
who
w

# Recent SSH service logs on Debian/Ubuntu
sudo journalctl -u ssh --since '1 hour ago'
# Fedora/RHEL commonly use: sudo journalctl -u sshd --since '1 hour ago'

# Follow authentication events as a client reconnects
sudo journalctl -u ssh -f
```

`who` and `w` show terminal logins; tunnels and non-interactive commands may only appear in socket/process inspection. Depending on the distribution, authentication logs may also be in `/var/log/auth.log` or `/var/log/secure`. If a session must be disconnected, identify its process carefully before terminating it; avoid killing the listener or your own recovery session.

## Client

### Generate and install a key

See [Generating a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent).

```sh
# Use a passphrase; choose a new filename instead of overwriting an existing key
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_work -C "alice-laptop"

# Install only the public key; requires an existing way to log in
ssh-copy-id -i ~/.ssh/id_ed25519_work.pub alice@server.example.com

# Test this specific key
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519_work alice@server.example.com
```

### Keep reusable host settings

```sshconfig
# ~/.ssh/config
Host work
    HostName server.example.com
    User alice
    Port 22
    IdentityFile ~/.ssh/id_ed25519_work
    IdentitiesOnly yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

Connect with `ssh work`. `IdentitiesOnly` avoids offering unrelated agent keys. The keepalive settings detect an unresponsive server after roughly 90 seconds; they do not reconnect a failed session. Put specific host blocks before broad `Host *` defaults because the first value found generally wins.

```sh
chmod 700 ~/.ssh
chmod 600 ~/.ssh/config ~/.ssh/id_ed25519_work

# Inspect the effective client configuration without connecting
ssh -G work

# Debug network, host-key, and authentication problems
ssh -vvv work
```

### Maintain the SSH agent and keys

```sh
# Start an agent only if your desktop/login session does not already provide one
eval "$(ssh-agent -s)"

# Cache a key for one hour, list loaded fingerprints, then remove it when done
ssh-add -t 1h ~/.ssh/id_ed25519_work
ssh-add -l
ssh-add -d ~/.ssh/id_ed25519_work

# Change a private key's passphrase without replacing the key pair
ssh-keygen -p -f ~/.ssh/id_ed25519_work
```

### Verify server host keys

Before accepting a new host key, compare its fingerprint through a trusted channel (for example, the server console or its administrator).

```sh
# On the server: display the Ed25519 host-key fingerprint
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

# On the client: find a saved host entry, including hashed entries
ssh-keygen -F server.example.com

# Only after independently verifying a legitimate host-key change:
ssh-keygen -R server.example.com
# For a non-default port, use the bracketed host:port form:
ssh-keygen -R '[server.example.com]:2222'
```

Reconnect and verify the replacement fingerprint. A changed-key warning can indicate a rebuilt server or an impersonation attempt; do not bypass it with `StrictHostKeyChecking=no`. `ssh-keyscan` can collect a key but cannot prove that the server is authentic.

## SSH Handshake
SSH setup establishes a TCP connection, negotiates algorithms, exchanges keys and verifies the server, then authenticates the user. The diagram shows a simplified ECDH exchange with successful public-key authentication; time flows downward.

{{< ssh-handshake >}}

The server signs the key-exchange transcript with its host key. The client checks that signature and whether the host key is trusted (commonly through `known_hosts`). Both peers derive symmetric traffic keys; the shared secret is never sent over the network. Each direction switches to encryption after its sender's `SSH_MSG_NEWKEYS`, **before** user authentication.

This is not a fixed five-RTT protocol: version exchange, pipelining, optional public-key probes, additional authentication methods, and channel setup affect latency. After authentication, SSH opens a channel for a shell, command, or subsystem. The diagram omits channel request/confirmation details.

 | Term | Meaning |
 |:-----|:--------|
 | `Banner` | Version string exchange (e.g. `SSH-2.0-OpenSSH_9.0`), identifies protocol version and implementation |
 | `SSH_MSG_KEXINIT` | Both sides advertise supported algorithms (kex, cipher, MAC) |
 | `SSH_MSG_KEX_ECDH_INIT` | Client sends its ephemeral EC public key to start DH exchange |
 | `SSH_MSG_KEX_ECDH_REPLY` | Server sends its EC public key + Host Key + Signature |
 | `SSH_MSG_NEWKEYS` | Signal to switch to the newly derived symmetric key |
 | `SSH_MSG_SERVICE_REQUEST` | Client requests the `ssh-userauth` sub-protocol |
 | `SSH_MSG_SERVICE_ACCEPT` | Server confirms the auth service is ready |
 | `SSH_MSG_USERAUTH_REQUEST` | For the signed public-key method: username + public key + signature (an optional unsigned key probe may come first) |
 | `SSH_MSG_USERAUTH_SUCCESS` | Server confirms authentication passed |

## SSH vs TLS
> for tls details, refer to [https](https://chejinying.com/tech/posts/network/https/)

 | | TLS 1.3 | TLS 1.2 | SSH |
 |---|---|---|---|
 | **RTT after TCP** | 1 RTT | 2 RTT | Varies with negotiation and authentication |
 | **Server Identity** | Certificate signed by CA | Certificate signed by CA | Host Key stored in `~/.ssh/known_hosts` (TOFU, Trust On First Use) |
 | **Client Identity** | Optional mTLS certificate | Optional mTLS certificate | Public key in `~/.ssh/authorized_keys` |
 | **Trust Model** | Centralized CA hierarchy | Centralized CA hierarchy | Trust On First Use (TOFU) |
 | **Key Exchange** | ECDHE inside ClientHello | Negotiated after hello | Separate KEXINIT then ECDH |
 | **Forward Secrecy** | Mandatory | Optional | Yes, ephemeral DH keys |
 | **User Authentication** | No | No | Separate phase (public key / password) |
 | **Encryption Start** | After 1 RTT | After 2 RTT | After key exchange phase |
