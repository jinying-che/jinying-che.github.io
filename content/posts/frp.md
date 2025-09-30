---
title: "FRP User Guide: SSH Tunneling Through Public Server"
date: "2025-09-30T08:10:42+08:00"
tags: ["network", "ssh", "frp"]
description: "Complete guide to setting up SSH tunneling using FRP (Fast Reverse Proxy) to access local servers through a public IP server"
---

## Introduction

FRP (Fast Reverse Proxy) is a high-performance reverse proxy application that helps you expose a local server behind a NAT or firewall to the internet. This guide focuses on using FRP to create SSH tunnels, allowing you to securely access your local servers through a public IP server.

## What is FRP?

FRP consists of two main components:
- **frps (FRP Server)**: Runs on a server with a public IP address
- **frpc (FRP Client)**: Runs on your local machine behind NAT/firewall

## How FRP Works for SSH Tunneling

- Traditional SSH Access Problem
  ```
  Internet → [Firewall/NAT] → Local Server (192.168.1.100:22)
  ```
  When your local server is behind a NAT or firewall, it's not directly accessible from the internet.

- FRP Solution
  ```
  Internet → Public Server (frps) → Tunnel → Local Server (frpc) → Local SSH (192.168.1.100:22)
  ```
  
  FRP creates a secure tunnel between your local server and the public server, allowing external connections to reach your local services.
  
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

## SSH Tunneling Usage 
Here is the SSH Tunneling Example, actually FRP can be used for more than just SSH:
- **Web Services**: Expose local web applications
- **Database Access**: Secure database connections
- **File Sharing**: Access local file servers
- **Development**: Share local development servers

for more usage, pls see [details](https://gofrp.org/en/docs/examples/)
### Prerequisites 
```sh
# Download FRP from the latest release page, get the binary and default config files
wget https://github.com/fatedier/frp/releases/download/v0.65.0/frp_xxx.tar.gz
tar -xzf frp_xxx.tar.gz

# Move the binaries and configuration files accordingly
sudo mv frp_xxx/frps /usr/local/bin/
sudo mv frp_xxx/frps.toml /etc/systmd/system/

sudo mv frp_xxx/frpc /usr/local/bin/
sudo mv frp_xxx/frpc.toml /etc/systmd/system/
```
update the config files as below
### Public Server With Static IP
- frps.toml (on public server)
  ```toml
  # FRP server listening port
  bindPort = 7000
  
  # Dashboard (optional)
  webServer.addr = "0.0.0.0"
  webServer.port = 7500
  webServer.user = "admin"
  webServer.password = "your_password"
  
  # Authentication token (recommended)
  auth.token = "your_secure_token_here"
  
  # Logging
  log.to = "/var/log/frps.log"
  log.level = "info"
  log.maxDays = 3
  ```

- systemd service file for frps (on public server)
  ```ini
  [Unit]
  Description=FRP Server
  After=network.target
  
  [Service]
  Type=simple
  User=frp
  ExecStart=/usr/local/frps -c /etc/systemd/system/frps.toml
  Restart=always
  RestartSec=5
  
  [Install]
  WantedBy=multi-user.target
  ```

### Private Server Behind NAT/Firewall
- frpc.toml (on local server)
  ```toml
  # Public server address and port
  serverAddr = "your_public_server_ip"
  serverPort = 7000
  
  # Authentication token (must match server)
  auth.token = "your_secure_token_here"
  
  # SSH tunnel configuration
  [[proxies]]
  name = "ssh"
  type = "tcp"
  localIP = "127.0.0.1"
  localPort = 22
  remotePort = 6000
  ```

- systemd service file for frpc (on local server)
  ```ini
  [Unit]
  Description=FRP Client
  After=network.target
  
  [Service]
  Type=simple
  User=frp
  ExecStart=/usr/local/frpc -c /etc/systemd/system/frpc.toml
  Restart=always
  RestartSec=5
  
  [Install]
  WantedBy=multi-user.target
  ```

## FRP's Design Philosophy

### Client-Driven Configuration Model

FRP follows a **client-driven configuration philosophy** where the client (frpc) tells the server (frps) what services it wants to expose and on which ports. This design choice has several important implications:

#### Why `remotePort` is in frpc.toml, not frps.toml

This is one of the most common points of confusion for new FRP users. Here's why:

1. **Dynamic Service Registration**: Services are registered dynamically when clients connect, not pre-configured on the server
2. **Multiple Client Support**: Different clients can request different ports without server pre-configuration
3. **Client Control**: Each client controls what it exposes and on which ports
4. **Server Simplicity**: The server only needs to know the control port (7000), not all service ports

#### Port Separation Philosophy

FRP clearly separates three types of ports:

- **`serverPort` (7000)**: Communication between frps and frpc (control channel)
- **`remotePort` (6000)**: External traffic to the exposed service (data channel)
- **`localPort` (22)**: Local service on the client machine

As stated in the official documentation:
> "The `localPort` (listened on the client) and `remotePort` (exposed on the server) are used for traffic going in and out of the frp system, while the `serverPort` is used for communication between frps and frpc."

#### Benefits of This Design

1. **Flexibility**: Clients can expose multiple services on different ports
2. **Simplicity**: Server configuration remains minimal
3. **Scalability**: Easy to add new clients without server reconfiguration
4. **Dynamic Allocation**: Ports are allocated when clients connect
5. **Client Autonomy**: Each client manages its own service exposure

#### Example: Multiple Services from One Client

```toml
# frpc.toml - One client exposing multiple services
serverAddr = "x.x.x.x"
serverPort = 7000

[[proxies]]
name = "ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 6000

[[proxies]]
name = "web"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8080
remotePort = 6001

[[proxies]]
name = "mysql"
type = "tcp"
localIP = "127.0.0.1"
localPort = 3306
remotePort = 6002
```

The server automatically handles all these port allocations when the client connects, without any server-side configuration changes.
