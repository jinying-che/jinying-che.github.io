---
title: "Mac Setup"
date: "2023-07-01T23:26:50+08:00"
tags: ["setup", "mac"]
description: "the check list for mac setup"
---

Please kindly follow the instructions below in order.

- [Turn on three finger drag for your Mac trackpad](https://support.apple.com/en-sg/HT204609)
- Increase the cursor moving speed: `System Preferences` -> `Keyboard` -> `Increase Key Repeat Rate`
- switch the `ctrl` and `caps lock` key: https://support.apple.com/en-sg/guide/mac-help/mchlp1011/mac
- Install [iterm2](https://iterm2.com/)
  - theme: [one dark](https://github.com/one-dark/iterm-one-dark-theme)
  - font: [source code pro](https://github.com/adobe-fonts/source-code-pro) 
- Install [Homebrew](https://brew.sh/)
- Install ZSH: `brew install zsh`
- Install [oh-my-zsh](https://ohmyz.sh/#install)
- [Generating a new SSH key and adding it to the ssh-agent](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
- After **ssh** setup and add to the https://github.com/, it's able to `git clone` resource for iterm2 now:
  - theme: [one dark](https://github.com/one-dark/iterm-one-dark-theme)
  - font: [source code pro](https://github.com/adobe-fonts/source-code-pro)  
    - To install new fonts on mac: Open `Font Book` App -> Open File -> Add Fonts To Current User -> Choose the downlaoded font files
- vim ([.vimrc](https://github.com/jinying-che/config/blob/master/.vimrc)):
  - install nvim: `brew install neovim`
  - init nvim: https://neovim.io/doc/user/nvim.html#nvim-from-vim
  - install [vim-plug](https://github.com/junegunn/vim-plug), copy `.vimrc` and `:PlugInstall` to install plugins
  - install [coc.nvim](https://github.com/neoclide/coc.nvim) (`brew install node` first)
- Install golang: https://go.dev/doc/install
- zsh ([.zshrc](https://github.com/jinying-che/config/blob/master/.zshrc))
  - plugins:
    - [autojump](https://github.com/wting/autojump): `brew install autojump`
    - [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions): `git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions`
    - [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting): `git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting`
    - [fzf](https://github.com/junegunn/fzf#using-homebrew)
      - `brew install fzf`
      - `$(brew --prefix)/opt/fzf/install`
- Install [fd](https://github.com/sharkdp/fd): `brew install fd`
- Personal Script: `git clone https://github.com/jinying-che/Geript`, add into **system path** in `.zshrc`
- Install [Hugo](https://github.com/gohugoio/hugo): `brew install hugo`
- Init [.gitconfig](https://github.com/jinying-che/config)
