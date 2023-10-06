from __future__ import annotations

from typing import Set
from typing import Tuple

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: Set[str] = set(["test", "pass"])
name = "passing check"


@checker
def check() -> Tuple[bool, str]:
    return True, ""


@fixer
def fix() -> Tuple[bool, str]:
    return True, ""
