---
title: "Go Basic"
date: 2020-09-27T19:47:01+08:00
draft: true
---

# Go Basic
> the basic of go
## Channel
#### 基本性质
- 在go的运行时环境，对**同一个通道**，发送操作是互斥的（即同一时刻，只有一个发送操作会执行），同理，接受操作也是互斥的
- 元素进入通道，分为两步，为一个原子操作：
  - 对元素进行复制
  - 将副本放入通道内部
- 元素从通道取出取出，分为三步，为一个原子操作：
  - 对元素进行复制
  - 赋值给接收方
  - 在通道中删除

#### 缓冲与非缓冲

- 非缓冲通道，send和receive操作会彼此阻塞，直到彼此准备好数据，比如：

  ```
  func main(){
    c := make(chan int)
    //当前线程send数据后，会挂起，直至channel中的数据被receive后，才继续执行
    c <- 1 
    //下面这句永远不会执行，导致deadlock
    fmt.Println(<- c)
  }
  ```
  

#### Channel Close

> - Only the sender should close a channel, never the receiver. Sending on a closed channel will cause a panic. (**don't close a channel from the receiver side and don't close a channel if the channel has multiple concurrent senders**. In other words, we should only close a channel in a sender goroutine if the sender is the only sender of the channel.)
> - Channels aren't like files; you don't usually need to close them. Closing is only necessary when the receiver must be told there are no more values coming, such as to terminate a `range` loop.
> - **don't close (or send values to) closed channels**.

##### what I think:

- send or close the channel which has been closed, will cause a panic

- Close the **channel** or **channel buffer**, just send a close **event** to the goroutines that consuming the channle(s)  , **do not stop the goroutines at  all**, the goroutines are still running, we can deal with the close event by this way:

  ```go
  if item, ok := <- channel; !ok {
    //stop goroutine
  }
  ```

- The value sented before the close event in channel will be received, when they are finished, the close event is in effect (receive zero value / ok is false)



## Method

method should be define in the same package as the stuct defined

### Method vs Function

```go
func (v Vertex) Abs() float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y)
}

func AbsFunc(v Vertex) float64 {
	return math.Sqrt(v.X*v.X + v.Y*v.Y)
}
```

Functions that take a value argument must take a value of that specific type:

```go
var v Vertex
fmt.Println(AbsFunc(v))  // OK
fmt.Println(AbsFunc(&v)) // Compile error!
```

while methods with value receivers take either a value or a pointer as the receiver when they are called:

```go
var v Vertex
fmt.Println(v.Abs()) // OK
p := &v
fmt.Println(p.Abs()) // OK
```

### Method and Package

When you create a method in your code the receiver and receiver type must present in the same package.



## Build

- Mac to Linux : `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build xxx.go`



## String

> To summarize, strings can contain arbitrary bytes, but when constructed from string literals, those bytes are (almost always) UTF-8.
>
> - Go source code is always UTF-8.
> - A string holds arbitrary bytes.
> - A string literal, absent byte-level escapes, always holds valid UTF-8 sequences.
> - Those sequences represent Unicode code points, called runes.
> - No guarantee is made in Go that characters in strings are normalized.

> In Go, a string is in effect a read-only slice of bytes.

```go
//Go 1.12.9 string.go
package runtime

type stringStruct struct {
	str unsafe.Pointer
	len int
}
```



## Goroutine Scheduler

> M, P, G

### P

> Go 语言中有两个运行队列，其中一个是处理器本地的运行队列，另一个是调度器持有的全局运行队列，只有在本地运行队列没有剩余空间时才会使用全局队列存储 Goroutine。
## Struct

### init

- If the struct is nested, should be initialized step by step manually 

## New && Make

> - The basic distinction is that `new(T)` returns a `*T`, a pointer that Go programs can dereference implicitly (the black pointers in the diagrams), while `make(T, `*args*`)` returns an ordinary `T`, not a pointer.
>
> - **new()** returned is a pointer to a newly allocated zero value of that type,  the **make** built-in function allocates and initializes an object of type slice, map, or chan (only).
>

## Slice

### underlying data structure

```go
//Go 1.12.9 slice.go

type slice struct {
   array unsafe.Pointer
   len   int
   cap   int
}
```

### pointer to slice

- `slice []byte`: If pass the slice to function, and change the slice index in function, like `slice = slice[0: len(slice) - 1]`, then exit the function, cannot change the **slice header**, so the slice is not changed yet.
- `slice *[]byte`: If pass the pointer that point to the slice, if change index, then will change the **slice header**, the slice is changed finally. 
- By the way, if change the content of slice, will change the uderlying array, so both is ok.

> It's important to understand that even though a slice contains a pointer, it is itself a value. Under the covers, it is a struct value holding a pointer and a length. It is *not* a pointer to a struct.

## Context



## Interface

- `interface{}`: An empty interface may hold values of any type, Empty interfaces are used by code that handles values of unknown type.

### Pointer to Interface

**It make no sense**, when we make a struct to implement a interface's method, we want to use this struct in which the interface is used, It's object-oriented. 

If we define a function which parameter is interface, we can use the struct that implemented the interface, but if which parametrer is pointer to interface, it can not work, make no sense, just a poniter to interface, useless.



## Pointers

### Receivers: Pointers vs Values

> The rule about pointers vs. values for receivers is that value methods can be invoked on pointers and values, but pointer methods can only be invoked on pointers.



##Function

- Function is the first-class and it's the Reference Type which means whenever passing the Function, we pass the the pointer of the Function.



## Modules

### Non-public modules

> https://golang.org/cmd/go/#hdr-Module_configuration_for_non_public_modules

## Q && A

- Value or Pointer ? 
- Pointer to Interface ? value interface

