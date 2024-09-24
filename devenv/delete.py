from __future__ import annotations

import argparse
from collections.abc import Sequence

from devenv import constants
from devenv.lib import fs
from devenv.lib import venv
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--colima", action="store_true", help="Removes colima's global state."
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Completely uninstalls devenv from the system.",
    )
    args = parser.parse_args(argv)

    repo = context["repo"]
    if repo is None:
        print(
            "note: you aren't in a repo, so no repo-local dev environments will be deleted"
        )
    else:
        reporoot = repo.path

        fs.rmtree(f"{reporoot}/.devenv")

        # as much as possible, things are contained to .devenv
        # exceptions to this are node_modules and python venvs
        # (the locations of which can be configured)

        fs.rmtree(f"{reporoot}/node_modules")

        for v in venv.get_all(reporoot):
            venv_dir = v[0]
            fs.rmtree(venv_dir)

    if args.colima:
        print("removing global colima state")
        fs.rmtree(f"{constants.home}/.colima")
        fs.rmtree(f"{constants.home}/.lima")

    if args.uninstall:
        # We leave brew untouched.
        print("uninstalling devenv")
        fs.rmtree(constants.root)

    return 0


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="delete",
    help="Deletes the repo's environment if inside a repo. Optionally perform even more drastic deletions.",
)
