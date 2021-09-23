---
title: "Tmux Cheat Sheet"
date: 2021-07-10T11:18:14+08:00
---

The basic usage of [Tmux](https://github.com/tmux/tmux/wiki), personally, I think Tmux makes more sense in server side than local.

### Session
- new session
> `tmux new -s name`
- show session
> `tmux ls`
- attach session with name
> `tmux a -t name`
- detach from session
> **ctrl+b** then  **d**


### Panes
- split pane horizontally
> **ctrl+b** then **%**
- split pane vertically
> **ctrl+b** then **"**
- cloes current pane
> **ctrl+b** then **x**


### Window
- Close current window
> **ctrl+b** then **&**
- Rename current window
> **ctrl+b** then **,**


### View in tmux
> **ctrl+b** then **[**

---
Reference
- https://tmuxcheatsheet.com/
