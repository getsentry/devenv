from __future__ import annotations

import os

from devenv.lib import fs
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = set()
name = "foo"


@checker
def check() -> tuple[bool, str]:
    if os.path.exists(f"{fs.gitroot()}/foo"):
        return True, ""
    return False, f"{fs.gitroot()}/foo doesn't exist"


@fixer
def fix() -> tuple[bool, str]:
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
