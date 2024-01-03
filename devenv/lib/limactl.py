from __future__ import annotations

import os
import platform
import tempfile
from shutil import which

from devenv.constants import bin_root
from devenv.constants import MACHINE
from devenv.lib import archive

_version = "0.19.1"
_sha256 = {
    f"lima-{_version}-Darwin-arm64.tar.gz": "0dfcf3a39782baf1c2ea43cf026f8df0321c671d914c105fbb78de507aa8bda4",
    f"lima-{_version}-Darwin-x86_64.tar.gz": "ac8827479f66ef1b288b31f164b22f6433faa14c44ce5bbebe09e6e913582479",
    f"lima-{_version}-Linux-aarch64.tar.gz": "c55e57ddbefd9988d0f3676bb873bcc6e0f7b3c3d47a1f07599ee151c5198d96",
    f"lima-{_version}-Linux-x86_64.tar.gz": "7d18b1716aae14bf98d6ea93a703e8877b0c3142f7ba2e87401d47d5d0fe3ff1",
}


class UnexpectedPlatformError(Exception):
    pass


def build_name() -> str | None:
    system = platform.system()
    if system == "Linux":
        if MACHINE == "arm64":
            return f"lima-{_version}-{system}-aarch64.tar.gz"
        return f"lima-{_version}-{system}-{MACHINE}.tar.gz"
    elif system == "Darwin":
        return f"lima-{_version}-{system}-{MACHINE}.tar.gz"
    else:
        raise UnexpectedPlatformError(f"Unexpected OS: {platform.platform()}")


def download_and_unpack_archive(name: str, into: str) -> None:
    url = (
        "https://github.com/lima-vm/lima/releases/download/"
        f"v{_version}/{name}"
    )

    archive_file = archive.download(url, _sha256[name], dest=f"{into}/{name}")
    archive.unpack(archive_file, into)


def _install(into: str) -> None:
    name = build_name()
    if name is None:
        return

    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        download_and_unpack_archive(name, tmpd)

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


def install() -> None:
    # this needs to be better
    if (
        which("lima", path=bin_root) == f"{bin_root}/lima"
        and which("limactl", path=bin_root) == f"{bin_root}/limactl"
    ):
        return

    _install(bin_root)

    if not os.path.exists(f"{bin_root}/lima") or not os.path.exists(
        f"{bin_root}/limactl"
    ):
        raise SystemExit("Failed to install colima!")
