# Personal Blog

This project is used to generate the static Web site powered by [Hugo](https://gohugo.io/) and [hugo-theme-terminal](https://github.com/panr/hugo-theme-terminal)

Here is my [blog](https://jinying-che.github.io/)

## How to setup a website hosted by Github Page
1. create a repository in Github following [Github Pages](https://pages.github.com/)
2. choose a static site generators and theme accordingly (mine is mentioned at the beginning)
3. set up a CICD workflow for the web site deployment following [Hugo x Github Pages x Github Action](https://gohugo.io/hosting-and-deployment/hosting-on-github/) 

## How to post a new blog
1. `hugo new posts/path/xxx.md`
2. Edit the `xxx.md` 
3. Review the post locally by running `hugo server -D` and adjust if needed
4. push the changes to `main` branch which will trigger the **Github Action** automatically
5. check the [action workflow](https://github.com/jinying-che/jinying-che.github.io/actions) which is defined by [github/workflows/gh-pages.yml](github/workflows/gh-pages.yml)
	- action 1: hugo build and generate the `/public` and push it to `gh-pages` branch
	- actoin 2: pages build and deployment from `gh-pages` branch

## Hugo 
- How to install theme: [install-theme-as-hugo-module](https://github.com/panr/hugo-theme-terminal#install-theme-as-hugo-module)

## Reference
- Hugo
	- [Front Matter](https://gohugo.io/content-management/front-matter/#example)
	- [Hugo x Github Pages x Github Action](https://gohugo.io/hosting-and-deployment/hosting-on-github/)
	- Some [hugo-theme-terminal](https://github.com/panr/hugo-theme-terminal) Users:
		- https://skoula.cz/
		- https://mn3m.info/
- GitHub
	- [Pages](https://pages.github.com/)
	- [Action](https://docs.github.com/en/actions/quickstart)
	- [Events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#push)

