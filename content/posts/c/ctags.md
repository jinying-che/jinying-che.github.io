---
title: "Setup Universal Ctags for Mac"
description: "A brief tutorial for setting up ctags in mac"
date: 2021-01-23T15:16:29+08:00
---
At the Beginning of this year, I'm going to start reading *Computer System A Programmer\'s Perspective*, this whole book introduces the different aspects of computer system basing on C language, and there's also plenty of C demos provided in the [web](http://csapp.cs.cmu.edu/3e/code.html), to navigate the code, I try to use **ctags**.

### What is Universal Ctags?

> [Universal Ctags](https://ctags.io/) (abbreviated as u-ctags) is a maintained implementation of ctags. ctags generates an index (or tag) file of language objects found in source files for programming languages. This index makes it easy for text editors and other tools to locate the indexed items.

### Install in Mac
```shell
brew tap universal-ctags/universal-ctags
brew install --HEAD universal-ctags
```
> brew tap
> A [tap](https://docs.brew.sh/Taps) is Homebrew-speak for a Git repository containing extra formulae.

### Configure .vimrc
```shell
#search the .tags in the current directory, will keep searching the upper directory if not found
set tags=./.tags;,.tags
```

### Setup alias for ctags
Because there is already a **ctags** command in Mac, which is **/usr/bin/ctags**, we need to create an alias of `ctags` for overwriting.

Add this in **.zshrc** (suppose to use **zsh**)
- `alias ctags="/usr/local/bin/ctags"` 
	> **`which ctags`** to verify
### Generate tag recursively
In the root of the project:

- `ctags -f .tags -R .`	
	- **-f .tags** indicates that the output file is **.tags**
	- **-R** means **\-\-recurse**
