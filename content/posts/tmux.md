---
title: "Tmux Cheat Sheet"
tags: ["tmux"]
description: "The basic usage of [Tmux](https://github.com/tmux/tmux/wiki), personally, I think Tmux makes more sense in server side than local."
date: 2021-07-10T11:18:14+08:00
---

### Session
- new session: `tmux new -s name`
- show session: `tmux ls`
- attach session with name: `tmux a -t name`
- detach from session: `ctrl+b` then `d`

### Panes
- split pane horizontally: `ctrl+b` then `%`
- split pane vertically: `ctrl+b` then `"`
- cloes current pane: `ctrl+b` then `x`
- swap panes: `ctrl+b` then `o` 
- swan and rotate panes: `ctrl+b` then `ctrl+o`

### Window
- Create current window: `ctrl+b` then `c`
- Close current window: `ctrl+b` then `&`
- Rename current window: `ctrl+b` then `,`
- Next window: `ctrl+b` then `p`
- Previous window: `ctrl+b` then `n`
- Lisgt all windows: `ctrl+b` then `w`

### View in tmux
`ctrl+b` then `[`

### Plugin
- [tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) Restore tmux environment after system restart.

> The better way to use tmux is to customize in your way, feel free to refer my [tmux config](https://github.com/jinying-che/config/blob/master/.tmux.conf)

---
## Reference
- https://tmuxcheatsheet.com/
