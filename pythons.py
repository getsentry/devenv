from __future__ import annotations

import os
import platform

_pythons = {
    "cpython-3.8.16+20221220-aarch64-apple-darwin-install_only.tar.gz": "a71280128ef05311affb8196a8d80571e48952a50093907ffcad33d886d04736",
    # "cpython-3.8.16+20221220-x86_64-apple-darwin-install_only.tar.gz": ""
}


def get_python(python_version: str):
    datetime = "20221220"
    archive = f"cpython-{python_version}+{datetime}-{platform.machine()}-apple-darwin-install_only.tar.gz"
    url = f"https://github.com/indygreg/python-build-standalone/releases/download/{datetime}/{archive}"

    pythons_root = os.path.expanduser("~/.sentry-dev/pythons")
    unpack_into = f"{pythons_root}/{python_version}"

    if not os.path.exists(f"{unpack_into}/python/bin/python3"):
        print(f"Downloading...")
        # TODO: error handling
        resp = urllib.request.urlopen(url)

        # TODO checksum verification

        os.makedirs(unpack_into, exist_ok=True)
        with tarfile.open(fileobj=resp, mode="r:gz") as f:
            f.extractall(path=unpack_into)
