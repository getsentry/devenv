from __future__ import annotations

import os
import sys

from devenv import constants
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "colima ssh credentials should only be owner rw"


def only_owner_can_rw(path: str) -> bool:
    mode = os.stat(path).st_mode & 0o777
    return mode == 0o400 or mode == 0o600


@checker
def check() -> tuple[bool, str]:
    lima_ssh_creds = f"{constants.home}/.colima/_lima/_config/user"

    if not only_owner_can_rw(lima_ssh_creds):
        return (
            False,
            f"Permission bits on {lima_ssh_creds} are too permissive; colima startup will hang on waiting for ssh",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    lima_ssh_creds = f"{constants.home}/.colima/_lima/_config/user"

    os.chmod(lima_ssh_creds, 0o600)

    try:
        proc.run((sys.executable, "-P", "-m", "devenv", "colima", "start"))
    except RuntimeError as e:
        return (
            False,
            f"""Failed to start colima: {e}


========================================================================================
You might want to share the last 100 lines of colima's stderr log in #discuss-dev-infra:

`tail -n 100 ~/.colima/_lima/colima/ha.stderr.log`
""",
        )

    return True, ""
