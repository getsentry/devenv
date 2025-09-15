from __future__ import annotations

import os
import shutil
import tempfile
import stat
from zipfile import ZipFile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/bun.zip")
        os.makedirs(into, exist_ok=True)
        with ZipFile(archive_file, mode="r") as zipf:
            bun_member = next(m for m in zipf.filelist if m.filename.endswith("/bun"))
            zipf.extract(bun_member, path=f"{tmpd}")

            target = f"{into}/bun"
            os.replace(f"{tmpd}/{bun_member.filename}", target)
            mode = os.stat(target).st_mode
            os.chmod(target, mode | stat.S_IEXEC)

            os.symlink(target, f"{into}/bunx")
            os.chmod(f"{into}/bunx", mode | stat.S_IEXEC)


def uninstall(binroot: str) -> None:
    for fp in (f"{binroot}/bun", f"{binroot}/bunx"):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _version(binpath: str) -> str:
    return proc.run((binpath, "--version"), stdout=True).strip()


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)
    binpath = f"{binroot}/bun"

    if shutil.which("bun", path=binroot) == binpath:
        installed_version = _version(binpath)
        if version == installed_version:
            return
        print(f"installed bun {installed_version} is unexpected!")

    print(f"installing bun {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    installed_version = _version(binpath)
    if version != installed_version:
        raise SystemExit("Failed to install bun {version}!")
