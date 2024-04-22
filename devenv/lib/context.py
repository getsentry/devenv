from __future__ import annotations

from argparse import Namespace
from typing import TypeAlias
from typing import TypedDict

from devenv.lib.repository import Repository

Path: TypeAlias = str


class Context(TypedDict):
    config_path: Path
    code_root: Path
    repo: Repository | None
    args: Namespace
