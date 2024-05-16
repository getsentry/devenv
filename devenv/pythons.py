from __future__ import annotations

import os
import shutil
import subprocess

from devenv.constants import CI
from devenv.constants import root
from devenv.lib import archive


def _check_version(exe: str, version: str) -> bool:
    """Returns true if the executable at the given path is a python interpreter
    with a semver-compatible version."""

    try:
        line = (
            subprocess.check_output([exe, "--version"], text=True)
            .strip()
            .lower()
        )
    except subprocess.CalledProcessError:
        return False

    if not line.startswith("python "):
        return False

    actual = line[7:].split(".")
    expected = version.split(".")

    return (
        len(actual) > 2
        and actual[:2] == expected[:2]
        and actual[2] >= expected[2]
    )


def get(python_version: str, url: str, sha256: str) -> str:
    unpack_into = f"{root}/pythons/{python_version}"

    if os.path.exists(f"{unpack_into}/python/bin/python3"):
        return f"{unpack_into}/python/bin/python3"

    if CI:
        system_py = shutil.which("python3")
        if system_py is not None and _check_version(system_py, python_version):
            return system_py

    archive_file = archive.download(url, sha256)
    archive.unpack(archive_file, unpack_into)

    assert os.path.exists(f"{unpack_into}/python/bin/python3")
    return f"{unpack_into}/python/bin/python3"
