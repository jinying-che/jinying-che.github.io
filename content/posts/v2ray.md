---
title: "v2ray setup"
date: "2024-05-19T11:10:54+08:00"
tags: ["network", "protocol"]
description: "https://www.v2fly.org/"
---

[V2Ray](https://github.com/v2fly/v2ray-core) is a tool under Project V. Project V is a project that includes a set of tools for building specific network environments, and V2Ray is the core one.

### Install
#### Server
The v2ray server is usually hosted in a linux server, the [official way](https://github.com/v2fly/fhs-install-v2ray) is to install with a script, which setups the systemd config as well.
```sh
# run with root privilege
bash <(curl -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh)

# output
installed: /usr/local/bin/v2ray
installed: /usr/local/share/v2ray/geoip.dat
installed: /usr/local/share/v2ray/geosite.dat
installed: /usr/local/etc/v2ray/config.json
installed: /var/log/v2ray/
installed: /var/log/v2ray/access.log
installed: /var/log/v2ray/error.log
installed: /etc/systemd/system/v2ray.service
installed: /etc/systemd/system/v2ray@.service
```
#### Client
```sh
# macos 
brew install v2ray
```

### Run
#### Server
For v2ray server, we use [systemd](https://systemd.io/) to manage the v2ray process in `/usr/local/etc/v2ray/config.json` which is empty after installation. We modify the config based on the [Novice Guide](https://www.v2fly.org/en_US/guide/start.html#server):
```json
{
    "log": {
        "loglevel": "warning",
        "access": "/var/log/v2ray/access.log",
        "error": "/var/log/v2ray/error.log"
    },
    "inbounds": [
        {
            "port": 10086,
            "protocol": "vmess",
            "settings": {
                "clients": [
                    {
                        "id": "b831381d-6324-4d53-ad4f-8cda48b30811"
                    }
                ]
            }
        }
    ],
    "outbounds": [
        {
            "protocol": "freedom"
        }
    ]
}
```
run service via `systemctl`:
```sh
systemctl enable v2ray.service 
systemctl start v2ray.service

# check status
systemctl status v2ray.service

# check tcp port under LISTEN
ss -tlp
```
#### Client
follow the [Novice Guide](https://www.v2fly.org/en_US/guide/start.html#client) to setup the config and run: `v2ray -c path/to/config.json`
> NOTE: To successfully connect, you need to make sure that the id and port are consistent with the client in the server configuration.

After setup the local proxy `127.0.0.1:1081`, in order to route brower traffic to the v2ray tunnel, [Proxy SwitchyOmega](https://chrome.google.com/webstore/detail/proxy-switchyomega/padekgcemlokbadohgkifijomclgjgif) is quite helpful.


### Reference
- quick start: https://www.v2fly.org/en_US/guide/install.html
