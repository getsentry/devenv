from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import tarfile
import tempfile
import urllib.request
from urllib.error import HTTPError


def download(url: str, sha256: str) -> str:
    try:
        resp = urllib.request.urlopen(url)
    except HTTPError as e:
        raise RuntimeError(f"Error getting {url}: {e}")

    fd, dest = tempfile.mkstemp()
    with open(fd, "wb") as f:
        shutil.copyfileobj(resp, f)

    checksum = hashlib.sha256()
    with open(fd, mode="rb", closefd=True) as f:
        bts = f.read(4096)
        while bts:
            checksum.update(bts)
            bts = f.read(4096)

    if not secrets.compare_digest(checksum.hexdigest(), sha256):
        raise RuntimeError(
            f"checksum mismatch for {url}:\n"
            f"- got: {checksum.hexdigest()}\n"
            f"- expected: {sha256}\n",
        )

    return dest


def unpack(path: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as f:
        f.extractall(path=into)
    os.remove(path)
