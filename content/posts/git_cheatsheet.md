---
title: "Git Cheatsheet"
date: "2023-01-31T16:14:39+08:00"
tags: ["git", "cheatsheet"]
description: "git best practices"
---

# git cheatsheet

#### 1. [How can I see the changes in a Git commit](https://stackoverflow.com/questions/17563726/how-can-i-see-the-changes-in-a-git-commit)?
`git diff COMMIT~ COMMIT` or `git show COMMIT`
    
#### 2. How to include config directives from another source? 
setup a `.gitconfig`, `.gitconfig-garena`, and `.gitconfig-github` at $HOME as follows, all the projects under the folder will be configured recursively:
```toml
# .gitconfig
[includeIf "gitdir:~/workspace/garena.com/"]
	path = ~/.gitconfig-garena

[includeIf "gitdir:~/workspace/github.com/"]
	path = ~/.gitconfig-github

# .gitconfig-garena
[user]
	name = Jinying Che
	email = jinying.che@shopee.com
	
# .gitconfig-github
[user]
	name = Jinying Che
	email = chejinying@me.com 
```

### git branch

1. 查看分支状态：
   - 本地与远程： `git branch -va`
   - 查看本地分支：`git branch`
   - 查看远程分支：`git branch -r`
2. 删除分支：
   - 删除本地分支：`git branch -d [branch-name]`
   - 删除远程分支：`git branch -dr [origin/branch-name]`

### git status

用法：列出未追踪的文件、本地库与工作区之间的差异，追踪`git add`、`git commit`进展

### 处理工作区与本地库的差异

> git checkout 不仅仅有切换分支的功能

工作区 —> 本地库：`git checkout [filename]` 

本地库 —> 工作区：`git add [filename]`  `git commit [filename] -m "commet"`

### git rm

- git rm file 
- git rm —cache file

#####不删除本地，删除远程（即删除本地缓存区，提交到远程）
```sh
 git rm —cache -r directory
 git commit -m "del"
 git pushf
 ```

### git revert

>  这条命令用于分布式代码管理的回滚

主要区别于`git reset`，`git reset <commit>`，会将该版本之前的版本全部抹掉。这样在多人合作的模式下，如果我们想回滚远程主分支中的代码，会抹掉其他人的提交，相当危险。

`git revert <commit>`：撤销某个版本的提交，即只撤销这个版本的提交(这个版本提交了什么就撤销什么)，并生成一个新的版本，原版本依然保留。这个新版本只提交到了本地库，还需要`git push`到远程仓库，才能完成远程仓库代码的回滚。



### git 合并上游fork 项目更新

> git remote add upstream url
>
> git fetch upstream
>
> git merge upsteam/master
>
> 注：期间可以通过`git remote -v`查看分支情况

## merge 其他分支的指定文件

> 没错，是checkout，但有一点需要注意：会直接覆盖本地的文件，没有merge合并代码的过程

git checkout branch_name filename

##远程覆盖本地代码

- git fetch --all

- git reset --hard origin/master

- git pull

## 关于撤销的一切

> https://www.fengerzh.com/git-reset/

- 代码修改，未`git add `

  `git checkout .` 或 `git reset --hard`

  > `git add .` 和 `git checkout .` 是一对逆操作

- 已经`git add `，未`git commit `

  `git reset ` + `git chekcout .`  或 `git reset --hard` 

- 已经`git commit `

  - `git reset head^`：撤销commit提交，本地库恢复到上一个版本，工作区不变
  - `git reset --hard head^`：撤销commit提交，本地库和工作区同时恢复到上一个版本

- 已经 `git push`

  > 本地覆盖远程

  `git reset --hard HEAD^`
  `git push -f`

## Squash commits

- `git rebase -i commit-version` (which is earlist one that squash beginning from)
- change `pick` to `s`(squash) manually by edting the file, leave the first `pick`, then `:wq`(for vim)
- Edit the commit message, leave the msg for the final commiting, then`:wq`(for vim)



> Reference : [回滚错误修改](https://github.com/geeeeeeeeek/git-recipes/wiki/2.6-%E5%9B%9E%E6%BB%9A%E9%94%99%E8%AF%AF%E7%9A%84%E4%BF%AE%E6%94%B9)
