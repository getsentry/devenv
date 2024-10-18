from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence

from devenv import constants
from devenv.lib import proc
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo

module_help = "Updates global devenv."


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    if not sys.executable.startswith(f"{constants.root}/venv/bin/python"):
        rc = subprocess.call((f"{constants.root}/bin/devenv", *sys.argv[1:]))
        if rc != 0:
            print(
                """
failed to update devenv!
"""
            )
            return rc

        print(
            f"""
The global devenv at {constants.root}/bin/devenv has been updated.

You used a local (at {sys.executable}) devenv to do this,
which has *not* been updated.

If sync wasn't working before, try using global devenv to run it now:

{constants.root}/bin/devenv sync
"""
        )
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("version", type=str, nargs="?")

    args = parser.parse_args(argv)

    if args.version is None:
        proc.run(
            (
                f"{constants.root}/venv/bin/pip",
                "install",
                "-U",
                "sentry-devenv",
            ),
            env={
                # better than cli flag (who knows if it'll break in the future)
                "PIP_DISABLE_PIP_VERSION_CHECK": "1"
            },
        )
    else:
        proc.run(
            (
                f"{constants.root}/venv/bin/pip",
                "install",
                f"sentry-devenv=={args.version}",
            ),
            env={
                # better than cli flag (who knows if it'll break in the future)
                "PIP_DISABLE_PIP_VERSION_CHECK": "1"
            },
        )

    return 0


module_info = DevModuleInfo(
    action=main, name=__name__, command="update", help=module_help
)
