## devenv

managing dev environments since '24

`devenv` is an extensible execution framework and library for authoring
a simple set of high level commands - bootstrap, fetch, sync, doctor - that
manage a repository's dev environment.

## prerequisites

Are you a Sentry employee? Make sure your GitHub account has been added to a [`getsentry/engineering` team](https://github.com/orgs/getsentry/teams/engineering). If not, open an IT Ticket before continuing.

Otherwise, set the `SENTRY_EXTERNAL_CONTRIBUTOR` environment variable.

## install

Download [this](https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh) and run it:

```
curl https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh > install-devenv.sh
bash install-devenv.sh
```

Make sure to call this file `install-devenv.sh` as the script calls itself when you run it.

This "global" devenv is installed to `~/.local/share/sentry-devenv/bin/devenv`.

To update this installation, run `devenv update`.


## user guide

`devenv bootstrap`

This is intended for initial setup of a new machine.

`devenv fetch [repository name]`

Any repository on github in the form of `[org]/[reponame]`

Repositories are cloned to a "coderoot" directory which is specified in the [global configuration](#configuration).

Note: `sentry` and `ops` are currently special names which perform more complicated installations (e.g., `sentry` will set up both sentry and getsentry)

`devenv sync`

This runs a user-supplied `[reporoot]/devenv/sync.py` which should:
- make sure any desired tools are installed
- bring the dev environment up-to-date, or create it if it doesn't exist

This script runs within devenv's [runtime](#runtime), which has access to many useful high-level routines.
There are currently no api docs, but referring to the [examples](#examples) should get you 90% of the way there.

If you have a feature request, please open an issue!

In general, our library is designed to isolate, as much as possible, a repo's dev environment within `[reporoot]/.devenv`.
For example, [gcloud](#gcloud) is installed to `[reporoot]/.devenv/bin/gcloud` (with the gcloud sdk at `[reporoot]/.devenv/bin/google-cloud-sdk`).
An exception to this would be python virtualenvs, which was implemented before the idea of `[reporoot]/.devenv`.

`devenv doctor`

Use this to diagnose and fix common issues.

Repo-specific checks and fixes can be defined in `[reporoot]/devenv/checks`.
Otherwise we have "builtin" checks and fixes in `devenv.checks`.

`devenv update`

This updates the global devenv installation, and global tools.

If you're upgrading from a particularly old devenv, it won't have `update` so you need to:
`~/.local/share/sentry-devenv/venv/bin/pip install -U sentry-devenv`


## technical overview

Everything devenv needs is in `~/.local/share/sentry-devenv`.

- `~/.local/share/sentry-devenv/bin` contains:
    - `devenv` itself
    - `direnv`
      - we currently rely on direnv and a minimal [`[reporoot]/.envrc`](#direnv) to add `[reporoot]/.devenv/bin` to PATH
      - see [examples](#examples) for .envrc suggestions
    - global tools: `docker` (cli), `colima`


### runtime

- `devenv` is installed exclusively in a virtualenv at `~/.local/share/sentry-devenv/venv`
    - this venv exclusively uses a python at `~/.local/share/sentry-devenv/python`


### global configuration

`~/.config/sentry-devenv/config.ini`
```ini
[devenv]
# the parent directory of all devenv-managed repos
coderoot = ~/code
```


### repository configuration

`[reporoot]/devenv/config.ini`
```ini
[devenv]
# optionally require a minimum version to run sync.py
minimum_version = 1.22.1
```

There are plenty more sections, their use is best seen in the [examples](#examples).


## examples

Skip to:
- [direnv](#direnv)
- [python](#python)
- [node](#node)
- [brew](#brew)
- [colima](#colima)
- [gcloud](#gcloud)
- [terraform](#terraform)

### direnv

A minimum viable `[reporoot]/.envrc` is currently needed:

```bash
if [[ -f "${PWD}/.env" ]]; then
    dotenv
fi

PATH_add "${HOME}/.local/share/sentry-devenv/bin"

if ! command -v devenv >/dev/null; then
    echo "install devenv: https://github.com/getsentry/devenv#install"
    return 1
fi

PATH_add "${PWD}/.devenv/bin"
```

### python

We have support for, and we standardize on [uv](https://github.com/astral-sh/uv)
to manage python environments.

More details (beyond a bare minimum example which is detailed here) about the standard is
[here](https://www.notion.so/sentry/Standard-Spec-python-uv-2248b10e4b5d8045b8fff30f8b8b67ca).

`[reporoot]/.envrc`
```bash
export VIRTUAL_ENV="${PWD}/.venv"

PATH_add "${PWD}/.venv/bin"
```

`[reporoot]/devenv/sync.py`
```py
from devenv.lib import config, uv

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]
    cfg = config.get_repo(reporoot)

    uv.install(
        cfg["uv"]["version"],
        cfg["uv"][constants.SYSTEM_MACHINE],
        cfg["uv"][f"{constants.SYSTEM_MACHINE}_sha256"],
        reporoot,
    )

    # reporoot/.venv is the default venv location
    print(f"syncing .venv ...")
    proc.run(("uv", "sync", "--frozen", "--quiet"))

    return 0
```

We pin the uv version to avoid any surprises.
(As opposed to a solution like `brew`, which always puts you on latest software.)
If you want to update the version then you'll have to update these urls and checksums.

`[reporoot]/devenv/config.ini`
```ini
[devenv]
minimum_version = 1.22.1

[uv]
darwin_arm64 = https://github.com/astral-sh/uv/releases/download/0.8.2/uv-aarch64-apple-darwin.tar.gz
darwin_arm64_sha256 = 954d24634d5f37fa26c7af75eb79893d11623fc81b4de4b82d60d1ade4bfca22
darwin_x86_64 = https://github.com/astral-sh/uv/releases/download/0.8.2/uv-x86_64-apple-darwin.tar.gz
darwin_x86_64_sha256 = ae755df53c8c2c1f3dfbee6e3d2e00be0dfbc9c9b4bdffdb040b96f43678b7ce
linux_arm64 = https://github.com/astral-sh/uv/releases/download/0.8.2/uv-aarch64-unknown-linux-gnu.tar.gz
linux_arm64_sha256 = 27da35ef54e9131c2e305de67dd59a07c19257882c6b1f3cf4d8d5fbb8eaf4ca
linux_x86_64 = https://github.com/astral-sh/uv/releases/download/0.8.2/uv-x86_64-unknown-linux-gnu.tar.gz
linux_x86_64_sha256 = 6dcb28a541868a455aefb2e8d4a1283dd6bf888605a2db710f0530cec888b0ad
# used for autoupdate
# NOTE: if using uv-build as a build backend, you'll have to make sure the versions match
version = 0.8.2
```

`[reporoot]/.python-version`
```
3.13.3
```

`[reporoot]/pyproject.toml`
```
[project]
name = "foo"
version = "0.0.0"
```


### node

`[reporoot]/.envrc`
```bash
PATH_add "${PWD}/node_modules/.bin"
```

`[reporoot]/devenv/sync.py`
```py
from devenv import constants
from devenv.lib import config, node, proc

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]
    cfg = config.get_repo(reporoot)

    node.install(
        cfg["node"]["version"],
        cfg["node"][constants.SYSTEM_MACHINE],
        cfg["node"][f"{constants.SYSTEM_MACHINE}_sha256"],
        reporoot,
    )
    node.install_yarn(cfg["node"]["yarn_version"], reporoot)

    print("installing node dependencies...")
    proc.run(
        (
            ".devenv/bin/yarn",
            "install",
            "--frozen-lockfile",
            "--no-progress",
            "--non-interactive",
        ),
    )

    return 0
```

If you'd like a different node version, fill in the appropriate urls https://nodejs.org/dist/
first in config.ini, then reach out to dev-infra and we can mirror it to GCS.

`[reporoot]/devenv/config.ini`
```ini
[node]
# upstream (https://nodejs.org/dist/) is not reliable enough so we've mirrored it to GCS
darwin_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-x64.tar.xz
darwin_x86_64_sha256 = c83bffeb4eb793da6cb61a44c422b399048a73d7a9c5eb735d9c7f5b0e8659b6
darwin_arm64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-darwin-arm64.tar.xz
darwin_arm64_sha256 = e8a8e78b91485bc95d20f2aa86201485593685c828ee609245ce21c5680d07ce
linux_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v20.13.1-linux-x64.tar.xz
linux_x86_64_sha256 = efc0f295dd878e510ab12ea36bbadc3db03c687ab30c07e86c7cdba7eed879a9
# used for autoupdate
version = v20.13.1
yarn_version = 1.22.22
```

### brew

`[reporoot]/devenv/sync.py`
```py
from devenv import constants
from devenv.lib import brew

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]

    brew.install()

    proc.run(
        (f"{constants.homebrew_bin}/brew", "bundle"),
        cwd=reporoot,
    )

    return 0
```

`[reporoot]/Brewfile`
```
# whatever you want, but we generally discourage installing
# things via brew as it's very difficult to pin a particular
# version of something
```


### colima

Since devenv 1.14.0, colima (and the docker CLI needed to interact with it)
should have been installed globally for you during bootstrap.
If you're on an older version, run `devenv update`.


### gcloud

`[reporoot]/devenv/sync.py`
```py
from devenv import constants
from devenv.lib import config, gcloud

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]
    cfg = config.get_repo(reporoot)

    gcloud.install(
        cfg["gcloud"]["version"],
        cfg["gcloud"][SYSTEM_MACHINE],
        cfg["gcloud"][f"{SYSTEM_MACHINE}_sha256"],
        reporoot,
    )

    return 0
```

`[reporoot]/devenv/config.ini`
```ini
[gcloud]
# custom python version not supported yet, it just uses
# devenv's internal python 3.11
darwin_x86_64 = https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-490.0.0-darwin-x86_64.tar.gz
darwin_x86_64_sha256 = fa396909acc763cf831dd5d89e778999debf37ceadccb3c1bdec606e59ba2694
darwin_arm64 = https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-490.0.0-darwin-arm.tar.gz
darwin_arm64_sha256 = a3a098a5f067b561e003c37284a9b164f28f37fd0d6371bb55e326679f48641c
linux_x86_64 = https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-490.0.0-linux-x86_64.tar.gz
linux_x86_64_sha256 = 40ce41958236f76d9cb08f377ccb9fd6502d2df4da14b36d9214bcb620e2b020
# used for autoupdate
version = 490.0.0
```


### terraform

Our responsibility ends at installing `tenv` and containing `TENV_ROOT` at  `[reporoot]/.devenv/bin/tenv-root`. We install `terraform` and `terragrunt` shims which use that `TENV_ROOT`.

Define `[reporoot]/.terraform-version` and `[reporoot]/.terragrunt-version` (if you want it) and after running sync, you should be able to just type `terraform` and `tenv` takes care of the rest.


`[reporoot]/devenv/sync.py`
```py
from devenv import constants
from devenv.lib import config, tenv

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]
    cfg = config.get_repo(reporoot)

    tenv.install(
        cfg["tenv"]["version"],
        cfg["tenv"][SYSTEM_MACHINE],
        cfg["tenv"][f"{SYSTEM_MACHINE}_sha256"],
        reporoot,
    )

    return 0
```

`[reporoot]/devenv/config.ini`
```ini
[tenv]
darwin_x86_64 = https://github.com/tofuutils/tenv/releases/download/v1.3.0/tenv_v1.3.0_Darwin_x86_64.tar.gz
darwin_x86_64_sha256 = 994100d26f4de6de4eebc7691ca4ea7b424e2fd73e6d5d77c5bf6dfd4af94752
darwin_arm64 =  https://github.com/tofuutils/tenv/releases/download/v1.3.0/tenv_v1.3.0_Darwin_arm64.tar.gz
darwin_arm64_sha256 = c31d2b8412147316a0cadb684408bc123e567852d7948091be7e4303fc19397a
# used for autoupdate
version = v1.3.0
```


## develop

We use `tox`. The easiest way to run devenv locally is just using the tox venv's executable:

```
~/code/sentry $  ~/code/devenv/.tox/py311/bin/devenv sync
```
