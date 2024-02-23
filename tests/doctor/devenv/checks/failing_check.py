from __future__ import annotations

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = set(["test", "fail"])
name = "failing check"


@checker
def check() -> tuple[bool, str]:
    return False, ""


@fixer
def fix() -> tuple[bool, str]:
    return False, ""
