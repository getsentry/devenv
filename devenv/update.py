from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from devenv import constants
from devenv.lib import proc
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo

module_help = "Updates global devenv."


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    if not sys.executable.startswith(f"{constants.root}/venv/bin/python"):
        raise SystemExit(
            f"""
update is only applicable to the global devenv.
This one is using: {sys.executable}

To update the global devenv, run `{constants.root}/bin/devenv update`.

To update a repo-local devenv, run `devenv sync`.

(It's the responsibility of devenv/sync.py and devenv/config.ini to
maintain a virtualenv with a devenv version for that particular repository.)
"""
        )

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
