from __future__ import annotations

import os
from pathlib import Path
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import run as subprocess_run
from typing import Literal
from typing import overload

from devenv.constants import home
from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.constants import shell_path
from devenv.constants import VOLTA_HOME

Command = tuple[str, ...]

# We don't want to use os.environ (to stay isolated from user's own env which could be broken).
# User provides paths as needed via pathprepend.
base_path = f"{VOLTA_HOME}/bin:{homebrew_bin}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:{root}/bin"
base_env = {
    "PATH": base_path,
    "HOME": home,
    # CI doesn't have TERM, but tput (which is called by sentry make) wants it,
    # and it can't be 'dumb' (why?), so xterm is used to make it happy.
    "TERM": os.environ.get("TERM") or "xterm-256color",
    "SHELL": shell_path,
}


@overload
def run(
    cmd: Command,
    *,
    pathprepend: str = "",
    exit: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    stdout: Literal[False] = False,
) -> None:
    ...


@overload
def run(
    cmd: Command,
    *,
    pathprepend: str = "",
    exit: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    stdout: Literal[True],
) -> str:
    ...


def run(
    cmd: Command,
    *,
    pathprepend: str = "",
    exit: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    stdout: bool = False,
) -> str | None:
    _stdout = PIPE if stdout else None
    del stdout

    if not env:
        env = base_env
    else:
        env = {**base_env, **env}

    if pathprepend:
        env["PATH"] = f"{pathprepend}:{env['PATH']}"

    try:
        proc = subprocess_run(cmd, check=True, stdout=_stdout, cwd=cwd)
        if _stdout:
            return proc.stdout.decode().strip()
        else:
            return None
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if exit:
            raise SystemExit(f"{e}")
        else:
            raise RuntimeError(f"{e}")
    except CalledProcessError as e:
        detail = f"""
`{' '.join(e.cmd)}` returned code {e.returncode}
"""
        if _stdout:
            detail += f"""
stdout:
{"" if e.stdout is None else e.stdout.decode()}
"""
        if exit:
            raise SystemExit(detail)
        else:
            raise RuntimeError(detail)
