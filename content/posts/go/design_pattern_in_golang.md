+++
title = "Design Pattern In Golang"
date = 2021-05-24T08:37:07+08:00
draft = true
tags = [
	"golang",
]
+++

Design Pattern is my favorite part among all technologys, which makes code reuseable, maintainable and readable. The most important, coding is becoming a art creation with Design Pattern, the elegant thing.
<!--more-->

Golang is neither a pure Object Oriented Language, nor a Functional Language, which has own design philosophy and is influenced by Unix a lot. So the traditional Design Pattern in Golang may look a bit differnet compared with Java, meanwhile, there're also some special design patterns created because function is the first class and we have goroutine and channel in Golang.  

From my personal point of view, the following patterns are really useful in practice.

### Pipeline 
- https://blog.golang.org/pipelines

### Options
- https://github.com/uber-go/guide/blob/master/style.md#functional-options

### IOC (Inversion Of Control)
- https://www.reddit.com/r/golang/comments/3awbyl/dependency_injection_by_overriding_interfaces/
- https://play.golang.org/p/NOVKZCxpca
#### DI (Dependency Injection)
- https://blog.golang.org/wire
- https://blog.drewolson.org/dependency-injection-in-go
- https://en.wikipedia.org/wiki/Dependency_injection

### Graceful Shutdown
