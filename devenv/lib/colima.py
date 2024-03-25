from __future__ import annotations

import os
import shutil
import tempfile
from typing import Optional

from devenv.constants import home
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive.download(url, sha256, dest=f"{tmpd}/colima")
        os.replace(f"{tmpd}/colima", f"{into}/colima")
        os.chmod(f"{into}/colima", 0o775)


def uninstall(binroot: str) -> None:
    for d in (f"{home}/.lima",):
        shutil.rmtree(d, ignore_errors=True)

    for f in (f"{binroot}/colima",):
        if os.path.exists(f):
            os.remove(f)


def install(
    version: str, url: str, sha256: str, reporoot: Optional[str] = ""
) -> None:
    if reporoot:
        binroot = fs.ensure_binroot(reporoot)
    else:
        # compatibility with devenv <= 1.4.0
        binroot = f"{root}/bin"
        os.makedirs(binroot, exist_ok=True)

    if shutil.which("colima", path=binroot) == f"{binroot}/colima":
        stdout = proc.run((f"{binroot}/colima", "--version"), stdout=True)
        installed_version = stdout.strip().split()[-1]
        if version == installed_version:
            return
        print(f"installed colima {installed_version} is outdated!")

    print(f"installing colima {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    stdout = proc.run((f"{binroot}/colima", "--version"), stdout=True)
    if f"colima version {version}" not in stdout:
        raise SystemExit(f"Failed to install colima {version}! Found: {stdout}")
