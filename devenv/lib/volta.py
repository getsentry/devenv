from __future__ import annotations

import os
import platform
from shutil import which

from devenv.constants import root
from devenv.constants import VOLTA_HOME
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

_version = "1.1.1"
_sha256 = {
    f"volta-{_version}-macos-aarch64.tar.gz": "013d419550525fa6a212c2693798f9e2e65737e887e3604b08bc15a6be737e01",  # noqa: E501
    f"volta-{_version}-macos.tar.gz": "778ccaa943de8729d91e9df02a2767b470d97e8d5551faf6d89978db6f5f3c64",  # noqa: E501
}


def install() -> None:
    unpack_into = f"{root}/bin"

    if (
        which("volta") == f"{unpack_into}/volta"
        and which("node") == f"{VOLTA_HOME}/bin/node"
    ):
        return

    suffix = "-aarch64" if platform.machine() == "arm64" else ""
    name = f"volta-{_version}-macos{suffix}.tar.gz"
    url = (
        "https://github.com/volta-cli/volta/releases/download/"
        f"v{_version}/{name}"
    )

    archive_file = archive.download(url, _sha256[name])
    archive.unpack(archive_file, unpack_into)

    # executing volta -v will populate the VOLTA_HOME directory
    # with node/npm/yarn shims
    proc.run((f"{root}/bin/volta", "-v"), env={"VOLTA_HOME": VOLTA_HOME})
    if not os.path.exists(f"{VOLTA_HOME}/bin/node"):
        raise SystemExit("Failed to install volta!")

    fs.idempotent_add(
        fs.shellrc(),
        f"""
export VOLTA_HOME={VOLTA_HOME}
export PATH="{VOLTA_HOME}/bin:$PATH"
""",
    )
