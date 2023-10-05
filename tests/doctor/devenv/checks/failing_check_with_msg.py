from __future__ import annotations

from typing import Set
from typing import Tuple

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: Set[str] = set(["test", "fail"])
name = "failing check with msg"


@checker
def check() -> Tuple[bool, str]:
    return False, "check failed"


@fixer
def fix() -> Tuple[bool, str]:
    return False, "fix failed"
