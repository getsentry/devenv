from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import tarfile
import tempfile
import urllib.request
from urllib.error import HTTPError

from devenv.constants import cache_root


def atomic_replace(src: str, dest: str) -> None:
    if os.path.dirname(src) != os.path.dirname(dest):
        raise RuntimeError(
            f"cannot atomically move to dest {dest}; it needs to be in the same dir as {src}"
        )
    os.replace(src, dest)


def download(url: str, sha256: str, dest: str = "") -> str:
    if not dest:
        dest = f"{cache_root}/{sha256}"
        os.makedirs(cache_root, exist_ok=True)

    if not os.path.exists(dest):
        try:
            resp = urllib.request.urlopen(url)
        except HTTPError as e:
            raise RuntimeError(f"Error getting {url}: {e}")

        with tempfile.NamedTemporaryFile(
            delete=False, dir=os.path.dirname(dest)
        ) as tmpf:
            shutil.copyfileobj(resp, tmpf)
            tmpf.seek(0)
            checksum = hashlib.sha256()
            buf = tmpf.read(4096)
            while buf:
                checksum.update(buf)
                buf = tmpf.read(4096)

            if not secrets.compare_digest(checksum.hexdigest(), sha256):
                raise RuntimeError(
                    f"checksum mismatch for {url}:\n"
                    f"- got: {checksum.hexdigest()}\n"
                    f"- expected: {sha256}\n"
                )

            atomic_replace(tmpf.name, dest)

    return dest


def unpack(path: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as tarf:
        tarf.extractall(into)
