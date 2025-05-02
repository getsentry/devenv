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
    version = "1.0.3"
    cfg = {
        # upstream github releases aren't built for macOS 14, so for now
        # we use homebrew binaries from https://formulae.brew.sh/api/formula/lima.json
        # unfortunately there's no way to view previous versions of a formula
        # so if we ever need to upgrade to a specific non-latest version we'll
        # have to build it ourselves
        # sonoma
        "darwin_x86_64": "https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:f675abee28d0f10f335f7a04dc6ad3de12434c83c2f0f32c913061204c137a94",
        "darwin_x86_64_sha256": "f675abee28d0f10f335f7a04dc6ad3de12434c83c2f0f32c913061204c137a94",
        # arm64_sonoma
        "darwin_arm64": "https://ghcr.io/v2/homebrew/core/lima/blobs/sha256:8aeb0a3b7295f0c3e0c2a7a92a798a44397936e5bb732db825aee6da5e762d7a",
        "darwin_arm64_sha256": "8aeb0a3b7295f0c3e0c2a7a92a798a44397936e5bb732db825aee6da5e762d7a",
        # on linux we use github releases since most people are probably not using
        # linuxbrew and the go binary in homebrew links to linuxbrew's ld.so
        "linux_x86_64": f"https://github.com/lima-vm/lima/releases/download/v{version}/lima-{version}-Linux-x86_64.tar.gz",
        "linux_x86_64_sha256": "b109cac29569a4aacab01c588f922ea6c7e2ef06ce9260bbc4c382e475bc3b98",
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
