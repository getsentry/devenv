from __future__ import annotations

import os
import shutil
import sys

from devenv import pythons
from devenv.constants import MACHINE
from devenv.lib import proc
from devenv.lib.config import repo_config

VENV_OK = 1
VENV_VERSION_MISMATCH = 2
VENV_NOT_PRESENT = 3
VENV_NOT_CONFIGURED = 4


def check(reporoot: str) -> int:
    cfg = repo_config(reporoot)

    if not cfg.has_section("python"):
        # the repo doesn't configure venv support
        # this is mainly here for `devenv exec` which
        # may or may not be run in a python project
        return VENV_NOT_CONFIGURED

    if not os.path.exists(f"{reporoot}/.venv/pyvenv.cfg"):
        return VENV_NOT_PRESENT

    python_version = cfg["python"]["version"]

    with open(f"{reporoot}/.venv/pyvenv.cfg", "r") as f:
        for line in f:
            if line.startswith("version"):
                venv_version = line.split("=")[1].strip()
                if venv_version != python_version:
                    return VENV_VERSION_MISMATCH

    return VENV_OK


def ensure(reporoot: str) -> None:
    venv_status = check(reporoot)
    if venv_status == VENV_OK:
        return
    if venv_status == VENV_NOT_CONFIGURED:
        print(
            f"warn: virtualenv isn't configured in {reporoot}/devenv/config.ini"
        )
        return

    print(
        "virtualenv doesn't exist or is using an outdated python, recreating..."
    )
    if os.path.exists(f"{reporoot}/.venv"):
        shutil.rmtree(f"{reporoot}/.venv")

    cfg = repo_config(reporoot)
    python_version = cfg["python"]["version"]
    url = cfg["python"][f"{sys.platform}_{MACHINE}"]
    sha256 = cfg["python"][f"{sys.platform}_{MACHINE}_sha256"]

    proc.run(
        (
            pythons.get(python_version, url, sha256),
            "-m",
            "venv",
            f"{reporoot}/.venv",
        ),
        exit=True,
    )
