from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import tarfile
import urllib.request
from urllib.error import HTTPError

from devenv.constants import cache_root


def download(url: str, sha256: str, dest: str = "") -> str:
    if not dest:
        dest = f"{cache_root}/{sha256}"
        os.makedirs(cache_root, exist_ok=True)

    if not os.path.exists(dest):
        try:
            resp = urllib.request.urlopen(url)
        except HTTPError as e:
            raise RuntimeError(f"Error getting {url}: {e}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(resp, f)

    checksum = hashlib.sha256()
    with open(dest, mode="rb") as f:
        bts = f.read(4096)
        while bts:
            checksum.update(bts)
            bts = f.read(4096)

    if not secrets.compare_digest(checksum.hexdigest(), sha256):
        os.remove(dest)
        raise RuntimeError(
            f"checksum mismatch for {url}:\n"
            f"- got: {checksum.hexdigest()}\n"
            f"- expected: {sha256}\n"
        )

    return dest


def unpack(path: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as tarf:
        tarf.extractall(into)
