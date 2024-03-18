from __future__ import annotations

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = set(["test", "broken"])
name = "broken fix"


@checker
def check() -> tuple[bool, str]:
    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    # This is a broken fix, it will raise an exception
    a = 1 / 0
    return True, f"{a}"
