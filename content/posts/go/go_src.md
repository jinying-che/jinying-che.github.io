---
title: "Go Src"
date: 2021-06-27T17:34:13+08:00
---
Golang Source Code Tips 
<!--more-->

### sync.WaitGroup
```golang
type WaitGroup struct {
	noCopy noCopy

	// 64-bit value: high 32 bits are counter, low 32 bits are waiter count.
	// 64-bit atomic operations require 64-bit alignment, but 32-bit
	// compilers do not ensure it. So we allocate 12 bytes and then use
	// the aligned 8 bytes in them as state, and the other 4 as storage
	// for the sema.
	state1 [3]uint32
}
```
- It's based on golang **semaphore** model, implemented by `runtime_Semrelease` and `runtime_Semacquire`
  > not relevant, semaphore is common mechanism used in concurrent progamming, like [Readers–writers problem](https://en.wikipedia.org/wiki/Readers%E2%80%93writers_problem)
- **state1** includes counter, waiter and semahpore, which obtained by `func (wg *WaitGroup) state() (statep *uint64, semap *uint32)` 

	![wait_group_state_byte_representation](/images/wait_group.png)

