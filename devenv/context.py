from __future__ import annotations

from typing import NotRequired
from typing import TypeAlias
from typing import TypedDict

Path: TypeAlias = str


class Context(TypedDict):
    config_path: Path
    code_root: Path
    repo_root: NotRequired[Path]
    repo_name: NotRequired[Path]
