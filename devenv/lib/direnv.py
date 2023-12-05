from __future__ import annotations

import os
import shutil
import sys

from devenv.constants import MACHINE
from devenv.constants import root
from devenv.constants import shell
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

_version = "2.32.3"

_sha256 = {
    "direnv.darwin-amd64": "6ff42606edb38ffce5e1a3f4a1c69401e42a7c49b8bdc4ddafd705bc770bd15c",
    "direnv.darwin-arm64": "dd053025ecae958118b3db2292721464e68da4fb319b80905a4cebba5ba9f069",
    "direnv.linux-amd64": "c0443e4600e4b93ec253e663fff18b5fb490cc555b1fc72f0ab22beaa2bb9810",
    "direnv.linux-arm64": "785684d2b228bcb1e3977545f0215966a5124cdffcf7a01a90cf1bf1aee71483",
}


def install() -> None:
    direnv_path = f"{root}/bin/direnv"

    if shutil.which("direnv") == direnv_path:
        return

    machine = "arm64" if MACHINE == "arm64" else "amd64"
    name = f"direnv.{sys.platform}-{machine}"
    url = (
        "https://github.com/direnv/direnv/releases/download"
        f"/v{_version}/{name}"
    )

    archive.download(url, _sha256[name], dest=direnv_path)
    os.chmod(direnv_path, 0o775)

    version = proc.run((direnv_path, "version"), stdout=True)
    assert version == _version, (version, _version)

    fs.idempotent_add(
        fs.shellrc(),
        f"""
eval "$(direnv hook {shell})"
""",
    )
