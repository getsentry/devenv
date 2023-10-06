from __future__ import annotations

import os
from subprocess import CalledProcessError
from subprocess import run as subprocess_run
from typing import Any
from typing import Tuple


def run(
    cmd: Tuple[str, ...],
    pathprepend: str = "",
    exit: bool = False,
    **kwargs: Any,
) -> str:
    kwargs["check"] = True
    kwargs["capture_output"] = True

    try:
        env = kwargs.pop("env")
    except KeyError:
        env = os.environ

    if pathprepend:
        env["PATH"] = f"{pathprepend}:{env['PATH']}"

    try:
        proc = subprocess_run(
            cmd,
            env=env,
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

    try:
        env = kwargs.pop("env")
    except KeyError:
        env = os.environ

    if pathprepend:
        env["PATH"] = f"{pathprepend}:{env['PATH']}"

    try:
        subprocess_run(
            cmd,
            env=env,
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
