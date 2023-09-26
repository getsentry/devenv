from __future__ import annotations

import os
from typing import Set
from typing import Tuple

from devenv.lib import fs
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: Set[str] = set()
name = "foo"


@checker
def check() -> Tuple[bool, str]:
    if os.path.exists(f"{fs.gitroot()}/foo"):
        return True, ""
    return False, f"{fs.gitroot()}/foo doesn't exist"


@fixer
def fix() -> Tuple[bool, str]:
    try:
        proc.run(
            (
                "/bin/bash",
                "-c",
                """
echo blah > foo
""",
            ),
            cwd=fs.gitroot(),
        )
        return True, ""
    except RuntimeError as e:
        return False, f"{e}"
