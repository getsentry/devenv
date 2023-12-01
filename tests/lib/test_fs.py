from __future__ import annotations

import contextlib
import os
import subprocess
from collections.abc import Generator

from devenv.lib.fs import gitroot

_gitroot = (
    subprocess.run(("git", "rev-parse", "--show-toplevel"), capture_output=True)
    .stdout.decode()
    .strip()
)


# TODO: replace with contextlib.chdir when we can use python3.11
@contextlib.contextmanager
def chdir(d: str) -> Generator[None, None, None]:
    curdir = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(curdir)


def test_gitroot() -> None:
    assert gitroot() == _gitroot
    assert os.path.isdir(f"{gitroot()}/.git")


def test_gitroot_cd() -> None:
    with chdir(f"{_gitroot}/tests"):
        assert gitroot() == _gitroot
        assert os.path.isdir(f"{gitroot()}/.git")
