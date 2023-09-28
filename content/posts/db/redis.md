---
title: "Redis"
date: "2019-09-16T17:37:10+08:00"
tags: ["database", "redis", "nosql"]
description: "Redis Overview"
---

## Data Structure
![redis data structure](/images/redis_data_structure.png)

## redis配置

1. redis初始并不设置所用内存大小，默认会使用全部物理内存，但有`maxmemory`选项可以配置。

   ```
   # In short... if you have slaves attached it is suggested that you set a lower
   # limit for maxmemory so that there is some free RAM on the system for slave
   # output buffers (but this is not needed if the policy is 'noeviction').
   #
   # maxmemory <bytes>
   ```


## Redis 命令

- ###zrem

  这个命令的返回值很特别：

  1. zset中存在的元素被删除，则返回1
  2. zset中不存在的元素、不存在的zset的key，返回0
  3. key存在，但不是zset类型，报错

##LUA



## 碎片率

>     出现高内存碎片问题的情况：大量的更新操作，比如append、setrange；大量的过期键删除，释放的空间无法得到有效利用 
>
>     解决办法：数据对齐，安全重启（高可用/主从切换）。

## 数据结构

#### 列表（list）

- 压缩列表
  - 每个数据节点会记录：前一个节点的长度（previous_entry_length）、编码（encoding）、节点的值（content）
- 双向循环链表
  - 会有单独的**list**的对象，来记录链表的**头、尾、长度**等信息

#### 字典（hash）

- 压缩列表
  
  - 将健值对依次放入压缩列表，查询复杂度为0(n)，需要遍历
  
- 散列表

  > **解决冲突：**通过链表法解决，每个数据节点都有**next**指针，冲突的节点会从头部插入
  >
  > **rehash期间:**
  >
  > - 字典的删除、查找、更新，会在两个哈希表上进行，插入操作只会在新表上进行
  > - 渐进式rehash会维护一个游标（rehashidx），每次有请求时，会按顺序进行rehash，直到将旧的hash表重新映射到新的hash表
  > - 负载因子：在进行**BGSAVE**或者**BGREWRITEAOF**，会fork子进程来后台处理，大多数操作系统都是通过写时复制的策略，即子进程在读操作时，会共享而不复制父进程的内存，只有在写时，才会复制，所以在此期间会尽量控制写操作，减少内存的复制，因此负载因子会升高

####集合 (set)

- 有序数组
- 散列表

#### 有序集合 (sorted set)

- 压缩列表
- 同时使用跳跃表和字典
  - 查询一组数据(zrange)利用跳跃表
  - 查询单个数据用字典

## 事务

- redis的事务，是通过客户端的事务状态、服务端的队列，简单封装redis命令实现的
- 事务中的命令要不就全部执行，或者都不执行
  - 当入队的命令出错时，事务取消，都不执行
  - 当部分命令失败时，继续执行
    - redis不提供回滚机制
    - 部分出错的命令结果会返回给客户端，客户端会根据错误情况进行处理，保证业务逻辑正确

## RDB

## AOF



## Referrence
- https://blog.bytebytego.com/p/why-is-redis-so-fast
