from __future__ import annotations

from subprocess import CalledProcessError
from subprocess import run as subprocess_run
from typing import Tuple
from typing import Union


def run(
    cmd: Tuple[str, ...], exit: bool = False, **kwargs: Union[str, bool, dict[str, str]]
) -> str:
    kwargs["check"] = True
    kwargs["capture_output"] = True
    try:
        proc = subprocess_run(
            cmd,
            **kwargs,  # type: ignore
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
    cmd: Tuple[str, ...], exit: bool = False, **kwargs: Union[str, bool, dict[str, str]]
) -> None:
    kwargs["check"] = True
    kwargs["capture_output"] = False
    try:
        subprocess_run(
            cmd,
            **kwargs,  # type: ignore
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
