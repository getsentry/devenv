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
