from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from collections.abc import Sequence
from typing import Dict
from typing import Tuple

from devenv import pythons
from devenv.constants import home
from devenv.constants import root
from devenv.constants import venv_root
from devenv.constants import VOLTA_HOME
from devenv.lib import proc

help = "Resyncs the environment."


def run_procs(repo: str, reporoot: str, _procs: Tuple[Tuple[str, Tuple[str, ...]], ...]) -> bool:
    procs = []

    for name, cmd in _procs:
        print(f"⏳ {name}")
        procs.append(
            (
                name,
                cmd,
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env={
                        **proc.base_env,
                        "VIRTUAL_ENV": f"{venv_root}/{repo}",
                        "VOLTA_HOME": VOLTA_HOME,
                        "PATH": f"{root}/bin:{venv_root}/{repo}/bin:{proc.base_path}",
                    },
                    cwd=reporoot,
                ),
            )
        )

    all_good = True
    for name, final_cmd, p in procs:
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

{shlex.join(final_cmd)}

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

    # TODO: delete getsentry's .python-version as it will no longer be used
    with open(f"{reporoot}/../sentry/.python-version", "rt") as f:
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
    if not run_procs(
        repo,
        reporoot,
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
                    """
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
        ),
    ):
        return 1

    if not os.path.exists(f"{home}/.sentry/config.yml") or not os.path.exists(
        f"{home}/.sentry/sentry.conf.py"
    ):
        proc.run((f"{venv_root}/{repo}/bin/sentry", "init", "--dev"))

    # TODO: run devservices healthchecks for redis and postgres to bypass this
    proc.run(
        (f"{venv_root}/{repo}/bin/sentry", "devservices", "up", "redis", "postgres"),
        stream_output=True,
        exit=True,
    )

    if not run_procs(
        repo,
        reporoot,
        (("python migrations", (f"{venv_root}/{repo}/bin/sentry", "upgrade", "--noinput")),),
    ):
        return 1

    return 0
