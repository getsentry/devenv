from __future__ import annotations

import contextlib
import os
import pathlib
import subprocess
from collections.abc import Generator

from devenv.lib.fs import gitroot


# TODO: replace with contextlib.chdir when we can use python3.11
@contextlib.contextmanager
def chdir(d: str | pathlib.Path) -> Generator[None, None, None]:
    curdir = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(curdir)


def test_gitroot(tmp_path: pathlib.Path) -> None:
    with chdir(tmp_path):
        subprocess.run(("git", "init"))

        _gitroot = (
            subprocess.run(
                ("git", "rev-parse", "--show-toplevel"), capture_output=True
            )
            .stdout.decode()
            .strip()
        )

        assert gitroot() == _gitroot
        assert os.path.isdir(f"{gitroot()}/.git")


def test_gitroot_cd(tmp_path: pathlib.Path) -> None:
    with chdir(tmp_path):
        subprocess.run(("git", "init"))

    (tmp_path / "nested").mkdir()

    with chdir(f"{tmp_path}/nested"):
        subprocess.run(("git", "init"))

        _gitroot = (
            subprocess.run(
                ("git", "rev-parse", "--show-toplevel"), capture_output=True
            )
            .stdout.decode()
            .strip()
        )

        assert gitroot() == _gitroot
        assert os.path.isdir(f"{gitroot()}/.git")
