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


## technical overview

Everything devenv needs is in `~/.local/share/sentry-devenv`.

- `~/.local/share/sentry-devenv/bin` contains `devenv` and `direnv`
    - we currently rely on a minimal [`[reporoot]/.envrc`](#direnv) to add `[reporoot]/.devenv/bin` to PATH
    - see [examples](#examples) for .envrc suggestions

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
minimum_version = 1.11.0
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

Need a single virtualenv (or have one already at `.venv` you want devenv to manage?)

`[reporoot]/.envrc`
```bash
export VIRTUAL_ENV="${PWD}/.venv"

PATH_add "${PWD}/.venv/bin"
```

`[reporoot]/devenv/sync.py`
```py
from devenv.lib import config, venv

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]

    venv_dir, python_version, requirements, editable_paths, bins = venv.get(reporoot, "venv")
    url, sha256 = config.get_python(reporoot, python_version)
    print(f"ensuring venv at {venv_dir}...")
    venv.ensure(venv_dir, python_version, url, sha256)

    print(f"syncing venv with {requirements}...")
    venv.sync(reporoot, venv_dir, requirements, editable_paths, bins)

    return 0
```

`[reporoot]/devenv/config.ini`
```ini
[venv.venv]
python = 3.12.3
path = .venv
requirements = requirements-dev.txt
editable =
  .

[python3.12.3]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = c37a22fca8f57d4471e3708de6d13097668c5f160067f264bb2b18f524c890c8
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = ccc40e5af329ef2af81350db2a88bbd6c17b56676e82d62048c15d548401519e
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = a73ba777b5d55ca89edef709e6b8521e3f3d4289581f174c8699adfb608d09d6
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = ec8126de97945e629cca9aedc80a29c4ae2992c9d69f2655e27ae73906ba187d
```

You can also have multiple virtualenvs, which is useful if you rely on a python tool
that has a bunch of dependencies that may conflict with others.

`[reporoot]/.envrc`
```bash
export VIRTUAL_ENV="${PWD}/.exampleproject"

PATH_add "${PWD}/.venv-exampleproject/bin"
PATH_add "${PWD}/.venv-inhouse-tool/bin"
```

`[reporoot]/devenv/sync.py`
```py
from devenv.lib import config, venv

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]

    for name in ("exampleproject", "inhouse-tool"):
        venv_dir, python_version, requirements, editable_paths, bins = venv.get(reporoot, name)
        url, sha256 = config.get_python(reporoot, python_version)
        print(f"ensuring {name} venv at {venv_dir}...")
        venv.ensure(venv_dir, python_version, url, sha256)

        print(f"syncing {name} with {requirements}...")
        venv.sync(reporoot, venv_dir, requirements, editable_paths, bins)

    return 0
```

`[reporoot]/devenv/config.ini`
```ini
[venv.exampleproject]
python = 3.12.3
requirements = requirements-dev.txt
editable =
  .

[venv.inhouse-tool]
python = 3.12.3
requirements = inhouse-tool/requirements-dev.txt

[python3.12.3]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = c37a22fca8f57d4471e3708de6d13097668c5f160067f264bb2b18f524c890c8
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = ccc40e5af329ef2af81350db2a88bbd6c17b56676e82d62048c15d548401519e
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = a73ba777b5d55ca89edef709e6b8521e3f3d4289581f174c8699adfb608d09d6
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20240415/cpython-3.12.3+20240415-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = ec8126de97945e629cca9aedc80a29c4ae2992c9d69f2655e27ae73906ba187d
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
