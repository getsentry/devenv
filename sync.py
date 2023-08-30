from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Sequence

from devenv import pythons
from devenv.constants import venv_root

help = "Resyncs the environment."

scripts = {
    # TODO: equivalent of make install-js-dev and make apply-migrations
    "sentry": """
source "{venv}/bin/activate"
export PIP_DISABLE_PIP_VERSION_CHECK=on

pip_install='pip install --constraint requirements-dev-frozen.txt'
$pip_install --upgrade pip setuptools wheel

# pip doesn't do well with swapping drop-ins
pip uninstall -qqy uwsgi

$pip_install -r requirements-dev-frozen.txt -r requirements-getsentry.txt

SENTRY_LIGHT_BUILD=1 $pip_install -e . --no-deps
SENTRY_LIGHT_BUILD=1 $pip_install -e ../getsentry --no-deps
""",
}


def main(context: dict, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.parse_args(argv)

    repo = context["repo"]
    if repo not in {"sentry", "getsentry"}:
        print(f"repo {repo} not supported yet!")
        return 1

    # it's easier to maintain a single venv that sentry and getsentry shares
    reporoot = context["reporoot"]
    if repo == "getsentry":
        repo = "sentry"
        reporoot = f"{reporoot}/../sentry"
        os.chdir(reporoot)

    reporoot = context["reporoot"]

    with open(f"{reporoot}/.python-version", "rt") as f:
        python_version = f.read().strip()

    # If the venv doesn't exist, create it with the expected python version.
    os.makedirs(venv_root, exist_ok=True)
    venv = f"{venv_root}/{repo}"

    if not os.path.exists(venv):
        print(f"virtualenv for {repo} doesn't exist, creating one...")
        subprocess.run((pythons.get(python_version), "-m", "venv", venv))

    # Check the python version. If mismatch, then recreate the venv.
    # This helps smooth out the python version upgrade experience.
    # XXX: it isn't in a format configparser can read as there are no sections
    venv_version = ""
    with open(f"{venv}/pyvenv.cfg", "r") as f:
        for line in f:
            if line.startswith("version"):
                venv_version = line.split("=")[1].strip()
                break
    if venv_version != python_version:
        print(f"outdated virtualenv version (python {venv_version})!")
        print("creating a new one...")
        # stampeding over it seems to work (no need for rm -rf)
        subprocess.run((pythons.get(python_version), "-m", "venv", venv))

    print("Resyncing your venv.")
    return subprocess.call(["/bin/sh", "-c", scripts[repo].format(venv=venv)])
