---
title: "Tech Writing"
date: "2023-09-03T15:26:12+08:00"
tags: ["writing", "English Learning"]
description: "tips for tech writing in english"
---

Here is the colloction that I think maybe useful for technical article writting.

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
> [SOCKS Protocol Version 5](https://datatracker.ietf.org/doc/html/rfc1928)
11. there exists a need to provide a general framework for these protocols to transparently and securely **traverse** a firewall.
> https://clig.dev/
12. Sometimes when using args, it’s impossible to add new input without breaking existing behavior or creating **ambiguity**.
13. Don’t have **ambiguous** or similarly-named commands. For example, having two subcommands called “update” and “upgrade” is quite confusing. You might want to use different words, or **disambiguate** with extra words.
14. If you have to append or modify to a system-wide config file, use a dated comment in that file to **delineate** your additions.
15. Apply configuration parameters in order of **precedence**. Here is the **precedence** for config parameters, from highest to lowest
16. You’ll **step on the toes** of other commands and confuse users. [slang]
17. The concurrency properties of HTTP/2 allow proxies to be more **performant**.
18. A failure of a single microservice can have a **cascading** effect on all microservices and can significantly affect system availability.
