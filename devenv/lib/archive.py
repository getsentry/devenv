from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import tarfile
import tempfile
import time
import urllib.request
from collections.abc import Sequence
from urllib.error import HTTPError

from devenv.constants import home


def atomic_replace(src: str, dest: str) -> None:
    if os.path.dirname(src) != os.path.dirname(dest):
        raise RuntimeError(
            f"cannot atomically move to dest {dest}; it needs to be in the same dir as {src}"
        )
    os.replace(src, dest)


def download(
    url: str,
    sha256: str,
    dest: str = "",
    retries: int = 3,
    retry_exp: float = 2.0,
) -> str:
    if retries < 0:
        raise ValueError("Retries cannot be negative")

    if not dest:
        cache_root = f"{home}/.cache/sentry-devenv"
        dest = f"{cache_root}/{sha256}"
        os.makedirs(cache_root, exist_ok=True)

    if not os.path.exists(dest):
        retry_sleep = 1.0
        while retries >= 0:
            try:
                resp = urllib.request.urlopen(url)
                break
            except HTTPError as e:
                if retries == 0:
                    raise RuntimeError(f"Error getting {url}: {e}")
                print(f"Error getting {url} ({retries} retries left): {e}")

            time.sleep(retry_sleep)
            retries -= 1
            retry_sleep *= retry_exp

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
                raise RuntimeError(
                    f"checksum mismatch for {url}:\n"
                    f"- got: {checksum.hexdigest()}\n"
                    f"- expected: {sha256}\n"
                )

            atomic_replace(tmpf.name, dest)

    return dest


# mutates members!
# strips the leading component (/ is always stripped and doesn't count)
# and optionally replaces with a new prefix
def strip1(members: Sequence[tarfile.TarInfo], new_prefix: str = "") -> None:
    for member in members:
        i = member.path.find("/")
        if i == -1:
            continue
        elif i == 0:
            i = member.path[1:].find("/") + 1
            if i == 0:
                continue

        member.path = member.path[i + 1 :]  # noqa: E203

        if new_prefix:
            member.path = f"{new_prefix}/{member.path}"


def unpack(
    path: str,
    into: str,
    perform_strip1: bool = False,
    strip1_new_prefix: str = "",
) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as tarf:
        if perform_strip1:
            strip1(tarf.getmembers(), strip1_new_prefix)
        tarf.extractall(into, filter="tar")
