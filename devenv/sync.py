from __future__ import annotations

import argparse
import importlib.util
import os
from collections.abc import Sequence

from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import require_repo


@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    # also support devenv sync -v in addition to devenv -v sync
    verbose = context["verbose"] or args.verbose

    repo = context["repo"]
    assert repo is not None

    if not os.path.exists(f"{repo.config_path}/sync.py"):
        print(f"{repo.config_path}/sync.py not found!")
        return 1

    spec = importlib.util.spec_from_file_location(
        "sync", f"{repo.config_path}/sync.py"
    )

    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    context_compat = {
        "reporoot": repo.path,
        "repo": repo.name,
        "coderoot": context.get("code_root"),
        "verbose": verbose,
    }
    return module.main(context_compat)  # type: ignore


module_info = DevModuleInfo(
    action=main, name=__name__, command="sync", help="Resyncs the environment."
)
