---
title: "Linux File System"
date: "2023-09-30T15:25:41+08:00"
tags: ["linux"]
description: "File System Overview"
draft: true
---

## Architecture
![file system](/images/linux_file_system.svg)

## VFS
The Virtual File System (also known as the Virtual Filesystem Switch) is the software layer in the kernel that provides the filesystem interface to userspace programs via system call. It also provides an abstraction within the kernel which allows different filesystem implementations to coexist.

A VFS specifies an interface (or a "contract") between the kernel and a concrete file system. Therefore, it is easy to add support for new file system types to the kernel simply by fulfilling the contract.

#### Superblock

#### Directory Entry

#### Index Node 

#### file

## Block Layer

## Troubleshooting

## Linux Storage Stack
![linux storage stack](/images/Linux-storage-stack-diagram_v6.2/linux_storage_stack.svg)
https://www.thomas-krenn.com/en/wiki/Linux_Storage_Stack_Diagram

## Reference
- https://developer.ibm.com/tutorials/l-linux-filesystem/
