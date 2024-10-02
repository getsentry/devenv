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
        headers = {}
        if url.startswith("https://ghcr.io/v2/homebrew"):
            # downloading homebrew blobs requires auth
            # you can get an anonymous token from https://ghcr.io/token?service=ghcr.io&scope=repository%3Ahomebrew/core/go%3Apull
            # but there's also a special shortcut token QQ==
            # https://github.com/Homebrew/brew/blob/2184406bd8444e4de2626f5b0c749d4d08cb1aed/Library/Homebrew/brew.sh#L993
            headers["Authorization"] = "bearer QQ=="

        req = urllib.request.Request(url, headers=headers)

        retry_sleep = 1.0
        while retries >= 0:
            try:
                resp = urllib.request.urlopen(req)
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
# strips N leading components and optionally adds a new prefix
# (what ends up being stripped should be a common prefix for all entries)
# (/ is always stripped and doesn't count)
def stripN(
    members: Sequence[tarfile.TarInfo], strip_n: int, new_prefix: str = ""
) -> None:
    # we'll use the first member to determine the prefix to strip
    member = members[0]

    end = 0
    if member.path.find("/") == 0:
        # strip leading "/"
        end = 1

    for n in range(strip_n):
        next_at = member.path[end:].find("/")
        if next_at == -1 and n != strip_n - 1:
            # no more '/' but we're not done iterating
            # this means this member isn't nested as deep as
            # N directories we want to strip, which is
            # unexpected
            raise RuntimeError(
                f"""unexpected archive structure:

trying to strip {strip_n} leading components but {member.path} isn't that deep
"""
            )
        end += next_at + 1

    stripped_prefix = member.path[:end]

    for member in members:
        if not member.path.startswith(stripped_prefix):
            raise RuntimeError(
                f"""unexpected archive structure:

{member.path} doesn't have the prefix to be removed ({stripped_prefix})
"""
            )

        if new_prefix:
            member.path = f"{new_prefix}/{member.path[end:]}"
        else:
            member.path = member.path[end:]


def strip1(members: Sequence[tarfile.TarInfo], new_prefix: str = "") -> None:
    stripN(members, 1, new_prefix)


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


def unpack_strip_n(
    path: str, into: str, strip_n: int, new_prefix: str = ""
) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as tarf:
        stripN(tarf.getmembers(), strip_n, new_prefix)
        tarf.extractall(into, filter="tar")
