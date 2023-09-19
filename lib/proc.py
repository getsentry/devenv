from __future__ import annotations

from subprocess import CalledProcessError
from subprocess import run as subprocess_run
from typing import Tuple
from typing import Union


def run(cmd: Tuple[str, ...], exit: bool = True, **kwargs: Union[str, dict[str, str]]) -> str:
    try:
        proc = subprocess_run(
            cmd,
            check=True,
            capture_output=True,
        )
        return proc.stdout.decode().strip()
    except FileNotFoundError as e:
        # This is reachable if the command isn't found.
        if exit:
            raise SystemExit(f"{e}")
        raise RuntimeError(f"{e}")
    except CalledProcessError as e:
        detail = f"""
`{e.cmd}` returned code {e.returncode}
stdout:
{e.stdout.decode()}
stderr:
{e.stderr.decode()}
"""
        if exit:
            raise SystemExit(detail)
        raise RuntimeError(detail)
