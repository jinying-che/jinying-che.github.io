# Personal Blog

This project is used to generate the static Web code which is powered by [Hugo](https://gohugo.io/)

Here is my [blog](https://jinying-che.github.io/)

## First Of All
If it's your first time to check out the repo:
- Run `git submodule update --init --recursive` to initial all the sub-module
For update:
- `git submodule update --recursive --remote` 

## How to post a new blog?
- `hugo new posts/path/xxx.md`
- Edit the `xxx.md` 
- Review the post locally by running `hugo server -D` and adjust if needed
- Run `sh deploy.sh` to deploy the new post to website (update the `public` subproject)
- Update the `Blog` project (git add, commit, push)

