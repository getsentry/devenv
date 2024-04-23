from __future__ import annotations

import importlib.util
import os
from collections.abc import Sequence

from devenv.lib.context import Context
from devenv.lib.modules import command
from devenv.lib.modules import ModuleDef
from devenv.lib.modules import require_repo


@command("sync", "Resyncs the current project")
@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
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
    }
    return module.main(context_compat)  # type: ignore


module_info = ModuleDef(
    module_name=__name__, name="sync", help="Resyncs the current project"
)
