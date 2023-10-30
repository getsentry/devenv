from __future__ import annotations

import os
from subprocess import CalledProcessError
from subprocess import run as subprocess_run
from typing import Any
from typing import Tuple

from devenv.constants import home
from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.constants import shell_path
from devenv.constants import VOLTA_HOME

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


def run(
    cmd: Tuple[str, ...],
    stream_output: bool = False,
    pathprepend: str = "",
    exit: bool = False,
    **kwargs: Any,
) -> str:
    kwargs["check"] = True
    kwargs["capture_output"] = not stream_output

    if not kwargs.get("env"):
        kwargs["env"] = base_env
    else:
        kwargs["env"] = {**base_env, **kwargs["env"]}

    if pathprepend:
        kwargs["env"]["PATH"] = f"{pathprepend}:{kwargs['env']['PATH']}"

    try:
        proc = subprocess_run(cmd, **kwargs)
        return "" if proc.stdout is None else proc.stdout.decode().strip()  # type: ignore
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if not exit:
            raise RuntimeError(f"{e}")
        raise SystemExit(f"{e}")
    except CalledProcessError as e:
        detail = f"""
`{' '.join(e.cmd)}` returned code {e.returncode}
"""
        if not stream_output:
            detail += f"""
stdout:
{"" if e.stdout is None else e.stdout.decode()}
stderr:
{"" if e.stderr is None else e.stderr.decode()}
"""
        if not exit:
            raise RuntimeError(detail)
        raise SystemExit(detail)
