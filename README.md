## devenv

managing dev environments since '24

`devenv` is an extensible execution framework and library for authoring
a simple set of high level commands - bootstrap, fetch, sync, doctor - that
manage a repository's dev environment.

## Prerequisites

If you are a Sentry employee, make sure your GitHub account is in a [`getsentry/engineering` team](https://github.com/orgs/getsentry/teams/engineering). If it is not, open an IT ticket before you continue.

If you are not a Sentry employee, set the `SENTRY_EXTERNAL_CONTRIBUTOR` environment variable. `devenv bootstrap` and `devenv fetch` both read it.

## Install

Download [`install-devenv.sh`](https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh) and run it:

```
curl https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh > install-devenv.sh
bash install-devenv.sh
```

Keep the file name `install-devenv.sh`. The script only runs its installer when it has that name.

The script installs the global devenv to `~/.local/share/sentry-devenv/bin/devenv`.

devenv uses [uv](https://docs.astral.sh/uv/) to install itself and to manage virtualenvs; it does not use pip.
Install the latest uv first with `brew install uv`. If the script can't find uv, it installs the latest uv to `~/.local/bin` with uv's official installer.

To update the global devenv, run `devenv update`.

## Commands

Run `devenv --help` for the full list.

`devenv bootstrap`

Sets up a new machine. It writes the [global configuration](#global-configuration), configures GitHub SSH access, and installs the global tools.

`devenv fetch [repository name]`

Clones any GitHub repository in the form `[org]/[reponame]` over SSH into your coderoot, then runs `devenv sync` in it. If you omit the org, it defaults to `getsentry`.

`sentry` and `ops` are special names:

- `devenv fetch sentry` sets up `getsentry/sentry`, and also `getsentry/getsentry` unless `SENTRY_EXTERNAL_CONTRIBUTOR` is set.
- `devenv fetch ops` sets up `getsentry/ops` and clones `getsentry/terraform-modules`.

`devenv sync`

Runs the repo's `sync.py` from the [repo config directory](#repository-configuration). `sync.py` defines `main(context: dict[str, str]) -> int`. The `context` keys are `reporoot`, `repo`, and `coderoot`. `sync.py` should:

- install any tools the repo needs
- create the dev environment, or bring it up to date

`sync.py` runs in devenv's [runtime](#runtime), so it can import the `devenv.lib` modules. There are no API docs. Start from the [examples](#examples). If you have a feature request, open an issue.

The library keeps a repo's dev environment inside `[reporoot]/.devenv` where it can.
For example, [gcloud](#gcloud) is installed to `[reporoot]/.devenv/bin/gcloud`, with the gcloud SDK at `[reporoot]/.devenv/bin/google-cloud-sdk`.
Python virtualenvs are an exception because they predate `[reporoot]/.devenv`.

`devenv doctor`

Diagnoses and fixes common issues. Use `--check-only` to skip fixes, and `--tag` or `--exclude-tag` to select checks.

Builtin checks live in `devenv.checks`. A repo can add its own checks in the `checks` directory of its [repo config directory](#repository-configuration).

`devenv update [version]`

Updates the global devenv installation and the global tools. Pass a version to install that version.

If your devenv is old enough that it has no `update` command, run:
`uv pip install --python ~/.local/share/sentry-devenv/venv/bin/python -U sentry-devenv`

`devenv colima start`

Starts colima with resources sized for your machine. The default `colima start` may underprovision resources. Run `devenv colima start` on a new machine, and again after `colima delete`. The other subcommands are `restart`, `check`, and `stop`.

`devenv pin_gha [file ...]`

Pins each `uses:` reference in the given GitHub Actions workflow files to a commit SHA.

## Technical overview

Everything devenv needs is in `~/.local/share/sentry-devenv`.

`~/.local/share/sentry-devenv/bin` contains:

- `devenv` itself
- `direnv`, if direnv was not already on your PATH. devenv relies on direnv and a minimal [`[reporoot]/.envrc`](#direnv) to add `[reporoot]/.devenv/bin` to PATH.
- on macOS only, the global tools: the `docker` CLI, `colima`, and `lima`. On Linux, install docker engine yourself. `devenv bootstrap` exits if it is missing.

### Runtime

`devenv` is installed with uv in a virtualenv at `~/.local/share/sentry-devenv/venv`.
That virtualenv uses the Python at `~/.local/share/sentry-devenv/python`.
It has no pip; `devenv update` uses `uv pip` to update it.

### Global configuration

`~/.config/sentry-devenv/config.ini`
```ini
[devenv]
# the parent directory of all devenv-managed repos
coderoot = ~/code
```

### Repository configuration

devenv reads `config.ini`, `sync.py`, and `checks` from the repo config directory.
The repo config directory is `[reporoot]/.devenv` if `[reporoot]/.devenv/config.ini` exists.
Otherwise, it is `[reporoot]/devenv` if `[reporoot]/devenv/config.ini` exists.
If neither file exists, it is `[reporoot]/.devenv`.
The examples below use `[reporoot]/devenv`.

`[reporoot]/devenv/config.ini`
```ini
[devenv]
# optionally require a minimum version to run sync.py
minimum_version = 1.22.1
```

The [examples](#examples) show the other sections.

## Examples

Skip to:
- [direnv](#direnv)
- [python](#python)
- [node](#node)
- [brew](#brew)
- [colima](#colima)
- [gcloud](#gcloud)
- [terraform](#terraform)

### direnv

Every repo needs a minimal `[reporoot]/.envrc`:

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

devenv does not manage uv installations. Run `brew install uv`.

To activate the virtualenv with direnv and run `uv sync` as part of `devenv sync`:

`[reporoot]/.envrc`
```bash
export VIRTUAL_ENV="${PWD}/.venv"

PATH_add "${PWD}/.venv/bin"
```

`[reporoot]/devenv/sync.py`
```py
from devenv.lib import proc

def main(context: dict[str, str]) -> int:
    # reporoot/.venv is the default venv location
    print(f"syncing .venv ...")
    proc.run(("uv", "sync", "--frozen", "--quiet"))

    return 0
```

Use `[reporoot]/.python-version` to pin a python version for uv:
```
3.13.3
```

### node

`node.install_pnpm` installs the pnpm version named in the `packageManager` field of `[reporoot]/package.json`.

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

    node.install_pnpm(reporoot)

    print("installing node dependencies...")
    proc.run(
        (
            f"{reporoot}/.devenv/bin/pnpm",
            "install",
            "--frozen-lockfile",
            "--reporter=append-only",
        ),
    )

    return 0
```

If you want a different node version, first fill in the matching URLs from https://nodejs.org/dist/ in `config.ini`. Then ask dev-infra to mirror them to GCS.

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
```

### brew

`[reporoot]/devenv/sync.py`
```py
from devenv import constants
from devenv.lib import brew, proc

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

On macOS, `devenv bootstrap` installs colima and the docker CLI globally. If you installed devenv before 1.14.0, run `devenv update` to get them.

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
        cfg["gcloud"][constants.SYSTEM_MACHINE],
        cfg["gcloud"][f"{constants.SYSTEM_MACHINE}_sha256"],
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

devenv installs `tenv` and keeps `TENV_ROOT` at `[reporoot]/.devenv/bin/tenv-root`. It also writes `tenv`, `terraform`, `tofu`, and `terragrunt` shims to `[reporoot]/.devenv/bin` that use that `TENV_ROOT`. It does not write a `tf` shim, so a repo's own `tf` wrapper is not shadowed.

Define `[reporoot]/.terraform-version`, and optionally `[reporoot]/.terragrunt-version`. After `devenv sync`, run `terraform` and `tenv` installs the pinned version.

`[reporoot]/devenv/sync.py`
```py
from devenv import constants
from devenv.lib import config, tenv

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]
    cfg = config.get_repo(reporoot)

    tenv.install(
        cfg["tenv"]["version"],
        cfg["tenv"][constants.SYSTEM_MACHINE],
        cfg["tenv"][f"{constants.SYSTEM_MACHINE}_sha256"],
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

## Get help

Run `devenv doctor` first. If that does not fix it, see the [devenv troubleshooting guide](https://develop.sentry.dev/development-infrastructure/environment/#troubleshooting).
