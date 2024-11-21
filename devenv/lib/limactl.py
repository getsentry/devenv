from __future__ import annotations

import os
import shutil
import tempfile

from devenv.constants import home
from devenv.constants import root
from devenv.constants import SYSTEM_MACHINE
from devenv.lib import archive
from devenv.lib import proc


def uninstall(binroot: str) -> None:
    for d in (f"{home}/.lima",):
        shutil.rmtree(d, ignore_errors=True)

    for fp in (
        f"{binroot}/lima",
        f"{binroot}/limactl",
        f"{binroot}/lima-guestagent.Linux-aarch64",
        f"{binroot}/lima-guestagent.Linux-x86_64",
        f"{binroot}/templates/default.yaml",
    ):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")

        # the archive from homebrew has a lima/version prefix
        if url.startswith("https://ghcr.io/v2/homebrew"):
            archive.unpack_strip_n(archive_file, tmpd, n=2)
        else:
            archive.unpack(archive_file, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/bin/lima", f"{into}/lima")
        os.replace(f"{tmpd}/bin/limactl", f"{into}/limactl")
        os.replace(
            f"{tmpd}/share/lima/lima-guestagent.Linux-aarch64",
            f"{into}/lima-guestagent.Linux-aarch64",
        )
        os.replace(
            f"{tmpd}/share/lima/lima-guestagent.Linux-x86_64",
            f"{into}/lima-guestagent.Linux-x86_64",
        )
        os.makedirs(f"{into}/templates", exist_ok=True)
        os.replace(
            f"{tmpd}/share/lima/templates/default.yaml",
            f"{into}/templates/default.yaml",
        )


def install_global() -> None:
    version = "0.23.2"
    cfg = {
        # upstream github releases aren't built for macOS 14, so we use homebrew binaries
        "darwin_x86_64": "https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:c2e69a572afa3a3cf895643ede988c87dc0622dae4aebc539d5564d820845841",
        "darwin_x86_64_sha256": "c2e69a572afa3a3cf895643ede988c87dc0622dae4aebc539d5564d820845841",
        "darwin_arm64": "https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:be8e2b92961eca2f862f1a994dbef367e86d36705a705ebfa16d21c7f1366c35",
        "darwin_arm64_sha256": "be8e2b92961eca2f862f1a994dbef367e86d36705a705ebfa16d21c7f1366c35",
        # on linux we use github releases since most people are probably not using
        # linuxbrew and the go binary in homebrew links to homebrew's ld.so
        "linux_x86_64": "https://github.com/lima-vm/lima/releases/download/v0.23.2/lima-0.23.2-Linux-x86_64.tar.gz",
        "linux_x86_64_sha256": "5d0034316096e3f3ceedcb2e1dcac7c7d380e26defb59a5894eaf1e3265b191e",
    }

    binroot = f"{root}/bin"

    if (
        shutil.which("lima", path=binroot) == f"{binroot}/lima"
        and shutil.which("limactl", path=binroot) == f"{binroot}/limactl"
    ):
        stdout = proc.run((f"{binroot}/limactl", "--version"), stdout=True)
        installed_version = stdout.strip().split()[-1]
        if version == installed_version:
            return
        print(f"installed limactl {installed_version} is outdated!")

    uninstall(binroot)
    _install(cfg[SYSTEM_MACHINE], cfg[f"{SYSTEM_MACHINE}_sha256"], binroot)

    stdout = proc.run((f"{binroot}/limactl", "--version"), stdout=True)
    if f"limactl version {version}" not in stdout:
        raise SystemExit(
            f"Failed to install limactl {version}! Found: {stdout}"
        )


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    install_global()
