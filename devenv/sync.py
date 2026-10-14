from __future__ import annotations

import contextlib
import importlib.util
import os
from collections.abc import Sequence

from devenv.constants import troubleshooting_help
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import require_repo


@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
    repo = context["repo"]
    assert repo is not None

    if not os.path.exists(f"{repo.config_path}/sync.py"):
        print(f"{repo.config_path}/sync.py not found!")
        return 1

    repo.check_minimum_version()

    spec = importlib.util.spec_from_file_location(
        "sync", f"{repo.config_path}/sync.py"
    )

    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    context_compat = {
        "reporoot": repo.path,
        "repo": repo.name,
        "coderoot": context.get("code_root"),
    }

    with contextlib.chdir(repo.path):
        rc = module.main(context_compat)
        if rc != 0:
            print(troubleshooting_help)
        return rc  # type: ignore


module_info = DevModuleInfo(
    action=main, name=__name__, command="sync", help="Resyncs the environment."
)
