from __future__ import annotations

import argparse
import os
import platform
import shutil
from collections.abc import Sequence

from devenv.constants import home
from devenv.lib import proc
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import require_repo


def start(reporoot: str) -> None:
    if not os.getenv("CI"):
        macos_version = platform.mac_ver()[0]
        macos_major_version = int(macos_version.split(".")[0])
        if macos_major_version < 14:
            raise SystemExit(
                f"macos >= 14 is required to use colima, found {macos_version}"
            )

    if not shutil.which("docker"):
        raise SystemExit(
            "docker executable not found, you might want to run devenv sync"
        )

    colima = f"{reporoot}/.devenv/bin/colima"
    if not os.path.isfile(colima):
        raise SystemExit(
            f"colima not found at {colima}, you might want to run devenv sync"
        )

    cpus = os.cpu_count()
    if cpus is None:
        raise SystemExit("failed to determine cpu count")

    # SC_PAGE_SIZE is POSIX 2008
    # SC_PHYS_PAGES is a linux addition but also supported by more recent MacOS versions
    SC_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
    SC_PHYS_PAGES = os.sysconf("SC_PHYS_PAGES")
    if SC_PAGE_SIZE == -1 or SC_PHYS_PAGES == -1:
        raise SystemExit("failed to determine memsize_bytes")
    memsize_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")

    args = ["--cpu", f"{cpus//2}", "--memory", f"{memsize_bytes//(2*1024**3)}"]
    if platform.machine() == "arm64":
        args = [*args, "--vm-type=vz", "--vz-rosetta", "--mount-type=virtiofs"]

    proc.run(
        (
            # we share the "default" machine across repositories
            colima,
            "start",
            "--verbose",
            # ideally we keep ~ ro and reporoot rw, but currently the "default" vm
            # is shared across repositories, so for ease of use we'll let home rw
            f"--mount=/var/folders:w,/private/tmp/colima:w,{home}:w",
            *args,
        ),
        pathprepend=f"{reporoot}/.devenv/bin",
    )

    proc.run(("docker", "context", "use", "colima"))


@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)

    repo = context["repo"]
    # repo.path
    return 0


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="colima",
    help="Colima convenience commands.",
)
