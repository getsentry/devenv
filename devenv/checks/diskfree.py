from __future__ import annotations

import shutil

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "there should be sufficient host disk space"


@checker
def check() -> tuple[bool, str]:
    disk_total, disk_used, disk_free = shutil.disk_usage("/")
    disk_gib_free = disk_free / (1024**3)

    if disk_gib_free < 10000:
        return (
            False,
            f"You have less than 10 GiB disk free ({disk_gib_free} GiB free). "
            "You might start to encounter various problems when using docker.",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    return (
        False,
        """

We can't autofix this, only you can clean up your own disk.

You might want to try cleaning up unused Docker resources:
   docker system prune -a
""",
    )
