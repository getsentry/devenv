from __future__ import annotations

import os
import platform
from shutil import which

from devenv.constants import bin_root
from devenv.constants import MACHINE
from devenv.lib import archive

_version = "0.6.2"
_sha256 = {
    "colima-Darwin-arm64": "add68719cc2a8e29be331177534db19812f9f79621425878cd88f890ca0db476",
    "colima-Darwin-x86_64": "43ef3fc80a8347d51b8ec1706f9caf8863bd8727a6f7532caf1ccd20497d8485",
    "colima-Linux-aarch64": "a04dbdfff0d913502b948ed1025d0d12485780493de24750b867c06a6325b5d5",
    "colima-Linux-x86_64": "58e1a13fb0f693a6b28c2d935856e3f4bab6f0ab93f6bf4c860b5d59791ed04f",
}


class UnexpectedPlatformError(Exception):
    pass


def build_name() -> str | None:
    system = platform.system()
    if system == "Linux":
        if MACHINE == "arm64":
            return "colima-Linux-aarch64"
        return f"colima-Linux-{MACHINE}"
    elif system == "Darwin":
        return f"colima-Darwin-{MACHINE}"
    else:
        raise UnexpectedPlatformError(f"Unexpected OS: {platform.platform()}")


def download(name: str, into: str) -> None:
    url = (
        "https://github.com/abiosoft/colima/releases/download/"
        f"v{_version}/{name}"
    )

    archive.download(url, _sha256[name], dest=f"{into}/colima")
    os.chmod(f"{into}/colima", 0o775)


def _install(into: str) -> None:
    name = build_name()
    if name is None:
        return
    download(name, into)


def install() -> None:
    if which("colima", path=bin_root) == f"{bin_root}/colima":
        return

    _install(bin_root)

    if not os.path.exists(f"{bin_root}/colima"):
        raise SystemExit("Failed to install colima!")
