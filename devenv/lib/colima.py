from __future__ import annotations

import os
import shutil
import tempfile

from devenv.constants import bin_root
from devenv.constants import home
from devenv.lib import archive
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive.download(url, sha256, dest=f"{tmpd}/colima")
        os.replace(f"{tmpd}/colima", f"{into}/colima")
        os.chmod(f"{into}/colima", 0o775)


def uninstall() -> None:
    for d in (f"{home}/.lima",):
        shutil.rmtree(d, ignore_errors=True)

    for f in (f"{bin_root}/colima",):
        if os.path.exists(f):
            os.remove(f)


def install(version: str, url: str, sha256: str) -> None:
    if shutil.which("colima", path=bin_root) == f"{bin_root}/colima":
        stdout = proc.run((f"{bin_root}/colima", "--version"), stdout=True)
        installed_version = stdout.strip().split()[-1]
        if version == installed_version:
            return
        print(f"installed colima {installed_version} is outdated!")

    print(f"installing colima {version}...")
    uninstall()
    _install(url, sha256, bin_root)

    stdout = proc.run((f"{bin_root}/colima", "--version"), stdout=True)
    if f"colima version {version}" not in stdout:
        raise SystemExit("Failed to install colima {version}!")
