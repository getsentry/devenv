from __future__ import annotations

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = set(["test", "bad"])
name = "bad fix"


@checker
def check() -> tuple[bool, str]:
    return True, ""


@fixer  # type: ignore  # intended error
def fix() -> tuple[str, str]:
    return "True", ""
