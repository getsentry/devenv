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

    with open(f'{context["reporoot"]}/.python-version', "rt") as f:
        python_version = f.read().strip()

    # If the venv doesn't exist, create it with the expected python version.
    venvroot = os.path.expanduser("~/.sentry-dev/virtualenvs")
    os.makedirs(venvroot, exist_ok=True)
    venv = f"{venvroot}/{repo}"

    if not os.path.exists(venv):
        print(f"virtualenv for {repo} doesn't exist, creating one (python {python_version})...")
        subprocess.run((pythons.get(python_version), "-m", "venv", venv))

    # Check the python version. If mismatch, then recreate the venv.
    # "{venv}/bin/python"

    # Install -e . and with requirements-dev-frozen.txt.

    # TODO: frontend environment

    return 0
