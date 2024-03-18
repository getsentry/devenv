from __future__ import annotations

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = set(["test", "fail"])
name = "failing check with msg"


@checker
def check() -> tuple[bool, str]:
    return False, "check failed"


@fixer
def fix() -> tuple[bool, str]:
    return False, "fix failed"
