from __future__ import annotations

import os
from subprocess import CalledProcessError
from subprocess import run as subprocess_run
from typing import Any
from typing import Tuple

from devenv.constants import home
from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.constants import VOLTA_HOME

# We don't want to use os.environ (to stay isolated from user's own env which could be broken).
# User provides paths as needed via pathprepend.
base_path = (
    f"{root}/bin:{VOLTA_HOME}/bin:{homebrew_bin}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)
base_env = {
    "PATH": base_path,
    "HOME": home,
    # CI doesn't have TERM, but tput (which is called by sentry make) wants it, and it can't
    # be dumb, so xterm is used to make it happy.
    "TERM": os.environ.get("TERM") or "xterm",
    "SHELL": os.environ["SHELL"],
}


def run(
    cmd: Tuple[str, ...],
    pathprepend: str = "",
    exit: bool = False,
    **kwargs: Any,
) -> str:
    kwargs["check"] = True
    kwargs["capture_output"] = True

    if not kwargs.get("env"):
        kwargs["env"] = base_env
    else:
        kwargs["env"] = {**base_env, **kwargs["env"]}

    if pathprepend:
        kwargs["env"]["PATH"] = f"{pathprepend}:{kwargs['env']['PATH']}"

    try:
        proc = subprocess_run(
            cmd,
            **kwargs,
        )
        return proc.stdout.decode().strip()  # type: ignore
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if not exit:
            raise RuntimeError(f"{e}")
        raise SystemExit(f"{e}")
    except CalledProcessError as e:
        detail = f"""
`{' '.join(e.cmd)}` returned code {e.returncode}
stdout:
{e.stdout.decode()}
stderr:
{e.stderr.decode()}
"""
        if not exit:
            raise RuntimeError(detail)
        raise SystemExit(detail)


def run_stream_output(
    cmd: Tuple[str, ...],
    pathprepend: str = "",
    exit: bool = False,
    **kwargs: Any,
) -> None:
    kwargs["check"] = True
    kwargs["capture_output"] = False

    kwargs.setdefault("env", base_env)
    if pathprepend:
        kwargs["env"]["PATH"] = f"{pathprepend}:{kwargs['env']['PATH']}"

    try:
        subprocess_run(
            cmd,
            **kwargs,
        )
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if not exit:
            raise RuntimeError(f"{e}")
        raise SystemExit(f"{e}")
    except CalledProcessError as e:
        detail = f"""
`{' '.join(e.cmd)}` returned code {e.returncode}
"""
        if not exit:
            raise RuntimeError(detail)
        raise SystemExit(detail)
