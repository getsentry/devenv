from __future__ import annotations

import os
from collections.abc import Sequence

from devenv import constants
from devenv.lib import config
from devenv.lib import fs
from devenv.lib import venv
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    # TODO: optional repo
    repo = context["repo"]
    reporoot = repo.path  # type: ignore
    repo_config = config.get_repo(reporoot)

    print(f"removing {reporoot}/.devenv")
    # fs.rmtree(f"{reporoot}/.devenv")

    # as much as possible, things are contained to .devenv
    # exceptions to this are node_modules and python venvs
    # (the locations of which can be configured)

    fs.rmtree(f"{reporoot}/node_modules")

    # TODO if isdir then rmtree

    for v in venv.get_all(reporoot):
        venv_dir = v[0]
        print(f"removing venv at {venv_dir}")
        # shutil.rmtree(venv_dir)

    # --colima
    print("removing global colima state")
    # shutil.rmtree(f"{constants.home}/.colima")
    # shutil.rmtree(f"{constants.home}/.lima")

    # --everything
    print("uninstalling brew")
    # shutil.rmtree(constants.homebrew_bin)
    # shutil.rmtree(constants.homebrew_repo)

    # --uninstall
    print(f"uninstalling devenv (removing {constants.root})")
    # shutil.rmtree(constants.root, ignore_errors=True)

    return 0


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="delete",
    help="Deletes the repo's environment.",
)
