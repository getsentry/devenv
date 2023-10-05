from __future__ import annotations

from typing import Set
from typing import Tuple

from devenv.lib_check.types import checker

tags: Set[str] = set(["test", "pass"])
name = "passing check with no fix"


@checker
def check() -> Tuple[bool, str]:
    return True, ""
