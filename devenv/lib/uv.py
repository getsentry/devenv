from __future__ import annotations

import os
import shutil
import tempfile

from devenv import constants
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

install_help = """\
uv is required but wasn't found on PATH.
Install it with `brew install uv`, or see
https://docs.astral.sh/uv/getting-started/installation/
"""


def find() -> str:
    """Returns the path to the uv on PATH.

    Falls back to ~/.local/bin/uv, which is where astral's installer
    (and install-devenv.sh) puts uv, in case that isn't on PATH yet.
    """
    found = shutil.which("uv")
    if found is not None:
        return found

    fallback = f"{constants.home}/.local/bin/uv"
    if os.access(fallback, os.X_OK):
        return fallback

    raise SystemExit(install_help)


def _install(url: str, sha256: str, into: str) -> None:
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd, perform_strip1=True)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/uv", f"{into}/uv")
        os.replace(f"{tmpd}/uvx", f"{into}/uvx")


def uninstall(binroot: str) -> None:
    for fp in (f"{binroot}/uv", f"{binroot}/uvx"):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _version(binpath: str) -> str:
    stdout = proc.run((binpath, "--version"), stdout=True)
    # uv 0.7.21 (77c771c7f 2025-07-14)
    return stdout.split()[1]


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    print("!!! devenv-managed uv is deprecated! run `brew install uv` !!!")

    binroot = fs.ensure_binroot(reporoot)
    binpath = f"{binroot}/uv"

    if shutil.which("uv", path=binroot) == binpath:
        installed_version = _version(binpath)
        if version == installed_version:
            return
        print(f"installed uv {installed_version} is unexpected!")

    print(f"installing uv {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    installed_version = _version(binpath)
    if version != installed_version:
        raise SystemExit("Failed to install uv {version}!")
