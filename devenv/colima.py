from __future__ import annotations

import argparse
from collections.abc import Sequence

from devenv.lib import colima
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo

module_help = "Colima convenience commands."


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("start", "restart", "check", "stop")
    )

    args = parser.parse_args(argv)

    # TODO: in addition to returning 1 we should print colima logs
    #       (and/or send to sentry)

    if args.command == "start":
        status = colima.start()
        if status == colima.ColimaStatus.UNHEALTHY:
            # https://github.com/abiosoft/colima/issues/949
            print("colima seems unhealthy, we'll try restarting once")
            status = colima.restart()
            if status != colima.ColimaStatus.UP:
                return 1
        if status != colima.ColimaStatus.UP:
            return 1
    elif args.command == "restart":
        status = colima.restart()
        if status != colima.ColimaStatus.UP:
            return 1
    elif args.command == "check":
        status = colima.check()
        if status != colima.ColimaStatus.UP:
            return 1
    elif args.command == "stop":
        status = colima.stop()
        if status != colima.ColimaStatus.DOWN:
            return 1

    return 0


module_info = DevModuleInfo(
    action=main, name=__name__, command="colima", help=module_help
)
