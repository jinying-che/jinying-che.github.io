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
The superblock records various information about the enclosing filesystem, such as block counts, inode counts, supported features, maintenance information, and more.

```c
/* https://github.com/torvalds/linux/blob/b9ddbb0cde2adcedda26045cc58f31316a492215/include/linux/fs.h#L1188 */
struct super_block {
	struct list_head	s_list;		/* Keep this first */
	dev_t			s_dev;		/* search index; _not_ kdev_t */
	unsigned char		s_blocksize_bits;
	unsigned long		s_blocksize;
	loff_t			s_maxbytes;	/* Max file size */
	struct file_system_type	*s_type;
	const struct super_operations	*s_op;
	const struct dquot_operations	*dq_op;
	const struct quotactl_ops	*s_qcop;
	const struct export_operations *s_export_op;
	unsigned long		s_flags;
	unsigned long		s_iflags;	/* internal SB_I_* flags */
	unsigned long		s_magic;
	struct dentry		*s_root;
	struct rw_semaphore	s_umount;
	int			s_count;
	atomic_t		s_active;
    ...
}
```
Show the super block info in Linux:
> all examples in this post are from my vps (OS: Ubuntu 22.04.2 LTS)

```shell
$ df -h
Filesystem      Size  Used Avail Use% Mounted on
tmpfs            96M  1.3M   95M   2% /run
/dev/vda1        24G   12G   11G  52% /
tmpfs           479M     0  479M   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
tmpfs            96M  4.0K   96M   1% /run/user/0

$ dumpe2fs /dev/vda1
dumpe2fs 1.46.5 (30-Dec-2021)
Filesystem volume name:   <none>
Last mounted on:          /
Filesystem UUID:          cc673143-6902-4174-990e-8cba0304cb7a
Filesystem magic number:  0xEF53
Filesystem revision #:    1 (dynamic)
Filesystem features:      has_journal ext_attr resize_inode dir_index filetype needs_recovery extent 64bit flex_bg sparse_super large_file huge_file dir_nlink extra_isize metadata_csum
Filesystem flags:         signed_directory_hash
Default mount options:    user_xattr acl discard
Filesystem state:         clean
Errors behavior:          Continue
Filesystem OS type:       Linux
Inode count:              6537600
Block count:              6553339
Reserved block count:     327666
Free blocks:              3333553
Free inodes:              6325191
First block:              0
Block size:               4096
Fragment size:            4096
...
```

#### Directory Entry (Dentry)
1. Dentry is used by VFS to represent information about the **directories and files** inside the **memory**
2. Dentries live in RAM and are never saved to disc: they exist only for performance. (RAM cannot save all dentries -> LFU cache)
3. An individual dentry usually has a pointer to an inode
4. It's a fast look-up mechanism to translate a pathname (filename) into a specific **dentry** then **inode**

```c
/* https://github.com/torvalds/linux/blob/b9ddbb0cde2adcedda26045cc58f31316a492215/include/linux/dcache.h#L82 */
struct dentry {
	/* RCU lookup touched fields */
	unsigned int d_flags;		/* protected by d_lock */
	seqcount_spinlock_t d_seq;	/* per dentry seqlock */
	struct hlist_bl_node d_hash;	/* lookup hash list */
	struct dentry *d_parent;	/* parent directory */
	struct qstr d_name;
	struct inode *d_inode;		/* Where the name belongs to - NULL is
					 * negative */
	unsigned char d_iname[DNAME_INLINE_LEN];	/* small names */

	/* Ref lookup also touches following */
	struct lockref d_lockref;	/* per-dentry lock and refcount */
	const struct dentry_operations *d_op;
	struct super_block *d_sb;	/* The root of the dentry tree */
	unsigned long d_time;		/* used by d_revalidate */
	void *d_fsdata;			/* fs-specific data */

	union {
		struct list_head d_lru;		/* LRU list */
		wait_queue_head_t *d_wait;	/* in-lookup ones only */
	};
	struct list_head d_child;	/* child of parent list */
	struct list_head d_subdirs;	/* our children */
	/*
	 * d_alias and d_rcu can share memory
	 */
	union {
		struct hlist_node d_alias;	/* inode alias list */
		struct hlist_bl_node d_in_lookup_hash;	/* only for in-lookup ones */
	 	struct rcu_head d_rcu;
	} d_u;
} __randomize_layout;
```

#### Index Node 

#### file

## What happens when reading a file in Linux?
TBD Diagram to elaborate on the concepts above

## Block Layer

## Troubleshooting

## Linux Storage Stack
![linux storage stack](/images/Linux-storage-stack-diagram_v6.2/linux_storage_stack.svg)
https://www.thomas-krenn.com/en/wiki/Linux_Storage_Stack_Diagram

## Reference
- https://developer.ibm.com/tutorials/l-linux-filesystem/
- [super block -- kernel doc](https://www.kernel.org/doc/html/latest/filesystems/ext4/globals.html?highlight=file+system+super+block)
- [vfs overview -- kernel doc](https://www.kernel.org/doc/html/latest/filesystems/vfs.html?highlight=inode)
- [What is a Superblock, Dentry, Inode and a File?](https://itslinuxfoss.com/what-is-superblock-inode-dentry-and-file/#:~:text=The%20superblock%20is%20the%20data,of%20bytes%20in%20different%20forms.)
