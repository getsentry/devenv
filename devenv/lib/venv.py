from __future__ import annotations

import os
import shutil
from typing import Optional

from devenv import pythons
from devenv.constants import bin_root
from devenv.constants import venvs_root
from devenv.lib import config
from devenv.lib import fs
from devenv.lib import proc

VENV_OK = 1
VENV_VERSION_MISMATCH = 2
VENV_NOT_PRESENT = 3
VENV_NOT_CONFIGURED = 4


# example venv configuration section:
#
# [venv.sentry-kube]
# python = 3.11.6
# requirements = k8s/cli/requirements.txt
# path = optional
# editable =
#   k8s/cli
#   k8s/cli/libsentrykube
# bins =
#   sentry-kube
#   sentry-kube-pop
#
# [venv.salt]
# python = 3.11.6
# requirements = salt/requirements.txt
# bins =
#   salt-ssh
#   ...
#
# example usage:
#
# venv_dir, python_version, requirements, editable_paths, bins = get(reporoot, "sentry-kube")
# url, sha256 = config.get_python(reporoot, python_version)
# ensure(path, python_version, url, sha256)
# sync(venv_dir, requirements, editable_paths, bins)
def get(
    reporoot: str, name: str
) -> tuple[str, str, str, Optional[tuple[str, ...]], Optional[tuple[str, ...]]]:
    cfg = config.get_repo(reporoot)

    if not cfg.has_section(f"venv.{name}"):
        raise KeyError(f"section venv.{name} not found in repo config")

    venv = cfg[f"venv.{name}"]
    reponame = os.path.basename(reporoot)
    venv_dir = venv.get("path", f"{venvs_root}/{reponame}-{name}")
    editable_paths = venv.get("editable", None)
    if editable_paths is not None:
        editable_paths = tuple(
            f"{reporoot}/{path}" for path in editable_paths.strip().split("\n")
        )

    bins = venv.get("bins", None)
    if bins is not None:
        bins = tuple(
            f"{venv_dir}/bin/{name}" for name in bins.strip().split("\n")
        )

    return (
        venv_dir,
        venv["python"],
        f"{reporoot}/{venv['requirements']}",
        editable_paths,
        bins,
    )


def sync(
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
        for name in bins:
            fs.ensure_symlink(
                expected_src=f"{venv_dir}/bin/{name}", dest=f"{bin_root}/{name}"
            )


# legacy, used for sentry/getsentry
def check_repolocal(reporoot: str) -> int:
    cfg = config.get_repo(reporoot)

    if not cfg.has_section("python"):
        # the repo doesn't configure venv support
        # this is mainly here for `devenv exec` which
        # may or may not be run in a python project
        return VENV_NOT_CONFIGURED

    python_version = cfg["python"]["version"]
    return check(f"{reporoot}/.venv", python_version)


def check(venv: str, python_version: str) -> int:
    if not os.path.exists(f"{venv}/pyvenv.cfg"):
        return VENV_NOT_PRESENT

    with open(f"{venv}/pyvenv.cfg", "r") as f:
        for line in f:
            if line.startswith("version"):
                venv_version = line.split("=")[1].strip()
                if venv_version != python_version:
                    return VENV_VERSION_MISMATCH

    return VENV_OK


# legacy, used for sentry/getsentry
def ensure_repolocal(reporoot: str) -> None:
    venv_status = check_repolocal(reporoot)
    if venv_status == VENV_OK:
        return
    if venv_status == VENV_NOT_CONFIGURED:
        print(
            f"warn: virtualenv isn't configured in {reporoot}/devenv/config.ini"
        )
        return

    url, sha256 = config.get_python(reporoot, "xxx")
    cfg = config.get_repo(reporoot)
    python_version = cfg["python"]["version"]
    url, sha256 = config.get_python(reporoot, python_version)
    ensure(f"{reporoot}/.venv", python_version, url, sha256)


def ensure(venv: str, python_version: str, url: str, sha256: str) -> None:
    venv_status = check(venv, python_version)
    if venv_status == VENV_OK:
        return

    print(
        f"virtualenv doesn't exist or is using an outdated python, recreating at {venv}..."
    )
    if os.path.exists(venv):
        shutil.rmtree(venv)

    proc.run(
        (pythons.get(python_version, url, sha256), "-m", "venv", venv),
        exit=True,
    )
