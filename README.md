## devenv

the next generation sentry devenv management tool

## install

Download [this](https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh) and run it:

```
bash install-devenv.sh
```

**If you are setting up a new development environment, run `devenv bootstrap` after installing.**


## develop

Follow the install instructions, then just work on the git repo in `~/.local/share/sentry-devenv/devenv`.
Changes are immediately reflected in `devenv`.
It isn't pip editable-installed, we just run python directly against the repo as module `devenv.main`.
