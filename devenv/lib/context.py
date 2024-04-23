from __future__ import annotations

from argparse import Namespace
from typing import TypedDict

from devenv.lib.repository import Repository


class Context(TypedDict):
    config_path: str
    code_root: str
    repo: Repository | None
    args: Namespace
