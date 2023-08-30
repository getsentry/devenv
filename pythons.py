from __future__ import annotations

import os
import platform
import tarfile
import urllib.request

_pythons = {
    "cpython-3.8.16+20221220-aarch64-apple-darwin-install_only.tar.gz": "a71280128ef05311affb8196a8d80571e48952a50093907ffcad33d886d04736",  # noqa: E501
    # "cpython-3.8.16+20221220-x86_64-apple-darwin-install_only.tar.gz": ""
}


def get(python_version: str) -> str:
    pythons_root = os.path.expanduser("~/.sentry-dev/pythons")
    unpack_into = f"{pythons_root}/{python_version}"

    if os.path.exists(f"{unpack_into}/python/bin/python3"):
        return f"{unpack_into}/python/bin/python3"

    print(f"Downloading Python {python_version}...")
    # TODO: error handling

    datetime = "20221220"
    archive = (
        f"cpython-{python_version}+{datetime}-{platform.machine()}-apple-darwin-install_only.tar.gz"
    )
    url = (
        "https://github.com/indygreg/python-build-standalone/releases/download/"
        f"{datetime}/{archive}"
    )

    resp = urllib.request.urlopen(url)

    # TODO checksum verification

    os.makedirs(unpack_into, exist_ok=True)
    with tarfile.open(fileobj=resp, mode="r:gz") as f:
        f.extractall(path=unpack_into)

    assert os.path.exists(f"{unpack_into}/python/bin/python3")
    return f"{unpack_into}/python/bin/python3"
