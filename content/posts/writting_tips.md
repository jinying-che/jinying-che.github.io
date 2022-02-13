---
title: "Writting Tips"
date: 2022-01-22T11:06:46+08:00
draft: true
---

Here is the colloction that I think maybe useful for technical artical writting.
<!--more--> 

> [The Zen of Go](https://dave.cheney.net/2020/02/23/the-zen-of-go) 1 - 3 
1. Without new blood and new ideas, our community become **myopic and wither**. 
2. ultimately
3. I tend to pick on net/http a lot, and this is not because it is bad, in fact it is the opposite, it is the most successful, oldest, most used API in the Go codebase. And because of that its design, evolution, and **shortcoming have been thoroughly picked over**. Think of this as **flattery**, not **criticism**.
> [Hardware Memory Models](https://research.swtch.com/hwmm)
4. Hardware designers and compiler developers need a clear answer to how **precisely** the hardware and compiled code are allowed to behave when executing a given program. 
> [Partitioning GitHub’s relational databases to handle scale](https://github.blog/2021-09-27-partitioning-githubs-relational-databases-scale/) 5 - 9
5. Over the years, this architecture went through many iterations to support GitHub’s growth and **ever-evolving resiliency** requirements.
6. With GitHub’s growth, this **inevitably led to** challenges.
7. the linter ensures that no new violations are introduced by accident.
8. MySQL’s query planner can sometimes create suboptimal query execution plans, **whereas** an application-side join has a more stable performance cost.
9. We often choose to **leverage** “boring” technology that has been proven to work at our scale, as reliability **remains** the primary concern.
> Golang sync.Pool Doc
10. Pool's purpose is to cache allocated but unused items for later reuse, **relieving** pressure on the garbage collector.
