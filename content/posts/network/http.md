---
title: "HTTP"
date: "2018-10-10T11:19:45+08:00"
tags: ["network", "protocol", "http"]
description: "HTTP History"
---

> HTTP位于网络的应用层，使用TCP/IP协议进行传输

- TCP连接
  - HTTP/1.0：通过非标准字段`Connection: keep-alive`保持TCP连接
  - HTTP/1.1：允许TCP复用，但所有数据通信都是按次序的，请求要一个一个处理
  - HTTP/2：

## HTTP/0.9

- 客户端请求，服务器回复完毕，TCP连接即关闭
- 只有一个命令：`GET`
- 服务器只能回应HTML格式的字符串

## HTTP/1.0

- 加入`POST`、`HEAD`命令
- 协议分为头部和数据部，头部字段如：`Content-Type`、`Content-Encoding`等
- 为了保持TCP的复用，引入头部字段：`Connection: keep-alive`

## HTTP/1.1

- TCP默认为持久连接，由客户端和服务端主动关闭

- 引入管道机制，向TCP连接发送多个请求（而不用等待上一个请求处理之后，再发送）

  - 服务端可以区分多个请求的基础：`Content-Length`字段，即知道每个请求的长度
  -  在1.0版中，`Content-Length`字段不是必需的，因为浏览器发现服务器关闭了TCP连接，就表明收到的数据包已经全了。

- 引入流模式

  > 对于一些很耗时的动态操作来说，这意味着，服务器要等到所有操作完成，才能发送数据，显然这样的效率不高。更好的处理方法是，产生一块数据，就发送一块，采用"流模式"（stream）取代"缓存模式"（buffer）。
  >
  > 因此，1.1版规定可以不使用`Content-Length`字段，而使用["分块传输编码"](https://zh.wikipedia.org/wiki/%E5%88%86%E5%9D%97%E4%BC%A0%E8%BE%93%E7%BC%96%E7%A0%81)（chunked transfer encoding）。只要请求或回应的头信息有`Transfer-Encoding`字段，就表明回应将由数量未定的数据块组成。
  >
  > [《HTTP 协议入门》 阮一峰](http://www.ruanyifeng.com/blog/2016/08/http.html)

  >当HTTP流水线启动时，后续请求都可以不用等待第一个请求的成功回应就被发送。然而HTTP流水线已被证明很难在现有的网络中实现，因为现有网络中有很多老旧的软件与现代版本的软件共存。因此，HTTP流水线已被在有多请求下表现得更稳健的HTTP/2的帧所取代。
  >
  >[《HTTP概述》 MDN](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Overview)

- 服务器只能按顺序处理请求，如果前面请求处理的慢，后面的需要排队，即["队头堵塞"](https://zh.wikipedia.org/wiki/%E9%98%9F%E5%A4%B4%E9%98%BB%E5%A1%9E)（Head-of-line blocking）。

## HTTP/2.0

> 2009年，谷歌公开了自行研发的 SPDY 协议，主要解决 HTTP/1.1 效率不高的问题。
>
> 这个协议在Chrome浏览器上证明可行以后，就被当作 HTTP/2 的基础，主要特性都在 HTTP/2 之中得到继承。

- 头部和数据部都是二进制，统称为“帧”
- 全双工模式（双向、实时通信），客户端和服务端可同时发送多个请求和回应（解决阻塞问题）
  - 实现的基础：由于HTTP/2不按照顺序发送，就需要对每个请求或回应作区分，即每个请求或回应的所有数据包都对应唯一ID
  - 客户端和服务器都可以发送信号（`RST_STREAM`帧），取消这个数据流
- 头信息压缩
- 服务器未经允许，主动推送数据到客户端

> Reference:
>
> - [《HTTP 协议入门》 阮一峰](http://www.ruanyifeng.com/blog/2016/08/http.html)
> - [《HTTP概述》 MDN](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Overview)
