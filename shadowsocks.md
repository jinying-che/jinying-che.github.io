# Setup Shadowsocks Server And Client

In this article, we will setup the Shadowsock Server and Client from scratch and solve the issue during and after the setup.

## Shadowsocks Server
Install the latest `Ubuntu` in vps, my vps provier is https://bandwagonhost.com/index.php, the route is: *My Service > KiwiVM Control Panel > Install new OS*

### 1. Installing Shadowsocks-libev
#### Install [Snap](https://snapcraft.io/about)
```
$ sudo apt update
$ sudo apt install snapd
$ sudo reboot
```
#### Install [Shadowsocks-libev](https://github.com/shadowsocks/shadowsocks-libev)
```
$ sudo snap install shadowsocks-libev
```

### 2. Configuring proxy server
```shell
# first time to use snap, this path should be the config convention of Snap apps 
sudo mkdir -p /var/snap/shadowsocks-libev/common/etc/shadowsocks-libev

sudo vim /var/snap/shadowsocks-libev/common/etc/shadowsocks-libev/config.json
```
#### config.json
```json
{
    "server":["::0", "0.0.0.0"],
    "server_port":4443,
    "password":"your password",
    "timeout":300,
    "method":"aes-256-gcm",
    "nameserver":"1.1.1.1",
    "mode":"tcp_and_udp"
}
```
**Note**: "server":["::0", "0.0.0.0"] --> support IPv4 and IPv6

### 3. Creating systemd service unit config
#### shadowsocks-libev-server@.service
```shell
$ sudo vim /etc/systemd/system/shadowsocks-libev-server@.service

[Unit]
Description=Shadowsocks-Libev Custom Server Service for %I
Documentation=man:ss-server(1)
After=network-online.target
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
Type=simple
Restart=always
RestartSec=5s
ExecStart=/usr/bin/snap run shadowsocks-libev.ss-server -c /var/snap/shadowsocks-libev/common/etc/shadowsocks-libev/%i.json

[Install]
WantedBy=multi-user.target
```
Two things to take note:
- `shadowsocks-libev-server@.service` is a filename (*systemd style*)
- `man systemd.service` to understand the details, btw it's better to set `Restart=always` if you prefer the log-term running


Start the service and make it managed by systemd
```shell
# Note that the @config is used to select the configuration file
$ sudo systemctl enable --now shadowsocks-libev-server@config
```

### 4. Troubleshooting
#### Command
```sh
# Status
$ sudo systemctl status shadowsocks-libev-server@config

# Log
# Check the certain process that managed by systemd
# journalctl is a command for viewing logs collected by systemd
$ journalctl -u shadowsocks-libev-server@config

# Check all the processes log
$ cd /var/log/
$ less syslog  # can check any related log, TBD
  ```

#### Cases
##### Process stopped unexpectedly
- Root Cause: process that managed by systemd will stop when user exit the session 
> https://github.com/systemd/systemd/issues/8486 
- Fix: `loginctl enable-linger`

## Shadowsocks Client
### Chrome
Enable the socks5 proxy for Chrome in macOS
1. `brew install shadowsocks-libev`
2. run `ss-local -h` to understand how to setup shadowsocks client locally, for example:
	- `ss-local -s server_ip -p port -k password -m aes-256-cfb -l 1081 -v`
3. install and setup SwitchyOmeg for Chrome: 
4. import [GFW List](https://shadowsockshelp.github.io/Shadowsocks/Chrome.html) and enable the auto-switch

### Global (Terminal)
Some request from termial or other Apps are supposed to go through the socks5 tunnel as well, the following steps will forward the traffic to the local port that listened by the shadowsocks client:
1. setup helper function in bash or zsh profile, so that it's able to control the proxy manually in the current terminal session via `proxy-on` or `proxy-off`:
	```sh
	function proxy-off(){
	    unset http_proxy
	    unset https_proxy
	    echo "proxy off"
	}
	
	function proxy-on() {
	    export no_proxy="localhost,127.0.0.1,localaddress,.localdomain.com"
	    export http_proxy="socks5://127.0.0.1:1081"
	    export https_proxy=$http_proxy
	    echo "proxy on: $http_proxy"
	}
	```
2. run `ss-local ... -v`
3. test via `curl cip.cc` or `curl ifconfig.me`, by right the ip that running shadowsocks server should be printed 

## Reference
- [systemd config](https://www.freedesktop.org/software/systemd/man/systemd.service.html) or check by `man systemd.service`
- https://www.linuxbabe.com/ubuntu/shadowsocks-libev-proxy-server-ubuntu
- https://upcloud.com/community/tutorials/install-shadowsocks-libev-socks5-proxy/
- https://unix.stackexchange.com/questions/225401/how-to-see-full-log-from-systemctl-status-service
- https://shadowsockshelp.github.io/Shadowsocks/Chrome.html
