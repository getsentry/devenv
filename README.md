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

We're relying on `direnv` (which bootstrap will install for you at `~/.local/share/sentry-devenv/bin/direnv`)
to add `[reporoot]/.devenv/bin` to PATH.
See [examples](#examples) for an example `[reporoot]/.envrc`.


## configuration

global configuration is at `~/.config/sentry-devenv/config.ini`.

repository configuration is at `[reporoot]/devenv/config.ini`.


## examples

Skip to:
- [python](#python)
- [node](#node)
- [brew](#brew)
- [colima](#colima)
- [gcloud](#gcloud)
- [terraform](#terraform)

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
path = .venv
requirements = requirements-dev.txt
editable =
  .

[venv.inhouse-tool]
python = 3.12.3
requirements = inhouse-tool/requirements-dev.txt
bins =
  # .devenv/bin/tool -> .venv-inhouse-tool/bin/tool
  tool

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


## develop

We use `tox`. The easiest way to run devenv locally is just using the tox venv's executable:

```
~/code/sentry $  ~/code/devenv/.tox/py311/bin/devenv sync
```
