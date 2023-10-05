from __future__ import annotations

from typing import Tuple

from devenv.lib_check.types import checker

name = "no tags"


@checker
def check() -> Tuple[bool, str]:
    return True, ""
