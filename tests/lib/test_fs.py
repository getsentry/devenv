from __future__ import annotations

import contextlib
import os
import pathlib
import shutil
import subprocess

import pytest

from devenv.lib.fs import gitroot
from devenv.lib.fs import write_script


def test_gitroot(tmp_path: pathlib.Path) -> None:
    subprocess.run(("git", "init", f"{tmp_path}"))

    with contextlib.chdir(tmp_path):
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
        with contextlib.chdir(tmp_path):
            gitroot()


def test_write_script(tmp_path: pathlib.Path) -> None:
    binroot = f"{tmp_path}"
    shim = "shim"
    bad = "$(echo hi)"

    write_script(
        f"{binroot}/{shim}",
        """#!/bin/sh
export PATH="{binroot}/node-env/bin:${{PATH}}"
export NPM_CONFIG_PREFIX="{binroot}/node-env"
very={bad}
exec "{binroot}/node-env/bin/{shim}" "$@"
""",
        shell_escape={"binroot": binroot, "shim": shim, "bad": bad},
    )

    with open(f"{binroot}/{shim}") as f:
        assert shutil.which(shim, path=binroot) == f"{binroot}/{shim}"
        text = f.read()
        assert (
            text
            == f"""#!/bin/sh
export PATH="{binroot}/node-env/bin:${{PATH}}"
export NPM_CONFIG_PREFIX="{binroot}/node-env"
very='$(echo hi)'
exec "{binroot}/node-env/bin/{shim}" "$@"
"""
        )
