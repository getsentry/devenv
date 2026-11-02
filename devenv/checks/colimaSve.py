from __future__ import annotations

from devenv.lib import colima
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin", "colima"}
name = "colima's VM shouldn't report SVE support on CPUs without SVE"


@checker
def check() -> tuple[bool, str]:
    try:
        misreported = colima.vm_misreports_sve()
    except RuntimeError:
        # colima isn't running, which another check covers
        return True, ""

    if misreported:
        return (
            False,
            "colima's VM kernel reports SVE2, but this CPU has no SVE. "
            "Programs that use it crash with 'Illegal instruction'.",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    # upgrades the VM's kernel and restarts colima to boot it
    status = colima.start(restart=True)
    if status != colima.ColimaStatus.UP:
        return False, "colima is unhealthy"

    # start only warns if it couldn't upgrade the kernel
    try:
        misreported = colima.vm_misreports_sve()
    except RuntimeError as e:
        return False, f"{e}"
    if misreported:
        return False, "colima's VM still misreports SVE, see above"

    return True, ""
