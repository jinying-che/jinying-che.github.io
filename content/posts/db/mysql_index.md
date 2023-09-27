---
title: "MySQL Index"
date: "2019-06-05T11:48:53+08:00"
tags: ["database", "mysql"]
description: "MySQL Index Overview"
---

This post is based on MySQL **InnoDB** Storage Engine.

## Type
#### 1. Cluster Index
Each InnoDB table has a special index called the **clustered index** that stores row data. Typically, the clustered index is synonymous with the **primary key**.
#### 2. Secondery Index
In InnoDB, each record in a **secondary index** contains the primary key columns for the row, as well as the columns specified for the secondary index. InnoDB uses this primary key value to search for the row in the clustered index.

Typical Quering Flow: select with index --> secondary index -> primary index -> data row 
## Data Structure
The index data is organized in **B+ Tree** which is common data structure widely used in the relation databases. B+ Tree is upgrading from B Tree, it eliminates the drawback B-tree used for indexing by storing data pointers only at the leaf nodes of the tree.
### B+ Tree vs B Tree
![b tree vs b+ tree](/images/btree.svg)
##### Similarity
1. Both B Tree and B+ Tree are balanced tree. (Efficiency for quering, lower the tree height, less the disk access)
2. All leaf nodes are at the same level.
##### Difference
1. **B Tree** stores the data pointer (pointing to the cluster index) in all nodes, whereas, **B+ Tree** only stores in leaf nodes. (less space cost means internal node is able to store more index, hence tree is lower and more efficient)
2. All leaf nodes of **B+ Tree** are linked together in a linked list. This makes **range queries** efficient.
3. In a **B+ Tree**, every key appears twice, once in the internal nodes and once in the leaf nodes, whereas, in a **B Tree**, it's once.

## Leftmost Prefix Index
If the table has a multiple-column index, any leftmost prefix of the index can be used by the optimizer to look up rows.

## Referrence
- MySQL 8.0 Reference Manual:
    - https://dev.mysql.com/doc/refman/8.0/en/mysql-indexes.html
    - https://dev.mysql.com/doc/refman/8.0/en/innodb-index-types.html
    - https://dev.mysql.com/doc/refman/8.0/en/sorted-index-builds.html
