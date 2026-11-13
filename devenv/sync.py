from __future__ import annotations

import contextlib
import importlib.util
import os
from collections.abc import Sequence

from devenv.constants import troubleshooting_help
from devenv.lib import mise
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import require_repo


@require_repo
def main(context: Context, argv: Sequence[str] | None = None) -> int:
    repo = context["repo"]
    assert repo is not None

    sync_py = f"{repo.config_path}/sync.py"
    if os.path.exists(sync_py):
        use_mise = False
    elif mise.configured(repo.path):
        use_mise = True
    else:
        print(f"{sync_py} not found!")
        return 1

    repo.check_minimum_version()

    if use_mise:
        rc = mise.sync(repo.path)
    else:
        rc = _run_sync_py(context, sync_py)

    if rc != 0:
        print(troubleshooting_help)
    return rc


def _run_sync_py(context: Context, sync_py: str) -> int:
    repo = context["repo"]
    assert repo is not None

    spec = importlib.util.spec_from_file_location("sync", sync_py)

    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    context_compat = {
        "reporoot": repo.path,
        "repo": repo.name,
        "coderoot": context.get("code_root"),
    }

    with contextlib.chdir(repo.path):
        return module.main(context_compat)  # type: ignore


module_info = DevModuleInfo(
    action=main, name=__name__, command="sync", help="Resyncs the environment."
)
