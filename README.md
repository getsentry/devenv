## devenv

the next generation sentry devenv management tool

## install

Download [this](https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh) and run it:

```
bash install-devenv.sh
```

**If you are setting up a new development environment, run `devenv bootstrap` after installing.**


## develop

Purpose: enable `gh act` to work quickly on localhost

To that end:

1. build a docker image with python pre-installed at the expected location
2. the python interpreter machine-architecture should match the host machine
