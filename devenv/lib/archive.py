from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import tarfile
import tempfile
import urllib.request
from urllib.error import HTTPError

from typing import Sequence, Iterator

from devenv.constants import home


def atomic_replace(src: str, dest: str) -> None:
    if os.path.dirname(src) != os.path.dirname(dest):
        raise RuntimeError(
            f"cannot atomically move to dest {dest}; it needs to be in the same dir as {src}"
        )
    os.replace(src, dest)


def download(url: str, sha256: str, dest: str = "", retries: int = 3) -> str:
    if not dest:
        cache_root = f"{home}/.cache/sentry-devenv"
        dest = f"{cache_root}/{sha256}"
        os.makedirs(cache_root, exist_ok=True)

    if not os.path.exists(dest):
        try:
            resp = urllib.request.urlopen(url)
        except HTTPError as e:
            # TODO retries
            raise RuntimeError(f"Error getting {url}: {e}")

        dest_dir = os.path.dirname(dest)
        os.makedirs(dest_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False, dir=dest_dir) as tmpf:
            shutil.copyfileobj(resp, tmpf)
            tmpf.seek(0)
            checksum = hashlib.sha256()
            buf = tmpf.read(4096)
            while buf:
                checksum.update(buf)
                buf = tmpf.read(4096)

            if not secrets.compare_digest(checksum.hexdigest(), sha256):
                # TODO retries
                raise RuntimeError(
                    f"checksum mismatch for {url}:\n"
                    f"- got: {checksum.hexdigest()}\n"
                    f"- expected: {sha256}\n"
                )

            atomic_replace(tmpf.name, dest)

    return dest


def strip_components(members: Sequence[tarfile.TarInfo], n: int, new_prefix: str) -> Iterator[tarfile.TarInfo]:
    for member in members:
        i = -1
        for _ in range(n):
            i = member.path.find("/")
            if i == -1:
                pass
            elif i == 0:
                i = member.path[1:].find("/") + 1

            member.path = member.path[i + 1 :]

        if new_prefix:
            member.path = f"{new_prefix}/{member.path}"

        yield member


def unpack(
    path: str,
    into: str,
    strip_components_n: int = 0,
    strip_components_new_prefix: str = "",
) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as tarf:
        members = strip_components(
            tarf.getmembers(), strip_components_n, strip_components_new_prefix
        )
        tarf.extractall(
            into,
            members=members,
        )
