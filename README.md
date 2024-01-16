## devenv

the next generation sentry devenv management tool

## install

Download [this](https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh) and run it:

```
bash install-devenv.sh
```

**If you are setting up a new laptop, run `devenv bootstrap` after installing.**



## technical overview

`devenv` is a command-line interface to a set of environment management commands
that can be custom implemented for a particular repository.

- `sync` brings the dev environment up-to-date
  - example: in sentry, `sync` updates python+js dependencies, and runs migrations
- `doctor` diagnoses and fixes common issues
  - TODO: more on this later, we're working on this at the moment
  - you can write these doctor "checks" using `devenv` facilities, and they're executed within devenv's environment
  - example to be available at `sentry/devenv/checks/....py`
- `exec` (coming soon) execs a command inside of `devenv`'s execution context, useful if things don't work locally

Dependencies like `colima` and `volta` are hermetically installed and used within `devenv`'s execution.
This lets us dictate how they get installed, and it doesn't affect the rest of the system.

`devenv` also:
- helps new engineers `devenv bootstrap` their new macbooks nearly effortlessly


### per-repository configuration

`REPOROOT/devenv/config.ini`

an example: if the right `[python]` block is specified (see sentry's),
we support downloading those prebuilt pythons for a repo's virtualenv


## develop

Purpose: enable `gh act` to work quickly on localhost

To that end:

1. build a docker image with python pre-installed at the expected location
2. the python interpreter machine-architecture should match the host machine
