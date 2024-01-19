from __future__ import annotations

import configparser
import os

VENV_OK = 1
VENV_VERSION_MISMATCH = 2
VENV_NOT_PRESENT = 3
VENV_NOT_CONFIGURED = 4


def check(reporoot: str) -> bool:
    repo_config = configparser.ConfigParser()
    repo_config.read(f"{reporoot}/devenv/config.ini")

    if not repo_config.has_section("python"):
        # the repo doesn't configure venv support
        # this is mainly here for `devenv exec` which
        # may or may not be run in a python project
        return VENV_NOT_CONFIGURED

    if not os.path.exists(f"{reporoot}/.venv/pyvenv.cfg"):
        return VENV_NOT_PRESENT

    python_version = repo_config["python"]["version"]

    with open(f"{reporoot}/.venv/pyvenv.cfg", "r") as f:
        for line in f:
            if line.startswith("version"):
                venv_version = line.split("=")[1].strip()
                if venv_version != python_version:
                    return VENV_VERSION_MISMATCH

    return VENV_OK
