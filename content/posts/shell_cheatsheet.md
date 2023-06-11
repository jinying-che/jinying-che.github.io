---
title: "Shell Cheatsheet"
date: "2023-06-08T15:41:00+08:00"
tags: ["cheatsheet", "shell"]
description: "Cheatsheet Every Day!"
---

Some skills of daily commands, they are useful but not worth creating a particular cheatsheet, so I put them here generally.

### [fzf](https://github.com/junegunn/fzf) + zsh
Add the fzf plugin for zsh, the terminal is fully enhanced!
```diff
- plugins=(git autojump zsh-autosuggestions zsh-syntax-highlighting)
+ plugins=(git autojump zsh-autosuggestions zsh-syntax-highlighting fzf)
```

Try some comands to see the fzf integartion, e.g.
- `cd **` + `TAB(key)`
- `Ctrl` + `r`
- ...

Reference:
- https://github.com/junegunn/fzf#fuzzy-completion-for-bash-and-zsh

### [mycli](https://github.com/dbcli/mycli) pager
By default, `mycli` shows the sql result in a new window (press `q` to quit and all results gone), but it would be annoyed when result needs to be kept in the current window, the behavior is controlled by **Pager Configuraton**. 

On macOS and Linux, the pager will default to less for most users.
```toml
# disable pager 
enable_pager = False 
```

Reference:
- https://www.mycli.net/pager


### linux/unix os version
```sh
- cat /etc/os-release
- lsb_release -a
```

### 批量删除进程

```shell
ps aux | grep redis | grep -v grep | awk '{print $2}' | xargs kill -9
```

其中`awk '{print $2}' `是打印所有进程的**pid**

## 2>&1

**> ** ：代表重定向到哪里(**>**：会覆盖，**>>**：追加，不覆盖)
**1 ** ：表示stdout标准输出，系统默认值是1（**0**代表标准输入）
**2 ** ：表示stderr标准错误
**& ** ：表示等同于的意思，2>&1，表示2的输出重定向等同于1（**错误输出**的位置同**标准输出**一样）

## #!

`#!` 是一个约定的标记，它告诉系统这个脚本需要什么解释器来执行，即使用哪一种 Shell



## shell 编程

#### 关于[]

- 实际上是bash 中 test 命令的简写。即所有的 [ expr ] 等于 test expr (expr与[]之间，要有空格)
- 使用逻辑判断，应该是：`[] || []`和`[] && []`

#### 变量

- 变量赋值不应有空格： `param=$1`

##ssh

- ssh 连接服务器

  `ssh -P port username@ip`

- ssh 使用scope复制本机文件到远程服务器

  `scope local-directory/local-file username@ip:remote-directory`

- ssh 公钥登陆流程：

  > 所谓"公钥登录"，原理很简单，就是用户将自己的公钥储存在远程主机上。登录的时候，远程主机会向用户发送一段随机字符串，用户用自己的私钥加密后，再发回来。远程主机用事先储存的公钥进行解密，如果成功，就证明用户是可信的，直接允许登录shell，不再要求密码。
  
- 打印连接**debug**信息(分析连接流程)： `ssh -v root@74.82.202.131 -p 28382` 

  > -v 参数：打印debug信息

##Disk 

> **df** displays the amount of disk space available on the file system containing each file name argument

- `df -lh` : If no file name is given, the space available on all currently mounted file systems is shown.
- `df -lh path`: show information about the file system on which each path resides

> **du** Summarize disk usage of the set of FILEs, recursively for directories.

- `du -h --max-depth=1` : display the usage of first depth in a human readable format
- `du -hs * | sort -rh | head -10` : display the usage of this depth and sort the output in a human readable format

## 查目录下的文件数

- ls -all | wc -l 

> Linux系统中的wc(Word Count)命令的功能为统计指定文件中的字节数、字数、行数，并将统计结果显示输出。

## 查看二进制(bin)文件 

For bin :

```
xxd -b file
```

For hex :

```
xxd file
```
## 进程进入后台并运行

> 这是个悲伤的故事，把socket服务通过`ctrl-z`放入后台，天真地认为进程在后台运行，其实进程已被暂停

- 后台运行： `command &`（在命令后加**&**）
- 后台暂停： `ctrl-z`（将线程放入后台，并暂停其运行）

## 解压

####tar

- 解压：`tar -xvf file.jar.gz`
- 解压到指定文件：
  - `mkdir directory`
  - `tar -xvf file.jar.gz -C directory`
- 压缩：`tar -zcvf directory/filename file||directory `

#### zip

- 解压：`gzip -d file.gz`
- 压缩：`gzip file`

## Linux 网络

> - nethogs: 按进程查看流量占用
> - iptraf: 按连接/端口查看流量
> - ifstat: 按设备查看流量
> - ethtool: 诊断工具
> - tcpdump: 抓包工具
> - ss: 连接查看工具
> - 其他: dstat, slurm, nload, bmon

###查看tcp端口

