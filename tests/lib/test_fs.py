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
    subprocess.run(("git", "init", f"{tmp_path}"))

    with chdir(tmp_path):
        assert os.path.samefile(tmp_path, gitroot())
        assert os.path.isdir(f"{gitroot()}/.git")


def test_gitroot_cd(tmp_path: pathlib.Path) -> None:
    subprocess.run(("git", "init", f"{tmp_path}"))
    os.mkdir(f"{tmp_path}/foo")

    _gitroot = gitroot(cd=f"{tmp_path}/foo")
    assert os.path.samefile(f"{tmp_path}", _gitroot)
    assert os.path.isdir(f"{_gitroot}/.git")
