from __future__ import annotations

import os
import shutil
from enum import Enum
from typing import Optional

from devenv import pythons
from devenv.lib import config
from devenv.lib import fs
from devenv.lib import proc

VenvStatus = Enum(
    "VenvStatus", ("OK", "VERSION_MISMATCH", "NOT_PRESENT", "NOT_CONFIGURED")
)


def get(
    reporoot: str, name: str
) -> tuple[str, str, str, Optional[tuple[str, ...]], Optional[tuple[str, ...]]]:
    cfg = config.get_repo(reporoot)

    if not cfg.has_section(f"venv.{name}"):
        raise KeyError(f"section venv.{name} not found in repo config")

    venv = cfg[f"venv.{name}"]
    venv_dir = venv.get("path", f"{reporoot}/.venv-{name}")
    editable_paths_s = venv.get("editable", None)
    if editable_paths_s is not None:
        editable_paths = tuple(
            f"{reporoot}/{path}"
            for path in editable_paths_s.strip().split("\n")
        )
    else:
        editable_paths = None

    bins_s = venv.get("bins", None)
    if bins_s is not None:
        bins = tuple(bins_s.strip().split("\n"))
    else:
        bins = None

    return (
        venv_dir,
        venv["python"],
        f"{reporoot}/{venv['requirements']}",
        editable_paths,
        bins,
    )


def sync(
    reporoot: str,
    venv_dir: str,
    requirements: str,
    editable_paths: Optional[tuple[str, ...]] = None,
    bins: Optional[tuple[str, ...]] = None,
) -> None:
    cmd: tuple[str, ...] = (
        f"{venv_dir}/bin/python",
        "-m",
        "pip",
        "--disable-pip-version-check",
        "--no-color",
        "--quiet",
        "--require-virtualenv",
        "install",
        "-r",
        requirements,
    )
    if editable_paths is not None:
        for path in editable_paths:
            cmd = (*cmd, "-e", path)
    proc.run(cmd)

    if bins is not None:
        binroot = fs.ensure_binroot(reporoot)
        for name in bins:
            fs.ensure_symlink(
                expected_src=f"{venv_dir}/bin/{name}", dest=f"{binroot}/{name}"
            )


def check(venv: str, python_version: str) -> VenvStatus:
    try:
        os.stat(f"{venv}/bin/python")
    except FileNotFoundError:
        return VenvStatus.NOT_PRESENT

    if not os.path.exists(f"{venv}/pyvenv.cfg"):
        return VenvStatus.NOT_PRESENT

    with open(f"{venv}/pyvenv.cfg", "r") as f:
        for line in f:
            if line.startswith("version"):
                venv_version = line.split("=")[1].strip()
                if venv_version != python_version:
                    return VenvStatus.VERSION_MISMATCH

    return VenvStatus.OK


def ensure(venv: str, python_version: str, url: str, sha256: str) -> None:
    venv_status = check(venv, python_version)
    if venv_status == VenvStatus.OK:
        return

    print(
        f"virtualenv doesn't exist or is using an unexpected python, recreating at {venv}..."
    )
    if os.path.exists(venv):
        shutil.rmtree(venv)

    proc.run(
        (pythons.get(python_version, url, sha256), "-m", "venv", venv),
        exit=True,
    )

    with open(f"{venv}/.gitignore", "w") as f:
        f.write(
            """*
# automatically written by devenv
"""
        )
