from __future__ import annotations

import importlib.util
import os
from collections.abc import Sequence
from typing import Dict


help = "Resyncs the environment."


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> int:
    reporoot = context["reporoot"]

    if not os.path.exists(f"{reporoot}/devenv/sync.py"):
        print(f"{reporoot}/devenv/sync.py not found!")
        return 1

    spec = importlib.util.spec_from_file_location(
        "sync", f"{reporoot}/devenv/sync.py"
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return module.main(context)  # type: ignore
