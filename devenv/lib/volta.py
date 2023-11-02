from __future__ import annotations

import os
import platform
from shutil import which

from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.constants import VOLTA_HOME
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

_version = "1.1.1"
_sha256 = {
    f"volta-{_version}-macos-aarch64.tar.gz": "013d419550525fa6a212c2693798f9e2e65737e887e3604b08bc15a6be737e01",
    f"volta-{_version}-macos.tar.gz": "778ccaa943de8729d91e9df02a2767b470d97e8d5551faf6d89978db6f5f3c64",
    f"volta-{_version}-linux.tar.gz": "ab14e5d50ef836f8f43b56323cfbe7ba95a004bad05450b453c5b06a0b433d7b",
}


class UnexpectedPlatformError(Exception):
    pass


def install_volta(unpack_into: str) -> None:
    system = platform.system()
    if system == "Linux":
        if platform.machine() == "x86_64":
            name = f"volta-{_version}-linux.tar.gz"
        else:
            proc.run(("brew", "install", "volta"), exit=True)
            proc.run(
                ("sh", "-c", f"ln -sfn {homebrew_bin}/volta* {unpack_into}/"),
                exit=True,
            )
            return
    elif system == "Darwin":
        suffix = "-aarch64" if platform.machine() == "arm64" else ""
        name = f"volta-{_version}-macos{suffix}.tar.gz"
    else:
        raise UnexpectedPlatformError(f"Unexpected OS: {platform.platform()}")

    url = (
        "https://github.com/volta-cli/volta/releases/download/"
        f"v{_version}/{name}"
    )

    archive_file = archive.download(url, _sha256[name])
    archive.unpack(archive_file, unpack_into)


def install() -> None:
    unpack_into = f"{root}/bin"

    if (
        which("volta", path=unpack_into) == f"{unpack_into}/volta"
        and which("node", path=f"{VOLTA_HOME}/bin") == f"{VOLTA_HOME}/bin/node"
    ):
        return

    install_volta(unpack_into)

    # executing volta -v will populate the VOLTA_HOME directory
    # with node/npm/yarn shims
    proc.run((f"{root}/bin/volta-migrate",))
    version = proc.run((f"{root}/bin/volta", "-v"), stdout=True)
    assert version == _version, (version, _version)
    if not os.path.exists(f"{VOLTA_HOME}/bin/node"):
        raise SystemExit("Failed to install volta!")

    fs.idempotent_add(
        fs.shellrc(),
        f"""
export VOLTA_HOME={VOLTA_HOME}
export PATH="{VOLTA_HOME}/bin:$PATH"
""",
    )
