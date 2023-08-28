from __future__ import annotations

from functools import cache


@cache
def gitroot(cd: str) -> str:
    from os.path import normpath, join
    from subprocess import CalledProcessError, run

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
