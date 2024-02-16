from __future__ import annotations

import os
import subprocess

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

    reporoot = f"{coderoot}/sentry"

    os.makedirs(f"{reporoot}/.venv/bin")
    os.symlink("/bin/sh", f"{reporoot}/.venv/bin/venv-executable")

    os.makedirs(f"{reporoot}/devenv")
    with open(f"{reporoot}/devenv/config.ini", "w") as f:
        f.write(
            """
[python]
version = 3.10.3
"""
        )
    subprocess.run(("git", "init", "--quiet", "--bare", reporoot))

    # first, let's test an outdated venv
    with open(f"{reporoot}/.venv/pyvenv.cfg", "w") as f:
        f.write("version = 3.8.16")

    env = {**os.environ, "HOME": home, "CI": "1"}

    p = subprocess.run(
        ("devenv", "exec", "command", "-v", "venv-executable"),
        cwd=reporoot,
        env=env,
        capture_output=True,
    )
    assert (
        b"WARN: venv doesn't exist or isn't up to date. You should create it with devenv sync."
        in p.stdout
    )
    # since the venv wasn't in good standing it shouldn't have been
    # used for the exec
    assert b"venv-executable: command not found" in p.stderr
    assert p.returncode != 0

    with open(f"{reporoot}/.venv/pyvenv.cfg", "w") as f:
        f.write("version = 3.10.3")

    p = subprocess.run(
        ("devenv", "exec", "venv-executable", "-c", "echo great success"),
        cwd=reporoot,
        env=env,
        capture_output=True,
    )
    assert p.stdout == b"great success\n"

    p = subprocess.run(
        # -- should also work
        ("devenv", "exec", "--", "venv-executable", "-c", "echo great success"),
        cwd=reporoot,
        env=env,
        capture_output=True,
    )
    assert p.stdout == b"great success\n"
