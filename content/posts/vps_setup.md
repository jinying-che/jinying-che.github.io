---
title: "vps setup"
date: "2024-11-22T08:00:37+08:00"
tags: ["setup", "linux"]
description: "a setup list for vps linux server"
---

Welcome to play the personal linux server, here's the setup list that all you need.

## Admin
1. systemd 
2. ifconfig
    - `sudo apt install net-tools`


## Dev
- git: `sudo apt install git`
- zsh: `sudo apt install zsh`
    - install oh-my-zsh: `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"`
- on my zsh: `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"`
  - plugins:
    - git
    - fzf
    - autojump: `sudo apt install autojump`
    - 
- gcc
- go
- make
    - `sudo apt install make`

## Reference
- https://github.com/ohmyzsh/ohmyzsh
