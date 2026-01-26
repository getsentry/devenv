from __future__ import annotations

from devenv.lib import colima
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "colima VM has sufficient disk space"


@checker
def check() -> tuple[bool, str]:
    status = colima.check()
    if status != colima.ColimaStatus.UP:
        return True, ""

    try:
        output = proc.run(
            ("colima", "exec", "--", "df", "--output=pcent", "/"), stdout=True
        )
    except RuntimeError:
        return True, ""

    lines = output.strip().split("\n")
    if len(lines) >= 2:
        percent_str = lines[1].strip().rstrip("%")
        try:
            used_percent = int(percent_str)
            if used_percent > 90:
                return (
                    False,
                    f"Colima VM disk is {used_percent}% full (less than 10% free space).\n"
                    "Consider resizing the disk or cleaning up unused Docker images/containers.",
                )
        except ValueError:
            pass

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    return (
        False,
        """
First you should try to cleanup unused Docker resources:
   docker system prune -a

Failing that, you can resize the Colima VM's disk:

1. Stop colima:
   colima stop

2. Install qemu:
   brew install qemu

2. Restart colima, resizing to a larger disk (e.g., 200GB):
   colima start --disk 200
""",
    )