- 查看所有tcp端口的使用情况：`netstat -nptl | grep pid/port/app` （可能需要root权限）
- check the TCP status : `netstat -atp`
  - For Established : `netstat -atp | grep ESTABLISHED`
  - For Established and specific port :  `netstat -atp | grep ESTABLISHED | grep port` 
- 端口即文件：`lsof -i:port` （可能需要root权限）
- For Mac: `netstat -an -ptcp | grep LISTEN`

### ss 

> 它利用到了TCP协议栈中tcp_diag。tcp_diag是一个用于分析统计的模块，可以获得Linux 内核中第一手的信息，这就确保了ss的快捷高效。当然，如果你的系统中没有tcp_diag，ss也可以正常运行，只是效率会变得稍慢

ss的用法与netstat类似，比如`ss -nptl | grep pid`

###网络配置

> [reference:](http://www.cnblogs.com/xiaoluo501395377/archive/2013/05/26/3100065.html)
>
> Linux支持将多块物理网卡绑定成一块逻辑网卡，绑定后的逻辑网卡可以并行使用组成其的所有物理网卡，通过这样的方式可以提高带宽以及网路的稳定性。
>
> Linux下支持三种模式的网卡绑定：
>
> **①模式0**：**平衡轮训**　　使用这种模式来进行多网卡绑定时我们可以提高网络的带宽，其流量是从绑定的多块网卡上平均分配的
>
> **②模式1**：**主动备份**　　使用这种模式来进行多网卡绑定时我们可以提高网络的稳定性，这种模式不会提高网络的带宽，每次只有一块网卡在走流量，只有当这块网卡发生故障时，绑定在一起的其它物理网卡才会工作
>
> **③模式3**：**广播模式**　　这种模式一般都不用
>
> 我们如果想通过多网卡绑定来提升网络的带宽，就选择模式0，如果想提高网络的稳定性，则选择模式1

模式由bond0配置文件中的BONDING_OPTS决定，配置文件在`/etc/network/network-scripts`路径下，文件命名可能如下：ifcfg-bond0、ifcfg-eth0、ifconfig-eth1等等

```
//ifcfg-bond0 文件

DEVICE=bond0
ONBOOT=yes
BONDING_OPTS="miimon=1000 mode=1" //模式选择
TYPE=Ethernet
BOOTPROTO=none
IPADDR=10.86.67.42
NETMASK=255.255.255.0
```

### 端口连通性测试

`nc -zv ip port`

`telnet ip port`

> nc 命令可起个临时的tcp服务  : `nc -l`

## sudo and su

####sudo vs su

- 两个命令的最大区别是：`sudo` 命令需要输入当前用户的密码，`su` 命令需要输入 root 用户的密码
- 两个命令之间的另外一个区别是其默认行为。`sudo` 命令只允许使用提升的权限运行单个命令，而 `su` 命令会启动一个新的 shell，同时允许使用 root 权限运行尽可能多的命令，直到明确退出登录####

#### sudo su

以当前用户的身份（即只需要当前用户的密码），就可登录root用户，而不需要root密码

#### su vs su - 

前者在切换到 root 用户之后仍然保持旧的（或者说原始用户的）环境，而后者则是创建一个新的环境（由 root 用户 `~/.bashrc` 文件所设置的环境），相当于使用 root 用户正常登录（从登录屏幕登录）

**所以推荐使用 `su -`**

> [深入理解 sudo 与 su 之间的区别](https://linux.cn/article-8404-1.html)

## 更改文件所属用户及用户组

`chown -R user:group file/directory`

## 查看文件类型

`file` 命令：

-  `file filename` 若显示为data，可能为压缩文件

cat /etc/sysconfig/network 

> 解释：-R 递归修改 

## 查看进程所在目录

### pwdx

```sh
$ pwdx <PID>
```

### lsof

```sh
$ lsof -p <PID> | grep cwd
```

### /proc

```sh
$ readlink -e /proc/<PID>/cwd
```

## Linux 系统参数

#####一个进程文件句柄数限制

- 查看
  -  `ulimit -n` (默认soft)
  -  `ulimit -Hn`(hard)
- 临时修改：ulimit -n 1000000，只对当前登录用户目前的使用环境有效，系统重启或用户退出后就会失效
- 永久修改：编辑 /etc/security/limits.conf 文件，( 修改完重新登录就可以见到)， 修改后内容为

```text
* soft nofile 1000000
* hard nofile 1000000
```

> soft是一个警告值，而hard则是一个真正意义的阀值，超过就会报错。soft 指的是当前系统生效的设置值。hard 表明系统中所能设定的最大值nofile - 打开文件的最大数目星号表示针对所有用户，若仅针对某个用户登录ID，替换星号。

##### 端口数量（压测客户端）

- 查看：`cat /proc/sys/net/ipv4/ip_local_port_range `

- 临时修改： `echo "1024 65535"> /proc/sys/net/ipv4/ip_local_port_range`

- 永久修改：`/etc/sysctl.conf 增加 net.ipv4.ip_local_port_range= 1024 65535 `

> 并令其生效sysctl -p现在可以使用的端口达到64510个

#####系统全局可用句柄数目限制

- 查看：`cat /proc/sys/fs/file-max`
- 当前会话修改，可以这么做：`echo 1048576 > /proc/sys/fs/file-max` 但系统重启后消失。
- 永久修改，要添加到 /etc/sysctl.conf 文件中：`fs.file-max = 1048576`保存并使之生效：`sysctl -p`

## Top

> 以前只是在 linux 机器上使用 top 命令。常用的快键键是:
>
> - p 键 - 按 cpu 使用率排序
> - m 键 - 按内存使用量排序
>
> 这 2 个快捷键在 mac 上都不一样。对应的是，先输入 o，然后输入 cpu 则按 cpu 使用量排序，输入 rsize 则按内存使用量排序。
>
> 如果记不清了，可以在 top 的界面上按 `?`，在弹出的帮助界面中即可看到。

#### 查看进程

`top -H -p pid`

## CPU

#### 查看物理cpu个数

`grep 'physical id' /proc/cpuinfo | sort -u | wc -l`

####查看核心数量

`grep 'core id' /proc/cpuinfo | sort -u | wc -l`

####查看线程数或逻辑CPU的个数

`grep 'processor' /proc/cpuinfo | sort -u | wc -l`

### Docker中cpu的查看

- `cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us`
- `cat /sys/fs/cgroup/cpu/cpu.cfs_period_us`

> `cfs_quota_us`和`cfs_period_us`两个值是联合使用的，两者的比值，即`cfs_quota_us`/`cfs_period_us`代表了该容器实际可用的做多的CPU核数。
>
> 比如`cfs_quota_us`=50000，`cfs_period_us`=100000，那么二者的比值是0.5，也就是说该容器可以使用0.5个cpu。这样的管控粒度更细，在cgroup使用systemd时最低可以到0.01核。

## watch

watch命令默认每隔2秒执行后面参数给出的命令，也可手动指定，最小间隔0.1秒

`watch -n 0.1 date`:  每隔100ms，打印日期

## curl

#### 分析http请求耗时

1. 构建输出格式

   ```txt
       curl-format.txt
       
       time_namelookup:  %{time_namelookup}\n
          time_connect:  %{time_connect}\n
       time_appconnect:  %{time_appconnect}\n
         time_redirect:  %{time_redirect}\n
      time_pretransfer:  %{time_pretransfer}\n
    time_starttransfer:  %{time_starttransfer}\n
                       ----------\n
            time_total:  %{time_total}\n
   ```

   > - `time_namelookup`：DNS 域名解析的时候，就是把 `https://zhihu.com` 转换成 ip 地址的过程
   > - `time_connect`：TCP 连接建立的时间，就是三次握手的时间
   > - `time_appconnect`：SSL/SSH 等上层协议建立连接的时间，比如 connect/handshake 的时间
   > - `time_redirect`：从开始到最后一个请求事务的时间
   > - `time_pretransfer`：从请求开始到响应开始传输的时间
   > - `time_starttransfer`：从请求开始到第一个字节将要传输的时间
   > - `time_total`：这次请求花费的全部时间

2. curl -w "@curl-format.txt" -o /dev/null -s -L "http://cizixs.com"`

## grep

- 取反： `-v`
- Ignore case: `-i`

## lsof

> lsof (list open files)是一个列出当前系统打开文件的工具。拥有查看你进程开打的文件，打开文件的进程，进程打开的端口(TCP、UDP)，找回/恢复删除的文件等功能

##Shell Script

- `lsof -i | awk '{print $2}' | sort | uniq -c | sort -nr` :

  > sort by the internet file descriptor, in reverse order

- Port status 

  `lsof -nP -i:8081`
  
- QPS

  `grep -a "got job" notify_server.log | cut -c -19 | uniq -c`

## innotop

> The monitor tool for mysql

- login:` innotop -uroot -p password`

## history

- execute comand by number line: `!number`

## scp

- repLocal to server (file): `scp path/file username@ip:/where/to/put`  
- Local to server (dir): `scp -r path/file username@ip:/where/to/put`  

##nohup

> run a command immune to hangups, with output to a non-tty

#### keep process running when ssh log out

`nohup command &`

####  and no **nohup.out**

`nohup command > /dev/null 2>&1 &`

## PS

- To print a process tree: `ps axjf` (alse add some grep: `ps axjf | grep "keyname"`)  

## xargs

- **list files (exclude some files that you don't want) , then copy to some dictionary**

  `ls -S | grep -E -v 'GPNServer.log*' | xargs cp -r -t ../gpns_backup`
  
- **list process, then get the specific process that you want to kill, then kill**

  `ps aux | grep kafka_2 | grep server | awk {'print$2'} | xargs kill -9`

## find

`find * -name filename`



