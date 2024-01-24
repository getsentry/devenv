from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import run as subprocess_run
from typing import Literal
from typing import overload

from devenv import constants
from devenv.constants import home
from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.constants import shell_path
from devenv.constants import user_environ
from devenv.constants import VOLTA_HOME

base_path = f"{root}/bin:{VOLTA_HOME}/bin:{homebrew_bin}:{user_environ['PATH']}"
base_env = {
    "PATH": base_path,
    "HOME": home,
    "SHELL": shell_path,
    "VOLTA_HOME": VOLTA_HOME,
}


def quote(cmd: tuple[str, ...]) -> str:
    """convert a command to bash-compatible form"""
    from pipes import quote

    return " ".join(quote(arg) for arg in cmd)


def xtrace(cmd: tuple[str, ...]) -> None:
    """Print a commandline, similar to how xtrace does."""

    teal = "\033[36m"
    reset = "\033[m"
    bold = "\033[1m"

    print(f"+ {teal}${reset} {bold}{quote(cmd)}{reset}")


@overload
def run(
    cmd: tuple[str, ...],
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
    cmd: tuple[str, ...],
    *,
    pathprepend: str = "",
    exit: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    stdout: Literal[True],
) -> str:
    ...


def run(
    cmd: tuple[str, ...],
    *,
    pathprepend: str = "",
    exit: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
    stdout: bool = False,
) -> str | None:
    _stdout = PIPE if stdout else None
    del stdout

    if env is None:
        env = {}
    env = {**constants.user_environ, **base_env, **env}

    if pathprepend:
        env["PATH"] = f"{pathprepend}:{env['PATH']}"

    if constants.DEBUG:
        xtrace(cmd)
    try:
        proc = subprocess_run(cmd, check=True, stdout=_stdout, cwd=cwd, env=env)
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if exit:
            raise SystemExit(f"{e}") from None
        else:
            raise RuntimeError(f"{e}") from None
    except CalledProcessError as e:
        detail = f"Command `{quote(e.cmd)}` failed! (code {e.returncode})"
        if _stdout:
            detail += f"""
stdout:
{"" if e.stdout is None else e.stdout.decode()}
"""
        if exit:
            raise SystemExit(detail) from None
        else:
            raise RuntimeError(detail) from None
    else:
        if _stdout:
            return proc.stdout.decode().strip()
        return None
