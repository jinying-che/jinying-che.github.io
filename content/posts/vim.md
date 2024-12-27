+++
title = "Vim Cheat Sheet"
date = 2021-07-10T11:20:07+08:00
description = "Vim cheat sheet, basically it's able to use `:help keyword` to search docs"
tags = [
	"vim", "cheatsheet"
]
+++

## Usage

### Basic
- delete inside parentheses (which can be replaced with any symbol)
  - `di(`
  - `di"` 
  - `di'`
  - ...

### Split
- Horizontal: `ctrl + w + s`
- Vertical: `ctrl + w + v`

### Replace a word with yanked text
```
yiw               Yank inner word (copy word under cursor, say "first").
                  Move the cursor to another word (say "second").
ciw Ctrl-R 0 Esc  Change "second", replacing it with "first". (Ctrl-R: paste `0` register in insert mode)
                  Move the cursor to another word (say "third").
.                 Repeat the operation (change word and replace it with "first").
                  Move the cursor to another word and press . to repeat the change.
      
ref: https://vim.fandom.com/wiki/Replace_a_word_with_yanked_text
```

## Plugin
1. lsp: https://github.com/neoclide/coc.nvim
2. fuzzy finder: https://github.com/junegunn/fzf.vim 
3. status tabline: https://github.com/vim-airline/vim-airline
4. git: https://github.com/tpope/vim-fugitive
5. theme: https://github.com/projekt0n/github-nvim-theme
6. outline: https://github.com/preservim/tagbar
7. tree: https://github.com/preservim/nerdtree
8. syntax: https://github.com/nvim-treesitter/nvim-treesitter


