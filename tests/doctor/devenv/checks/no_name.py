from __future__ import annotations

from devenv.lib_check.types import checker

tags: set[str] = set()


@checker
def check() -> tuple[bool, str]:
    return True, ""
