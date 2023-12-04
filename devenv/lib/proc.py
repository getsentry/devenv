from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import run as subprocess_run
from subprocess import STDOUT

from devenv import constants
from devenv.constants import home
from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.constants import shell_path
from devenv.constants import VOLTA_HOME

base_path = f"{VOLTA_HOME}/bin:{homebrew_bin}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:{root}/bin"
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


def run(
    cmd: tuple[str, ...],
    *,
    pathprepend: str = "",
    exit: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
) -> str:
    if env is None:
        env = {}
    env = {**constants.user_environ, **base_env, **env}

    if pathprepend:
        env["PATH"] = f"{pathprepend}:{env['PATH']}"

    if constants.DEBUG:
        xtrace(cmd)
    try:
        proc = subprocess_run(
            cmd, check=True, stdout=PIPE, stderr=STDOUT, cwd=cwd, env=env
        )
        if proc.stdout:
            return proc.stdout.decode().strip()
        else:
            return ""
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if exit:
            raise SystemExit(f"{e}") from None
        else:
            raise RuntimeError(f"{e}") from None
    except CalledProcessError as e:
        detail = f"""
Command `{quote(e.cmd)}` failed! (code {e.returncode})"

stdout:
{"" if e.stdout is None else e.stdout.decode()}
"""
        if exit:
            raise SystemExit(detail) from None
        else:
            raise RuntimeError(detail) from None
