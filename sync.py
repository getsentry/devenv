from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Sequence
from typing import Dict
from typing import Tuple

from devenv import pythons
from devenv.constants import venv_root
from devenv.lib import proc

help = "Resyncs the environment."


def run_procs(_procs: Tuple[Tuple[str, Tuple[str, ...]], ...]) -> bool:
    procs = []

    for name, args in _procs:
        print(f"> {name}")
        procs.append(
            (name, args, subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT))
        )

    all_good = True
    for name, args, p in procs:
        cmd = " ".join(args)
        p.wait()
        if p.returncode != 0:
            all_good = False
            if p.stdout is None:
                out = ""
            else:
                out = p.stdout.read().decode()
            print(
                f"""
❌ {name}

{cmd}

Output (returncode {p.returncode}):

{out}

"""
            )
        else:
            print(f"✅ {name}")

    return all_good


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> int:
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

    # TODO: delete getsentry's .python-version as it will no longer be used
    with open(f"{reporoot}/.python-version", "rt") as f:
        python_version = f.read().strip()

    # If the venv doesn't exist, create it with the expected python version.
    os.makedirs(venv_root, exist_ok=True)
    venv = f"{venv_root}/{repo}"

    if not os.path.exists(venv):
        print(f"virtualenv for {repo} doesn't exist, creating one...")
        proc.run((pythons.get(python_version), "-m", "venv", venv), exit=True)

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
        proc.run((pythons.get(python_version), "-m", "venv", venv), exit=True)

    print("Resyncing your dev environment.")
    all_good = run_procs(
        (
            ("git and precommit", ("make", "setup-git")),
            ("javascript dependencies", ("make", "install-js-dev")),
            (
                "python dependencies",
                (
                    "/bin/bash",
                    "-euo",
                    "pipefail",
                    "-c",
                    f"""
source "{venv}/bin/activate"
export PIP_DISABLE_PIP_VERSION_CHECK=on

pip_install='pip install --constraint requirements-dev-frozen.txt'
$pip_install --upgrade pip setuptools wheel

# pip doesn't do well with swapping drop-ins
pip uninstall -qqy uwsgi

$pip_install -r requirements-dev-frozen.txt -r requirements-getsentry.txt

pip_install_editable='pip install --no-deps'
SENTRY_LIGHT_BUILD=1 $pip_install_editable -e . -e ../getsentry
""",
                ),
            ),
        )
    )
    if not all_good:
        return 1

    # TODO: need to make sure devservices are running
    all_good = run_procs((("python migrations", ("sentry", "upgrade", "--noinput")),))
    if not all_good:
        return 1

    return 0
