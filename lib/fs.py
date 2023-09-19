from __future__ import annotations

import os
from functools import cache

from devenv.lib import proc


@cache
def gitroot(cd: str = "") -> str:
    from os.path import normpath, join

    if not cd:
        cd = os.getcwd()

    stdout = proc.run(("git", "-C", cd, "rev-parse", "--show-cdup"), exit=True)
    return normpath(join(cd, stdout))


def idempotent_add(filepath: str, text: str) -> None:
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(f"\n{text}\n")
            return
    with open(filepath, "r+") as f:
        contents = f.read()
        if text not in contents:
            f.write(f"\n{text}\n")
