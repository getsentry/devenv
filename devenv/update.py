from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from devenv import constants
from devenv.lib import brew
from devenv.lib import colima
from devenv.lib import direnv
from devenv.lib import docker
from devenv.lib import limactl
from devenv.lib import proc
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo

module_help = "Updates global devenv and tools."


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", type=str, nargs="?")
    parser.add_argument(
        "--post-update", action="store_true", help="Internal, do not use."
    )

    args = parser.parse_args(argv)

    # This is so that people don't have to run update twice.
    if args.post_update:
        # Mirror this in bootstrap.py.
        print(
            f"""\
Updating global tools (at {constants.root}/bin).
"""
        )
        os.makedirs(f"{constants.root}/bin", exist_ok=True)
        brew.install()
        docker.install_global()
        direnv.install()
        colima.install_global()
        limactl.install_global()
        return 0

    is_global_devenv = sys.executable.startswith(
        f"{constants.root}/venv/bin/python"
    )

    global_devenv_exists = os.path.exists(f"{constants.root}/bin/devenv")

    # even if we aren't the global devenv, we want to update
    # the global devenv (but only if it exists) out of convenience
    if is_global_devenv or global_devenv_exists:
        if args.version is None:
            version = "sentry-devenv"
        else:
            version = "sentry-devenv=={args.version}"

        proc.run(
            (f"{constants.root}/venv/bin/pip", "install", "-U", version),
            env={
                # better than cli flag (who knows if it'll break in the future)
                "PIP_DISABLE_PIP_VERSION_CHECK": "1"
            },
        )

        print(
            f"""\

Global devenv at {constants.root}/bin/devenv updated.
"""
        )

    proc.run((sys.executable, "-P", "-m", "devenv", "update", "--post-update"))

    if not is_global_devenv:
        print(
            """\
To update the local devenv, you'll want to run `devenv sync`.
"""
        )

    return 0


module_info = DevModuleInfo(
    action=main, name=__name__, command="update", help=module_help
)
