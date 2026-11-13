from __future__ import annotations

import os
import subprocess
from unittest.mock import patch

from devenv import main


def test(tmp_path: str) -> None:
    config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
    coderoot = f"{tmp_path}/code"
    reporoot = f"{coderoot}/repo"

    subprocess.run(("git", "init", reporoot))

    os.makedirs(f"{reporoot}/devenv")
    with open(f"{reporoot}/devenv/config.ini", "w") as f:
        pass
    with open(f"{reporoot}/devenv/sync.py", "w") as f:
        f.write("""
import devenv

def main(context: dict[str, str]) -> int:
    return 123
""")

    # devenv sync should be able to be run from places other than reporoot...
    os.chdir(f"{reporoot}/devenv")

    rc = main.devenv(("/path/to/argv0", "sync"), config_path)
    assert rc == 123

    # ...and leave the cwd unchanged
    assert os.getcwd() == f"{reporoot}/devenv"


def test_mise(tmp_path: str) -> None:
    config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
    reporoot = f"{tmp_path}/code/repo"

    subprocess.run(("git", "init", reporoot))
    with open(f"{reporoot}/mise.toml", "w") as f:
        f.write('[tools]\njq = "1.7.1"\n')

    os.chdir(reporoot)
    with patch("devenv.lib.mise.sync", return_value=0) as sync:
        rc = main.devenv(("/path/to/argv0", "sync"), config_path)

    assert rc == 0
    sync.assert_called_once_with(reporoot)


def test_no_sync_py_or_mise(tmp_path: str) -> None:
    config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
    reporoot = f"{tmp_path}/code/repo"

    subprocess.run(("git", "init", reporoot))

    os.chdir(reporoot)
    rc = main.devenv(("/path/to/argv0", "sync"), config_path)
    assert rc == 1
