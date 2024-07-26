from __future__ import annotations

import argparse
from collections.abc import Sequence

from devenv.lib import colima
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import require_repo

module_help = "Colima convenience commands."


@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
    repo_path = context["repo"].path  # type: ignore

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("start", "restart", "check", "stop")
    )

    args = parser.parse_args(argv)

    if args.command == "start":
        status = colima.start(repo_path)
        if status == colima.ColimaStatus.UNHEALTHY:
            # https://github.com/abiosoft/colima/issues/949
            print("colima seems unhealthy, we'll try restarting once")
            status = colima.restart(repo_path)
            if status != colima.ColimaStatus.UP:
                return 1
        if status != colima.ColimaStatus.UP:
            return 1
    elif args.command == "restart":
        status = colima.restart(repo_path)
        if status != colima.ColimaStatus.UP:
            return 1
    elif args.command == "check":
        status = colima.check(repo_path)
        if status != colima.ColimaStatus.UP:
            return 1
    elif args.command == "stop":
        status = colima.stop(repo_path)
        if status != colima.ColimaStatus.DOWN:
            return 1

    return 0


module_info = DevModuleInfo(
    action=main, name=__name__, command="colima", help=module_help
)
