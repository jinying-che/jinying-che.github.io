---
title: "How lrzsz works"
date: 2026-08-07T15:21:49+0800
tags: ["linux"]
description: "How lrzsz, ZMODEM, terminal streams, PTYs, iTerm2 coprocesses, and nested SSH sessions work together"
---

`lrzsz` can transfer a file through a terminal session even when normal SSH forwarding is unavailable. That sounds surprising until the terminal is viewed as a bidirectional byte stream rather than just a keyboard and screen.

This post follows one concrete environment:

- A Mac runs iTerm2.
- The Mac can SSH to a jump server.
- The remote server is reachable only by starting another SSH client on the jump server.
- The jump server rejects the SSH `direct-tcpip` channel, so `ProxyJump`, `scp -J`, and direct SFTP cannot use it.
- iTerm2 has ZMODEM triggers that launch local `rz` or `sz` as a silent coprocess.

The goal is to explain what happens after running `sz /tmp/jinying.test` or `rz` on the final remote server, down to SSH channels, PTYs, ZMODEM frames, escaping, checksums, retransmission, and the strange bytes that sometimes leak into Bash.

## What lrzsz Provides

[`lrzsz`](https://www.ohse.de/uwe/software/software.html) is a Unix implementation of three file-transfer protocol families originally designed for serial and dial-up terminal links.

| Protocol | Main model                                          | Important limitation or improvement                             |
| -------- | --------------------------------------------------- | --------------------------------------------------------------- |
| XMODEM   | Fixed-size blocks, receiver acknowledges each block | Original form does not carry a filename and waits frequently    |
| YMODEM   | XMODEM-style blocks plus file metadata and batches  | Better file handling, but still block-and-ack oriented          |
| ZMODEM   | Framed, full-duplex streaming with file offsets     | Supports continuous transmission, recovery, batches, and resume |

The commands are named from the machine on which they run:

| Command   | Role           | In this example            |
| --------- | -------------- | -------------------------- |
| `sz file` | Send a file    | Remote server to local Mac |
| `rz`      | Receive a file | Local Mac to remote server |

The local side must run the opposite role. When remote `sz` sends, local `rz` receives. When remote `rz` receives, local `sz` sends. iTerm2 automation starts that local process.

## The Core Mental Model

A terminal session is an ordered stream of bytes in both directions. It has no built-in concepts of files, names, offsets, or checksums. Normally those bytes encode shell commands, text, and ANSI display controls. ZMODEM temporarily gives the same stream a file-transfer grammar.

![Terminal byte path from local iTerm2 through a jump server to remote lrzsz](/images/lrzsz-zmodem-terminal-path.drawio.svg)

The diagram contains two independent SSH connections:

1. Connection A runs from the Mac to the jump server.
2. The user runs `ssh remote-user@10.105.211.102` inside that interactive session.
3. That command starts an SSH client process on the jump server.
4. The jump-side SSH client opens connection B to the remote server.

The remote terminal's output therefore becomes the inner SSH client's output on the jump server. That output enters the jump PTY, crosses connection A, and arrives at iTerm2.

No `direct-tcpip` channel is involved. The second TCP connection is opened by the ordinary `ssh` process executing on the jump server, not by asking the jump server's `sshd` to forward a local connection.

### SSH Channel View

Interactive login uses the SSH connection protocol defined by [RFC 4254](https://datatracker.ietf.org/doc/html/rfc4254). A simplified setup is:

| SSH operation            | Protocol value                              | Purpose                                  |
| ------------------------ | ------------------------------------------- | ---------------------------------------- |
| Open interactive channel | `SSH_MSG_CHANNEL_OPEN`, type `session`      | Run a shell or command                   |
| Allocate terminal        | `SSH_MSG_CHANNEL_REQUEST`, type `pty-req`   | Attach a pseudo-terminal                 |
| Start shell              | `SSH_MSG_CHANNEL_REQUEST`, type `shell`     | Start the user's shell                   |
| Carry bytes              | `SSH_MSG_CHANNEL_DATA`                      | Transport terminal input and output      |
| Open forwarded socket    | `SSH_MSG_CHANNEL_OPEN`, type `direct-tcpip` | Used by local forwarding and `ProxyJump` |

The restricted jump server rejects the last operation. It has already accepted the `session` channel, however, and ZMODEM frames are simply bytes carried by `SSH_MSG_CHANNEL_DATA` inside that session.

### PTY View

A [pseudo-terminal](https://man7.org/linux/man-pages/man7/pty.7.html) is a master/slave character-device pair. The shell and `sz` or `rz` use the slave side, such as `/dev/pts/7`. `sshd` controls the master side.

| Write direction     | Result                                          |
| ------------------- | ----------------------------------------------- |
| PTY master to slave | Appears to the remote process as terminal input |
| PTY slave to master | Appears to `sshd` as terminal output            |

The PTY can apply terminal rules configured through [`termios`](https://man7.org/linux/man-pages/man3/cfmakeraw.3.html). Important examples include input echo, canonical line editing, newline conversion, signal characters such as `Ctrl-C`, and `Ctrl-S`/`Ctrl-Q` flow control. ZMODEM was designed for terminal links, so it includes escaping and terminal-mode handling, but every extra PTY or terminal parser remains another place where framing can be disturbed.

### Encryption Boundaries

The two links are encrypted independently. Connection A terminates at the jump server, and connection B starts there. ZMODEM bytes are decrypted into the jump PTY and then encrypted again by the inner SSH client.

The jump server normally does not store the file, but privileged software on that server could inspect the bytes passing through memory. This differs from `ProxyJump`, where a second SSH handshake can run end-to-end through a forwarding channel and the jump server sees only the inner encrypted stream.

## Download Example: Remote sz to Local rz

First establish the nested login:

```shell
# Local Mac
ssh jump-user@jump.example.com

# Jump server
ssh remote-user@10.105.211.102
```

On the final remote server, create and send a test file:

```shell
printf 'hello through ZMODEM\n' > /tmp/jinying.test
sz /tmp/jinying.test
```

![ZMODEM download sequence through nested SSH sessions](/images/lrzsz-zmodem-download.drawio.svg)

The transfer proceeds as follows:

1. Remote `sz` writes a ZMODEM startup header to its terminal output.
2. The bytes cross the remote PTY, connection B, the jump PTY, and connection A.
3. iTerm2 matches the startup pattern and starts the local receive script as a silent coprocess.
4. The script runs local `rz`, which replies with its capabilities.
5. Remote `sz` sends the filename and metadata in a `ZFILE` frame.
6. Local `rz` returns `ZRPOS` with offset zero, or a nonzero resume offset.
7. `sz` streams `ZDATA` subpackets. `rz` validates their CRCs and writes verified bytes.
8. The peers exchange `ZEOF`, `ZRINIT`, `ZFIN`, and the final `OO` bytes.

The iTerm2 receive trigger often watches for a human-visible prefix resembling:

```text
**B00000000000000
```

That text is not the entire header. It is the printable portion around ZMODEM padding, a `ZDLE` control byte, the `ZHEX` indicator, the `ZRQINIT` frame type, header bytes, and a checksum.

### What the iTerm2 Coprocess Does

The [iTerm2 coprocess contract](https://iterm2.com/documentation/2.1/documentation-coprocesses.html) is exactly what ZMODEM integration needs:

- Terminal output is copied byte-for-byte to the coprocess's standard input.
- Coprocess standard output is injected into the terminal as if typed at the keyboard.

During normal shell use, iTerm2 renders incoming bytes and sends keyboard bytes to SSH. During the transfer, remote ZMODEM output is consumed by local `rz`, while replies from local `rz` are injected into the existing SSH terminal input.

Even a download is bidirectional: the receiver must send capabilities, offsets, acknowledgements, recovery requests, and finish frames back to the sender.

## Upload Example: Local sz to Remote rz

On the final remote server, move to the destination directory and start the receiver:

```shell
cd /tmp
rz
```

![ZMODEM upload sequence through nested SSH sessions](/images/lrzsz-zmodem-upload.drawio.svg)

Remote `rz` prints its waiting message and a `ZRINIT` header. The iTerm2 upload trigger detects that output, opens the local file picker, and launches local `sz` with the selected file. Local `sz` sends `ZFILE`; remote `rz` chooses the starting position with `ZRPOS`, validates incoming data, and writes the destination file.

For either direction, verify important files independently:

```shell
# Linux source or destination
sha256sum /tmp/jinying.test

# macOS source or destination
shasum -a 256 ~/Desktop/jinying.test
```

ZMODEM carries individual files and batches, not a directory abstraction. Archive a directory first:

```shell
tar -czf logs.tar.gz logs/
sz logs.tar.gz
```

## ZMODEM Protocol Sequence

ZMODEM is a stateful conversation between a sender and receiver. It is not an IETF protocol and has no RFC; the closest primary description is Chuck Forsberg's [ZMODEM Inter Application File Transfer Protocol](https://techheap.packetizer.com/communications/modems/zmodem8.html). The [`lrzsz` source](https://sources.debian.org/src/lrzsz/) is also essential because terminal integrations commonly implement its behavior.

![ZMODEM negotiation, streaming, recovery, and finish sequence](/images/lrzsz-zmodem-protocol.drawio.svg)

The key frame types are defined in [`zmodem.h`](https://sources.debian.org/src/zssh/1.5a-1/lrzsz-0.12.20/src/zmodem.h):

| Frame     | Numeric type | Meaning                                                  |
| --------- | -----------: | -------------------------------------------------------- |
| `ZRQINIT` |            0 | Sender asks the receiver to initialize                   |
| `ZRINIT`  |            1 | Receiver reports readiness and capabilities              |
| `ZSINIT`  |            2 | Optional sender initialization and attention information |
| `ZACK`    |            3 | Acknowledgement where requested                          |
| `ZFILE`   |            4 | File metadata follows in a data subpacket                |
| `ZSKIP`   |            5 | Receiver declines the current file                       |
| `ZFIN`    |            8 | Finish the ZMODEM session                                |
| `ZRPOS`   |            9 | Start or restart data at a byte offset                   |
| `ZDATA`   |           10 | File data subpackets follow                              |
| `ZEOF`    |           11 | Sender reached the stated final offset                   |
| `ZCRC`    |           13 | Request or report a file CRC                             |
| `ZCAN`    |           16 | Cancel the session                                       |

### Capability Negotiation

`ZRINIT` uses header flag bytes to advertise receiver behavior. Common flags include:

| Flag      | Meaning                                      |
| --------- | -------------------------------------------- |
| `CANFDX`  | Receiver supports full-duplex operation      |
| `CANOVIO` | Receiver can overlap disk I/O with reception |
| `CANFC32` | Receiver supports 32-bit frame checks        |
| `ESCCTL`  | Sender should escape control characters      |

The sender uses these capabilities to select CRC size, escaping, and streaming behavior. Optional `ZSINIT` can communicate an attention sequence and additional escaping requirements before file metadata begins.

### File Metadata and Resume

`ZFILE` is followed by a data subpacket. Its first NUL-terminated field is the filename; another ASCII field can carry size, modification time, mode, and related attributes.

The receiver answers with `ZRPOS`. Its four-byte header field is interpreted as a file offset:

- Offset `0` starts a new file.
- A nonzero offset resumes from an existing verified prefix.
- After a CRC or framing error, the receiver can send a new `ZRPOS` for the last trustworthy position.

The sender seeks to that position and emits another `ZDATA` header. Resume is therefore part of the protocol, although a particular terminal script may choose rename, overwrite, or no-resume behavior.

### Streaming Instead of ACK-per-Block

XMODEM-style protocols commonly stop after each block and wait for an acknowledgement. ZMODEM can transmit a sequence of data subpackets continuously. The receiver interrupts only when an acknowledgement is requested, flow control requires it, or recovery is necessary.

This is why ZMODEM performs well on a link with noticeable round-trip latency: useful bytes remain in flight instead of waiting after every small block.

## Header and Subpacket Encoding

The low-level implementation is in [`zm.c`](https://sources.debian.org/src/lrzsz/0.12.21rc-0.2/src/zm.c/). ZMODEM supports three header encodings.

![ZMODEM hex headers, binary headers, data subpackets, and position bytes](/images/lrzsz-zmodem-framing.drawio.svg)

### Header Prefixes

The important framing constants are:

| Symbol   |  Value | Purpose                                  |
| -------- | -----: | ---------------------------------------- |
| `ZPAD`   |  `'*'` | Marks the beginning of a header          |
| `ZDLE`   | `0x18` | ZMODEM data-link escape character        |
| `ZBIN`   |  `'A'` | Binary header with CRC-16                |
| `ZHEX`   |  `'B'` | Printable hexadecimal header with CRC-16 |
| `ZBIN32` |  `'C'` | Binary header with CRC-32                |

A hex header begins with two padding bytes because it is intended to be easy to recognize on a terminal path. Its conceptual prefix is:

```text
ZPAD ZPAD ZDLE ZHEX
  *    *   0x18   B
```

The frame type, four header bytes, and CRC-16 are then encoded as printable hexadecimal characters. `lrzsz` appends carriage-return and line-ending bytes, and usually an `XON`, after a hex header.

Binary headers are denser. They encode the frame type, the four-byte header field, and CRC directly, while escaping bytes that could be interpreted by the terminal path.

### Four-Byte Header Field

Every ZMODEM header carries four bytes named `ZF0` through `ZF3`. Their interpretation depends on the frame. For position-bearing frames they are also named `ZP0` through `ZP3`.

`lrzsz` stores positions little-endian:

```text
ZP0 = offset bits 0..7
ZP1 = offset bits 8..15
ZP2 = offset bits 16..23
ZP3 = offset bits 24..31
```

The same mechanism carries the restart position in `ZRPOS`, starting position in `ZDATA`, and final byte count in `ZEOF`.

### Data Subpacket Terminators

Each data subpacket contains escaped payload bytes, a `ZDLE`, a frame-end marker, and CRC-16 or CRC-32. The marker controls whether streaming continues and whether an acknowledgement is expected.

| Marker  | Encoded character | Meaning                                       |
| ------- | ----------------- | --------------------------------------------- |
| `ZCRCE` | `'h'`             | End this frame; a new header follows          |
| `ZCRCG` | `'i'`             | Continue streaming without waiting for an ACK |
| `ZCRCQ` | `'j'`             | Continue, but request a `ZACK`                |
| `ZCRCW` | `'k'`             | End the frame and wait for a `ZACK`           |

### CRC Is Integrity, Not Security

CRC-16 or CRC-32 detects accidental corruption of headers and subpackets. It does not authenticate the sender and does not protect against deliberate modification. In this environment, SSH supplies encryption and cryptographic transport integrity; ZMODEM's CRC still detects damage introduced at the application or terminal-framing layer.

### ZDLE Escaping

A terminal may treat some bytes as actions rather than data. Examples include `Ctrl-C`, `Ctrl-S`, `Ctrl-Q`, carriage return, and `ZDLE` itself. ZMODEM uses link escaping so these values can cross a less-than-transparent path.

Conceptually, a sensitive byte is represented by `ZDLE` followed by a transformed byte. The receiver recognizes the pair and reconstructs the original value. This adds overhead but prevents many control bytes from being consumed by terminal flow control or command processing.

## Why tmux Can Break the Transfer

SSH channel data is binary-safe, but an interactive path also contains PTYs and terminal-aware programs. `tmux` adds another virtual terminal, parser, screen model, and PTY between remote `sz` or `rz` and iTerm2.

![Clean ZMODEM terminal path compared with a tmux failure path](/images/lrzsz-zmodem-tmux-failure.drawio.svg)

ZMODEM can sometimes work through `tmux`, but an iTerm2 trigger-based setup is fragile there. Output can be buffered, interpreted, delayed, or exposed to the screen in a way that changes trigger timing. The safest practice is to detach and run the transfer from the ordinary remote shell:

```text
Ctrl-b d
```

Then run `sz` or `rz` outside `tmux`.

### Explaining Leaked Bytes

Consider this output:

```text
sz jinying.test
�*B00000000000000
-bash: $'\212': command not found
```

The visible `*B000...` belongs to a ZMODEM hex header. The non-printable byte was rendered as a replacement character because it was not normal terminal text.

The octal `212` is especially revealing. The `lrzsz` hex-header writer appends octal `0212` after carriage return. If trigger startup or cleanup leaves that byte in the interactive input stream, Bash can receive it after the transfer and try to parse it as a command.

This explains why the file may still be downloaded successfully while Bash prints an error afterward: the file data and its CRC checks completed, but trailing protocol or line-ending bytes escaped the coprocess boundary.

Other common symptoms are:

| Symptom                                         | Likely layer                                             |
| ----------------------------------------------- | -------------------------------------------------------- |
| `rz waiting to receive` remains on screen       | Upload trigger did not start local `sz`                  |
| `Cancelled transfer`                            | File picker was cancelled or the local coprocess exited  |
| `**B000...` displayed as text                   | Download trigger missed or started late                  |
| Works outside tmux but hangs inside             | Extra terminal parser or PTY disturbed framing or timing |
| File succeeds but Bash reports a binary command | Trailing bytes leaked after protocol completion          |

## When lrzsz Is the Right Tool

| Method         | Protocol path                                      | Fit for this restricted jump-server case                               |
| -------------- | -------------------------------------------------- | ---------------------------------------------------------------------- |
| `lrzsz`        | ZMODEM inside existing terminal `session` channels | Convenient for occasional manual files                                 |
| SFTP           | SFTP subsystem inside SSH                          | Direct local-to-remote use needs an allowed route or forwarding        |
| Modern SCP     | Usually SFTP inside SSH                            | Same jump-routing constraint                                           |
| rsync          | Rsync protocol over an SSH command channel         | Excellent for large trees, but nested setup or staging is more complex |
| Two-stage copy | Local to jump, then jump to remote                 | Reliable but stores an intermediate copy                               |
| Object storage | HTTP/TLS API                                       | Best for repeatable team workflows when both sides have service access |

`lrzsz` is reasonable when all of the following are true:

- An interactive terminal path already exists.
- SSH forwarding is unavailable.
- The terminal emulator has working ZMODEM integration.
- The transfer is manual and involves a small number of files.
- The command can run outside `tmux`, `screen`, and `mosh`.

It is a poor default for automation, very large directory trees, reproducible deployment workflows, or untrusted terminal endpoints. ZMODEM itself provides no encryption or peer authentication, and automatic terminal triggers should launch only fixed, reviewed local scripts with controlled destination directories.

## References

- [lrzsz upstream project](https://www.ohse.de/uwe/software/software.html)
- [Debian lrzsz source package](https://sources.debian.org/src/lrzsz/)
- [ZMODEM constants in zmodem.h](https://sources.debian.org/src/zssh/1.5a-1/lrzsz-0.12.20/src/zmodem.h)
- [lrzsz low-level protocol implementation in zm.c](https://sources.debian.org/src/lrzsz/0.12.21rc-0.2/src/zm.c/)
- [The ZMODEM Inter Application File Transfer Protocol](https://techheap.packetizer.com/communications/modems/zmodem8.html)
- [Tera Term ZMODEM implementation notes](https://github.com/TeraTermProject/teraterm/wiki/ZMODEM-Protocol)
- [RFC 4254: The Secure Shell Connection Protocol](https://datatracker.ietf.org/doc/html/rfc4254)
- [Linux pty(7)](https://man7.org/linux/man-pages/man7/pty.7.html)
- [Linux termios(3)](https://man7.org/linux/man-pages/man3/cfmakeraw.3.html)
- [iTerm2 coprocess documentation](https://iterm2.com/documentation/2.1/documentation-coprocesses.html)
