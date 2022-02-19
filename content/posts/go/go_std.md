---
title: "Golang Standard Library"
date: 2021-06-27T17:34:13+08:00
---
Dive into golang standard library, where we can learn how high quality code is written and what the golang convention and style is.
<!--more-->

### sync.WaitGroup
```golang
// go version 1.18rc1
type WaitGroup struct {
	noCopy noCopy

	// 64-bit value: high 32 bits are counter, low 32 bits are waiter count.
	// 64-bit atomic operations require 64-bit alignment, but 32-bit
	// compilers only guarantee that 64-bit fields are 32-bit aligned.
	// For this reason on 32 bit architectures we need to check in state()
	// if state1 is aligned or not, and dynamically "swap" the field order if
	// needed.
	state1 uint64
	state2 uint32
}
```
![wait group state byte representation](/images/wait_group.png)

It's based on golang **semaphore** model, implemented by `runtime_Semrelease` and `runtime_Semacquire`
  > semaphore is common mechanism used in concurrent progamming, like [Readers–writers problem](https://en.wikipedia.org/wiki/Readers%E2%80%93writers_problem)

Here is an example demostrating how it works, there are three tasks added, one task is done before `Wait()`, the other two are done after `Wait()`
- `Add()` increases or decreases the counter, only reset waiter to 0 when waiter != 0 (which means `Wait` has already been called then) and release the semaphore.
- `Wait()` increases the waiter and try to acquire the semaphore.

![wait group case](/images/wait_group_case.png)

### sync.Pool
