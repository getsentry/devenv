from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Sequence

from devenv import pythons

help = "Resyncs the environment."


def main(context: dict, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.parse_args(argv)

    repo = context["repo"]
    if repo not in {"sentry", "getsentry"}:
        print(f"repo {repo} not supported yet!")
        return 1

    # What does it take to have one venv that sentry and getsentry can coexist in?
    # Try this. I suppose it's pretty easy since we now have requirements-getsentry.txt
    # in sentry repo.
    if repo == "getsentry":
        repo = "sentry"

    with open(f'{context["reporoot"]}/.python-version', "rt") as f:
        python_version = f.read().strip()

    # If the venv doesn't exist, create it with the expected python version.
    venvroot = os.path.expanduser("~/.sentry-dev/virtualenvs")
    os.makedirs(venvroot, exist_ok=True)
    venv = f"{venvroot}/{repo}"

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
    script = f"""
source "{venv}/bin/activate"
pip install -r requirements-dev-frozen.txt -r requirements-getsentry.txt
"""
    subprocess.run(["/bin/sh", "-c", script])

    # TODO: frontend environment
    return 0
