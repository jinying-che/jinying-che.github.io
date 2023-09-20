---
title: "Mac Setup"
date: "2023-07-01T23:26:50+08:00"
tags: ["setup", "mac"]
description: "the check list for mac setup"
---

## 1. Mac Setting
- [Turn on three finger drag for your Mac trackpad](https://support.apple.com/en-sg/HT204609)
- Increase the cursor moving speed: `System Preferences` -> `Keyboard` -> `Increase Key Repeat Rate`
- switch the `ctrl` and `caps lock` key: https://support.apple.com/en-sg/guide/mac-help/mchlp1011/mac

## 2. Shell
- Install [iterm2](https://iterm2.com/)
  - theme: [one dark](https://github.com/one-dark/iterm-one-dark-theme)
  - font: [source code pro](https://github.com/adobe-fonts/source-code-pro) 
- Install [Homebrew](https://brew.sh/)
- Install ZSH: `brew install zsh`
- Install [oh-my-zsh](https://ohmyz.sh/#install)
- [Generating a new SSH key and adding it to the ssh-agent](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- After **ssh** setup and add to the https://github.com/, it's able to `git clone` resource for iterm2 now:
  - theme: [github-nvim-theme](https://github.com/projekt0n/github-nvim-theme)
  - font: [source code pro](https://github.com/adobe-fonts/source-code-pro)  
    - To install new fonts on mac: Open `Font Book` App -> Open File -> Add Fonts To Current User -> Choose the downlaoded font files
- Init [.gitconfig](https://github.com/jinying-che/config)

### 2.1 Zsh 
- configuration ([.zshrc](https://github.com/jinying-che/config/blob/master/.zshrc))
- setting:
  - move the cursor by words:
  ```
  1. Go to iTerm2 (in the menu bar) > Settings... > Profiles > Keys (not Preferences... > Keys)
  2. On current versions (3.14+) you then switch to the Key Mappings tab
  3. Press Presets... dropdown button.
  4. Select Natural Text Editing
  ```
- plugins:
  - [autojump](https://github.com/wting/autojump): `brew install autojump`
  - [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions): `git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions`
  - [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting): `git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting`
  - [fzf](https://github.com/junegunn/fzf#using-homebrew)
    - `brew install fzf`
    - `$(brew --prefix)/opt/fzf/install`

## 3. vim 
- vim ([.vimrc](https://github.com/jinying-che/config/blob/master/.vimrc)):
  - install nvim: `brew install neovim`
  - init nvim: https://neovim.io/doc/user/nvim.html#nvim-from-vim
  - install [vim-plug](https://github.com/junegunn/vim-plug), copy `.vimrc` and `:PlugInstall` to install plugins
  - install [coc.nvim](https://github.com/neoclide/coc.nvim) (`brew install node` first)

### 3.1 [coc.nvim](https://github.com/neoclide/coc.nvim/)
I would say coc.nvim is VS Code in neo vim, as well as the function is also expanded by plugins. Here's the basic plugins we used in daily development.

- [coc-lists](https://github.com/neoclide/coc-lists)
- [coc-go](https://github.com/josa42/coc-go) (for golang developer)
- [coc-pyright](https://github.com/fannheyward/coc-pyright) (for python developer)

## tmux
- `brew install tmux`
- install tmux plugin manager: https://github.com/tmux-plugins/tpm
- copy [config](https://github.com/jinying-che/config/blob/master/.tmux.conf) to `~/.tmux.conf`
- `tmux source ~/.tmux.conf` (type this in terminal if tmux is already running)
- theme: https://github.com/catppuccin/tmux 
    - intall by tpm (included in the config above)
    - patch font via https://github.com/catppuccin/tmux#installation (for font installation refer to shell section 2)

## 4. Tool
- [fd](https://github.com/sharkdp/fd) is a simple, fast and user-friendly alternative to `find`: `brew install fd`
- Personal Script: `git clone https://github.com/jinying-che/Geript`, add into **system path** in `.zshrc`
- [Hugo](https://github.com/gohugoio/hugo) is one of the most popular open-source static site generators.: `brew install hugo`
- GitHub Readme Instant Preview: `brew install grip`
- [tlrd](https://github.com/tldr-pages/tldr): collection of community-maintained help pages for command-line tools, that aims to be a simpler, more approachable complement to traditional man pages.

## 5. Development
### 5.1 golang 
- Install `golang`: https://go.dev/doc/install

### 5.2 python
- Install python: `brew install python3`
- Install ipython: `pip install "ipython[all]"`


