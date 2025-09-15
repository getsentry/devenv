from __future__ import annotations

import os
import shutil
import stat
import tempfile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        bin_file = archive.download(url, sha256, dest=f"{tmpd}/pnpm")

        target = f"{into}/pnpm"
        os.replace(bin_file, target)
        mode = os.stat(target).st_mode
        os.chmod(target, mode | stat.S_IEXEC)


def uninstall(binroot: str) -> None:
    try:
        os.remove(f"{binroot}/pnpm")
    except FileNotFoundError:
        # it's better to do this than to guard with
        # os.path.exists(fp) because if it's an invalid or circular
        # symlink the result'll be False!
        pass


def _version(binpath: str) -> str:
    stdout = proc.run((binpath, "--version"), stdout=True)
    # 10.16.1
    return stdout.strip()


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)
    binpath = f"{binroot}/pnpm"

    if shutil.which("pnpm", path=binroot) == binpath:
        installed_version = _version(binpath)
        if version == installed_version:
            return
        print(f"installed pnpm {installed_version} is unexpected!")

    print(f"installing pnpm {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    installed_version = _version(binpath)
    if version != installed_version:
        raise SystemExit("Failed to install pnpm {version}!")
