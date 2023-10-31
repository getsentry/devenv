from __future__ import annotations

import os
import platform

from devenv.constants import pythons_root
from devenv.lib import archive

_sha256 = {
    "cpython-3.8.16+20221220-aarch64-apple-darwin-install_only.tar.gz": "a71280128ef05311affb8196a8d80571e48952a50093907ffcad33d886d04736",
    "cpython-3.8.16+20221220-x86_64-apple-darwin-install_only.tar.gz": "2916eea6b522d5b755ba2e328527019015597751e0f32c27d73c7d618b61f6b1",
    "cpython-3.8.18+20231002-aarch64-apple-darwin-install_only.tar.gz": "1825b1f7220bc93ff143f2e70b5c6a79c6469e0eeb40824e07a7277f59aabfda",
    "cpython-3.8.18+20231002-x86_64-apple-darwin-install_only.tar.gz": "fcf04532e644644213977242cd724fe5e84c0a5ac92ae038e07f1b01b474fca3",
    "cpython-3.9.18+20231002-aarch64-apple-darwin-install_only.tar.gz": "fdc4054837e37b69798c2ef796222a480bc1f80e8ad3a01a95d0168d8282a007",
    "cpython-3.9.18+20231002-x86_64-apple-darwin-install_only.tar.gz": "82231cb77d4a5c8081a1a1d5b8ae440abe6993514eb77a926c826e9a69a94fb1",
}


def get(python_version: str) -> str:
    unpack_into = f"{pythons_root}/{python_version}"

    if os.path.exists(f"{unpack_into}/python/bin/python3"):
        return f"{unpack_into}/python/bin/python3"

    print(f"Downloading Python {python_version}...")

    datetime = "20221220"
    machine = platform.machine()
    if machine == "arm64":
        machine = "aarch64"
    name = f"cpython-{python_version}+{datetime}-{machine}-apple-darwin-install_only.tar.gz"
    url = (
        "https://github.com/indygreg/python-build-standalone/releases/download/"
        f"{datetime}/{name}"
    )

    archive_file = archive.download(url, _sha256[name])
    archive.unpack(archive_file, unpack_into)

    assert os.path.exists(f"{unpack_into}/python/bin/python3")
    return f"{unpack_into}/python/bin/python3"
