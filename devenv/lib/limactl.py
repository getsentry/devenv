from __future__ import annotations

import os
import shutil
import tempfile

from devenv.constants import SYSTEM_MACHINE
from devenv.constants import home
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import proc

# lima >= 2 looks for its guest agents and drivers relative to limactl,
# in ../share/lima and ../libexec/lima
_DATA_DIRS = ("share/lima", "libexec/lima")


def uninstall(binroot: str) -> None:
    prefix = os.path.dirname(binroot)
    for d in (
        f"{home}/.lima",
        *(f"{prefix}/{d}" for d in _DATA_DIRS),
        # lima < 2 kept its templates and guest agents next to limactl
        f"{binroot}/templates",
    ):
        shutil.rmtree(d, ignore_errors=True)

    for fp in (
        f"{binroot}/lima",
        f"{binroot}/limactl",
        f"{binroot}/lima-guestagent.Linux-aarch64",
        f"{binroot}/lima-guestagent.Linux-x86_64",
    ):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _install(url: str, sha256: str, into: str) -> None:
    prefix = os.path.dirname(into)
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        for d in _DATA_DIRS:
            os.makedirs(os.path.dirname(f"{prefix}/{d}"), exist_ok=True)
            os.replace(f"{tmpd}/{d}", f"{prefix}/{d}")
        os.replace(f"{tmpd}/bin/lima", f"{into}/lima")
        os.replace(f"{tmpd}/bin/limactl", f"{into}/limactl")


def install_global() -> None:
    version = "2.2.1"
    cfg = {
        "darwin_x86_64": f"https://github.com/lima-vm/lima/releases/download/v{version}/lima-{version}-Darwin-x86_64.tar.gz",
        "darwin_x86_64_sha256": "6b776e4bc41f358e6ee01fefcc78e2eb26f11635a0fcff632234af77a566c6c4",
        "darwin_arm64": f"https://github.com/lima-vm/lima/releases/download/v{version}/lima-{version}-Darwin-arm64.tar.gz",
        "darwin_arm64_sha256": "9e9eacce88f37e185c346bad73aa6136f738d8cdf8c3bb23cd42b071824bc66e",
    }

    binroot = f"{root}/bin"

    if (
        shutil.which("lima", path=binroot) == f"{binroot}/lima"
        and shutil.which("limactl", path=binroot) == f"{binroot}/limactl"
    ):
        stdout = proc.run((f"{binroot}/limactl", "--version"), stdout=True)
        installed_version = stdout.strip().split()[-1]
        # an interrupted install can leave limactl without its guest agents
        if version == installed_version and all(
            os.path.isdir(f"{root}/{d}") for d in _DATA_DIRS
        ):
            return
        print(f"installed limactl {installed_version} is unexpected!")

    uninstall(binroot)
    _install(cfg[SYSTEM_MACHINE], cfg[f"{SYSTEM_MACHINE}_sha256"], binroot)

    stdout = proc.run((f"{binroot}/limactl", "--version"), stdout=True)
    if f"limactl version {version}" not in stdout:
        raise SystemExit(
            f"Failed to install limactl {version}! Found: {stdout}"
        )


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    install_global()
