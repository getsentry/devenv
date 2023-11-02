from __future__ import annotations

from typing import Set
from typing import Tuple

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: Set[str] = set(["test", "bad"])
name = "bad fix"


@checker
def check() -> Tuple[bool, str]:
    return True, ""


@fixer  # type: ignore  # intended error
def fix() -> Tuple[str, str]:
    return "True", ""
