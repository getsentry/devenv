from __future__ import annotations

import os
from functools import cache
from subprocess import CalledProcessError
from subprocess import run


@cache
def gitroot(cd: str = "") -> str:
    from os.path import normpath, join

    if not cd:
        cd = os.getcwd()

    try:
        proc = run(
            ("git", "-C", cd, "rev-parse", "--show-cdup"),
            check=True,
            capture_output=True,
        )
        root = normpath(join(cd, proc.stdout.decode().strip()))
    except CalledProcessError as e:
        raise SystemExit(f"git failed: {e.stderr}")
    return root
