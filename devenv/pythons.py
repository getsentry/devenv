from __future__ import annotations

import os

from devenv.constants import pythons_root
from devenv.lib import archive


def get(python_version: str, url: str, sha256: str) -> str:
    unpack_into = f"{pythons_root}/{python_version}"

    if os.path.exists(f"{unpack_into}/python/bin/python3"):
        return f"{unpack_into}/python/bin/python3"

    archive_file = archive.download(url, sha256)
    archive.unpack(archive_file, unpack_into)

    assert os.path.exists(f"{unpack_into}/python/bin/python3")
    return f"{unpack_into}/python/bin/python3"
