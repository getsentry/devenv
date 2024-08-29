## devenv

managing dev environments since '24

`devenv` is an extensible execution framework and library for authoring
a simple set of high level commands - bootstrap, sync, doctor, nuke - that
manage a repository's dev environment.

## prerequisites

Are you a Sentry employee? Make sure your GitHub account has been added to a [`getsentry/engineering` team](https://github.com/orgs/getsentry/teams/engineering). If not, open an IT Ticket before continuing.

Otherwise, set the `SENTRY_EXTERNAL_CONTRIBUTOR` environment variable.

## install

Download [this](https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh) and run it:

```
bash install-devenv.sh
```

This "global" devenv is installed to `~/.local/share/sentry-devenv`.

To update this installation, run `devenv update`.


## user guide

`devenv bootstrap`

This is intended for initial setup.


`devenv fetch [repository name]`

Any repository on github in the form of `[org]/[reponame]`

Repositories are cloned to a "coderoot" directory which is specified in the [global configuration](#configuration).

Note: `sentry` and `ops` are currently special names which perform more complicated installations (e.g., `sentry` will set up both sentry and getsentry)

`devenv sync`

When you're inside a repository, this will bring the dev environment up to date,
or create it if it doesn't exist.
It runs `[reporoot]/devenv/sync.py`.

`devenv doctor`

When you're inside a repository, this diagnoses and tries to fix common issues.
Checks and fixes are defined in `[reporoot]/devenv/checks`.

`devenv nuke|uninstall` (wip)

When you're inside a repository, this completely removes the dev environment.


## technical overview

devenv itself lives in `~/.local/share/sentry-devenv`.
This is the "global" devenv. Inside:
- `bin` contains devenv itself and `direnv`
  - this is the only PATH entry needed for devenv
- a private python and virtualenv used exclusively by `devenv`

As much as possible, a repo's dev environment is self-contained within `[reporoot]/.devenv`.

We're relying on `direnv` (which bootstrap will install, globally) to add `[reporoot]/.devenv/bin` to PATH.
Therefore a minimum viable `[reporoot]/.envrc` might look like:

```bash
if [ -f "${PWD}/.env" ]; then
    dotenv
fi

PATH_add "${HOME}/.local/share/sentry-devenv/bin"

if ! command -v devenv >/dev/null; then
    echo "install devenv: https://github.com/getsentry/devenv#install"
    return 1
fi

PATH_add "${PWD}/.devenv/bin"
```

### configuration

global configuration is at `~/.config/sentry-devenv/config.ini`.

repository configuration is at `[reporoot]/devenv/config.ini`.


## develop

We use `tox`. The easiest way to run devenv locally is just using the tox venv's executable:

```
~/code/sentry $  ~/code/devenv/.tox/py311/bin/devenv sync
```
