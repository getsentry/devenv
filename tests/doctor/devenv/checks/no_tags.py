from __future__ import annotations

from devenv.lib_check.types import checker

name = "no tags"


@checker
def check() -> tuple[bool, str]:
    return True, ""
