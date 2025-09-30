---
title: "FRP User Guide: SSH Tunneling Through Public Server"
date: "2025-01-27T08:10:42+08:00"
tags: ["networking", "ssh", "tunneling", "frp", "infrastructure"]
description: "Complete guide to setting up SSH tunneling using FRP (Fast Reverse Proxy) to access local servers through a public IP server"
draft: true
---

# FRP User Guide: SSH Tunneling Through Public Server

## Introduction

FRP (Fast Reverse Proxy) is a high-performance reverse proxy application that helps you expose a local server behind a NAT or firewall to the internet. This guide focuses on using FRP to create SSH tunnels, allowing you to securely access your local servers through a public IP server.

## What is FRP?

FRP consists of two main components:
- **frps (FRP Server)**: Runs on a server with a public IP address
- **frpc (FRP Client)**: Runs on your local machine behind NAT/firewall

## How FRP Works for SSH Tunneling

### Traditional SSH Access Problem
```
Internet → [Firewall/NAT] → Local Server (192.168.1.100:22)
```
When your local server is behind a NAT or firewall, it's not directly accessible from the internet.

### FRP Solution
```
Internet → Public Server (frps) → Tunnel → Local Server (frpc) → Local SSH (192.168.1.100:22)
```

FRP creates a secure tunnel between your local server and the public server, allowing external connections to reach your local services.

## Prerequisites

- A server with public IP (AWS EC2, DigitalOcean, etc.)
- Local server behind NAT/firewall
- Basic understanding of SSH and networking

## Installation

### Download FRP
```bash
# Download the latest release from GitHub
wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz
cd frp_0.52.3_linux_amd64
```

## Configuration

### 1. Server Configuration (frps.ini)

On your public server (AWS VPS), create `frps.ini`:

```ini
[common]
# FRP server listening port
bind_port = 7000

# Dashboard (optional)
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = your_password

# Authentication token (recommended)
token = your_secure_token_here

# Logging
log_file = /var/log/frps.log
log_level = info
log_max_days = 3
```

### 2. Client Configuration (frpc.ini)

On your local server, create `frpc.ini`:

```ini
[common]
# Public server address and port
server_addr = your_public_server_ip
server_port = 7000

# Authentication token (must match server)
token = your_secure_token_here

# SSH tunnel configuration
[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000

# Optional: Custom domain (if you have one)
# custom_domains = ssh.yourdomain.com
```

## Running FRP

### Start the Server (frps)
```bash
# On your public server
./frps -c frps.ini
```

### Start the Client (frpc)
```bash
# On your local server
./frpc -c frpc.ini
```

## Connecting via SSH

Once both services are running, you can connect to your local server through the public server:

```bash
# Connect to local server via public server
ssh -p 6000 username@your_public_server_ip

# Or if using custom domain
ssh -p 6000 username@ssh.yourdomain.com
```

## How SSH Tunneling Works with FRP

### Step-by-Step Process

1. **Client Connection**: External user connects to `public_server:6000`
2. **FRP Server**: Receives connection and forwards it through the tunnel
3. **FRP Client**: Receives forwarded connection and routes to `127.0.0.1:22`
4. **Local SSH**: Handles the SSH connection normally

### Network Flow Diagram

```
External User
    ↓ SSH to public_server:6000
Public Server (frps)
    ↓ Tunnel (port 7000)
Local Server (frpc)
    ↓ Forward to 127.0.0.1:22
Local SSH Service
```

## Advanced Configuration

### Multiple SSH Services

You can expose multiple SSH services by adding more `[ssh]` sections:

```ini
[ssh-server1]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000

[ssh-server2]
type = tcp
local_ip = 192.168.1.100
local_port = 22
remote_port = 6001
```

### Security Enhancements

#### 1. Enable Authentication Token
```ini
# In both frps.ini and frpc.ini
token = your_very_secure_random_token
```

#### 2. Use Custom Domains
```ini
[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000
custom_domains = ssh.yourdomain.com
```

#### 3. Enable TLS Encryption
```ini
[common]
# In frps.ini
tls_cert_file = /path/to/server.crt
tls_key_file = /path/to/server.key

# In frpc.ini
tls_enable = true
```

## Running as System Service

### Systemd Service for frps

Create `/etc/systemd/system/frps.service`:

```ini
[Unit]
Description=FRP Server
After=network.target

[Service]
Type=simple
User=frp
ExecStart=/opt/frp/frps -c /opt/frp/frps.ini
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Systemd Service for frpc

Create `/etc/systemd/system/frpc.service`:

```ini
[Unit]
Description=FRP Client
After=network.target

[Service]
Type=simple
User=frp
ExecStart=/opt/frp/frpc -c /opt/frp/frpc.ini
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl enable frps
sudo systemctl start frps

sudo systemctl enable frpc
sudo systemctl start frpc
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
- Check if frps is running on the public server
- Verify firewall rules allow port 7000 and 6000
- Ensure token matches between client and server

#### 2. Authentication Failed
- Verify the token is identical in both configurations
- Check if the token contains special characters that need escaping

#### 3. Port Already in Use
- Change the `remote_port` in frpc.ini
- Check what's using the port: `netstat -tulpn | grep :6000`

### Debugging Commands

```bash
# Check FRP processes
ps aux | grep frp

# Check port usage
netstat -tulpn | grep -E "(7000|6000)"

# View logs
tail -f /var/log/frps.log
tail -f /var/log/frpc.log

# Test connection
telnet your_public_server_ip 6000
```

## Security Best Practices

1. **Use Strong Authentication Tokens**: Generate random, long tokens
2. **Enable TLS**: Encrypt tunnel communication
3. **Firewall Rules**: Only open necessary ports
4. **Regular Updates**: Keep FRP updated to latest version
5. **Monitor Logs**: Regularly check logs for suspicious activity
6. **SSH Key Authentication**: Use SSH keys instead of passwords
7. **Fail2Ban**: Implement fail2ban for additional SSH protection

## Performance Considerations

- **Bandwidth**: FRP adds minimal overhead (~1-2%)
- **Latency**: Expect slight increase due to additional hop
- **Concurrent Connections**: FRP handles multiple connections efficiently
- **Resource Usage**: Low CPU and memory footprint

## Alternative Use Cases

FRP can be used for more than just SSH:

- **Web Services**: Expose local web applications
- **Database Access**: Secure database connections
- **File Sharing**: Access local file servers
- **Development**: Share local development servers

## Conclusion

FRP provides a robust solution for accessing local services through public servers. The SSH tunneling setup described in this guide offers a secure way to manage remote servers behind NAT/firewalls. With proper configuration and security measures, FRP can significantly improve your remote access capabilities.

Remember to always prioritize security by using strong authentication, enabling encryption, and monitoring your connections regularly.