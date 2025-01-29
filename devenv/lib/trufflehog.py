from __future__ import annotations

import os
import shutil
import tempfile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/trufflehog", f"{into}/trufflehog")


def uninstall(binroot: str) -> None:
    for fp in (f"{binroot}/trufflehog",):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _version(binpath: str) -> str:
    stdout = proc.run((binpath, "--version"), stdout=True)
    return stdout.split()[-1]


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)
    binpath = f"{binroot}/trufflehog"

    if shutil.which("trufflehog", path=binroot) == binpath:
        installed_version = _version(binpath)
        if version == installed_version:
            return
        print(f"installed trufflehog {installed_version} is outdated!")

    print(f"installing trufflehog {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    installed_version = _version(binpath)
    if version != installed_version:
        raise SystemExit(f"Failed to install trufflehog {version}!")
