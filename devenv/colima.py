from __future__ import annotations

import argparse
import os
import platform
import shutil
from collections.abc import Sequence

from devenv.constants import home
from devenv.lib import proc
from devenv.lib import colima
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import require_repo

module_help = "Colima convenience commands."


@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
    repo_path = context["repo"].path

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start",))

    args = parser.parse_args(argv)

    match args.command:
        case "start":
            colima.start(repo_path)

    return 0


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="colima",
    help=module_help,
)
