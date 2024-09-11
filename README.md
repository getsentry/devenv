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

When you're inside a repository, this diagnoses and tries to fix common issues.
Checks and fixes are defined in `[reporoot]/devenv/checks`.

`devenv nuke|uninstall` (wip)

When you're inside a repository, this completely removes the dev environment.


## technical overview

Everything devenv needs is in `~/.local/share/sentry-devenv`.

- `~/.local/share/sentry-devenv/bin` contains `devenv` and `direnv`
    - we currently rely on a minimal [`[reporoot]/.envrc`](#direnv) to add `[reporoot]/.devenv/bin` to PATH
    - see [examples](#examples) for .envrc suggestions

### runtime

- `devenv` is installed exclusively in a virtualenv at `~/.local/share/sentry-devenv/venv`
    - this venv exclusively uses a python at `~/.local/share/sentry-devenv/python`


### configuration

global configuration is at `~/.config/sentry-devenv/config.ini`.

repository configuration is at `[reporoot]/devenv/config.ini`.


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

You can have multiple virtualenvs, which is useful if you rely on a python tool
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
from devenv.lib import config, node

def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]
    repo_config = config.get_config(f"{reporoot}/devenv/config.ini")

    node.install(
        repo_config["node"]["version"],
        repo_config["node"][constants.SYSTEM_MACHINE],
        repo_config["node"][f"{constants.SYSTEM_MACHINE}_sha256"],
        reporoot,
    )
    node.install_yarn(repo_config["node"]["yarn_version"], reporoot)

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


## develop

We use `tox`. The easiest way to run devenv locally is just using the tox venv's executable:

```
~/code/sentry $  ~/code/devenv/.tox/py311/bin/devenv sync
```
