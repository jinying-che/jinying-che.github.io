---
title: "systemd"
date: "2024-07-03T08:19:14+08:00"
tags: ["systemd", "linux"]
description: "systemd in nutshell"
---
## what is systemd?
1. systemd is a suite of basic building blocks for a Linux system. 
2. It provides a system and service manager that runs as PID 1 and starts the rest of the system.

## Where is the config file?
```bash
systemd-analyze unit-paths
```
The systemd manager scans many directories to load unit files, for user-defined units:
```bash
/etc/systemd/system
```

## Unit File
A unit file is a plain text ini-style file that encodes information about a service, a socket, a device, a mount point, an automount point, a swap file or partition, a start-up target, a watched file system path, a timer controlled and supervised by systemd(1), a resource management slice or a group of externally created processes.

e.g. sshd service unit file, `cat /lib/systemd/system/sshd.service`:
```bash
[Unit]
Description=OpenBSD Secure Shell server
Documentation=man:sshd(8) man:sshd_config(5)
After=network.target auditd.service
ConditionPathExists=!/etc/ssh/sshd_not_to_be_run

[Service]
EnvironmentFile=-/etc/default/ssh
ExecStartPre=/usr/sbin/sshd -t
ExecStart=/usr/sbin/sshd -D $SSHD_OPTS
ExecReload=/usr/sbin/sshd -t
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure
RestartPreventExitStatus=255
Type=notify
RuntimeDirectory=sshd
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
Alias=sshd.service
```

`WantedBy=multi-user.target` means the service will be started when the system enters multi-user mode. (equal to runlevel 2 in SysV init system)

**Target** A unit configuration file whose name ends in ".target" encodes information about a target unit of systemd. Target units are used to group units and to set synchronization points for ordering dependencies with other unit files.

Target units provide a more flexible replacement for SysV runlevels in the classic SysV init system.
```bash
lrwxrwxrwx 1 root root   15 Nov 22  2023 runlevel0.target -> poweroff.target
lrwxrwxrwx 1 root root   13 Nov 22  2023 runlevel1.target -> rescue.target
lrwxrwxrwx 1 root root   17 Nov 22  2023 runlevel2.target -> multi-user.target
lrwxrwxrwx 1 root root   17 Nov 22  2023 runlevel3.target -> multi-user.target
lrwxrwxrwx 1 root root   17 Nov 22  2023 runlevel4.target -> multi-user.target
lrwxrwxrwx 1 root root   16 Nov 22  2023 runlevel5.target -> graphical.target
lrwxrwxrwx 1 root root   13 Nov 22  2023 runlevel6.target -> reboot.target
```

e.g. multi-user.target
```bash
cat lib/systemd/system/multi-user.target

[Unit]
Description=Multi-User System
Documentation=man:systemd.special(7)
Requires=basic.target
Conflicts=rescue.service rescue.target
After=basic.target rescue.service rescue.target
AllowIsolate=yes
```

## References
- https://systemd.io/
- https://en.wikipedia.org/wiki/Systemd
- https://www.baeldung.com/linux/systemd-target-multi-user
