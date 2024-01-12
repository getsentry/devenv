from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

from devenv.lib.fs import gitroot
from tests.utils import chdir


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


def test_no_gitroot(tmp_path: pathlib.Path) -> None:
    with pytest.raises(RuntimeError):
        with chdir(tmp_path):
            gitroot()
