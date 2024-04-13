from __future__ import annotations

import importlib.util
import os
from collections.abc import Sequence

from devenv.context import Context

help = "Resyncs the environment."


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    repo_root = context["repo_root"]

    if not os.path.exists(f"{repo_root}/devenv/sync.py"):
        print(f"{repo_root}/devenv/sync.py not found!")
        return 1

    spec = importlib.util.spec_from_file_location(
        "sync", f"{repo_root}/devenv/sync.py"
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    context_compat = {
        **context,
        "reporoot": context.get("repo_root"),
        "repo": context.get("repo_name"),
        "coderoot": context.get("code_root"),
    }
    return module.main(context_compat)  # type: ignore
