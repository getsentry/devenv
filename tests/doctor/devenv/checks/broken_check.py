from __future__ import annotations

from typing import Set
from typing import Tuple

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: Set[str] = set(["test", "broken"])
name = "broken check"


@checker
def check() -> Tuple[bool, str]:
    # This is a broken check, it will raise an exception
    a = 1 / 0
    return True, f"{a}"


@fixer
def fix() -> Tuple[bool, str]:
    return True, ""
