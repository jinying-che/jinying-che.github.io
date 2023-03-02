---
title: "Git Cheatsheet"
date: "2023-01-31T16:14:39+08:00"
tags: ["git", "cheatsheet"]
description: "git best practices"
---
### Overall
![git architecture](/images/git.svg)
### Everything about the changes rollback
- code changed without `git add`
  ```shell
  # `git add .` and `git checkout .` is a pair of inverse operations
  git checkout . 
  or 
  git reset --hard
  ```

- `git add .` done without `git commit`
  ```shell
  git reset + git chekcout . 
  or 
  git reset --hard 
  ```

- `git commit` done
  ```shell
  # option 1: keep the changes in worksapce, rollback committed chagnes in local repo
  git reset head^
  # option 2: rollback the changes in both workspace and local repo
  git reset --hard head^
  ```

- `git push` done
  ```shell
  # overwrite remote via the local
  git reset --hard HEAD^
  git push -f
  ```

### [How can I see the changes in a git commit](https://stackoverflow.com/questions/17563726/how-can-i-see-the-changes-in-a-git-commit)?
`git diff COMMIT~ COMMIT` or `git show COMMIT`
    
### How to include config directives from another source? 
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

### Keep the local changes, delete the remote changes 
delete the local cache, push to the remote
```shell
1. git rm —cache -r directory
2. git commit -m "del"
3. git pushf
 ```

### Git merge the update from the forked project
```shell
1. git remote add upstream url
2. git fetch upstream
3. git merge upsteam/master

 # NOTE check the remote brach status:
 git remote -v
```

### Git merge the file from the other branch
exactly, it's `checkout`, pls be reminded that this command will overwrite the local file without merging process
```shell
git checkout branch_name filename
```

### Overwrite the local via the remote
```shell
1. git fetch --all
2. git reset --hard origin/master

```

### Squash commits
1. `git rebase -i commit-version` (which is earlist one that squash beginning from)
2. change `pick` to `s`(squash) manually by edting the file, leave the first `pick`, then `:wq`(for vim)
3. Edit the commit message, leave the msg for the final commiting, then`:wq`(for vim)

## Reference
- https://www.fengerzh.com/git-reset/
