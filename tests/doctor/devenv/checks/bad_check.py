from __future__ import annotations

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = set(["test", "bad"])
name = "bad check"


@checker  # type: ignore # intended error
def check() -> tuple[str, str]:
    return "True", ""


@fixer
def fix() -> tuple[bool, str]:
    return True, ""
