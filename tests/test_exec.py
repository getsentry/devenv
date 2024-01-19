from __future__ import annotations

import os
import subprocess
from unittest.mock import call
from unittest.mock import patch

config_template = """
[devenv]
coderoot = {coderoot}
"""


def test_python_project(tmp_path: str) -> None:
    home = tmp_path
    coderoot = f"{home}/coderoot"

    config_dir = f"{home}/.config/sentry-devenv"
    os.makedirs(config_dir)
    with open(f"{config_dir}/config.ini", "w") as f:
        f.write(config_template.format(coderoot=coderoot))

    reporoot = f"{coderoot}/repo"
    os.makedirs(f"{reporoot}/.venv")
    with open(f"{reporoot}/config.ini", "w") as f:
        f.write(
            """
[python]
version = 3.10.3
"""
        )

    # first, let's test an outdated venv
    with open(f"{reporoot}/.venv/pyvenv.cfg", "w") as f:
        f.write("version = 3.8.16")

    env = {**os.environ, "HOME": home}
    p = subprocess.run(
        ("devenv", "exec", "env"), cwd=coderoot, env=env, capture_output=True
    )
    assert p.returncode == 0

    # now we should modify cfg and it should amtch

    # devenv exec -- env should also work (argparse)
    # lets also have a test for .venv/bin/foo
