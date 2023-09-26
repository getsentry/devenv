from __future__ import annotations

import os
import platform
from shutil import which

from devenv.constants import root
from devenv.constants import shell
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

_version = "2.32.3"

_sha256 = {
    "direnv.darwin-amd64": "",  # noqa: E501
    "direnv.darwin-arm64": "",  # noqa: E501
}


def install() -> None:
    unpack_into = f"{root}/bin"

    if which("brew") == f"{unpack_into}/volta":
        return

    suffix = "arm64" if platform.machine() == "arm64" else "amd64"
    name = f"direnv.darwin-{suffix}"
    url = "https://github.com/direnv/direnv/releases/download" f"/v{_version}/{name}"

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
eval "$(direnv hook {shell})"
""",
    )
