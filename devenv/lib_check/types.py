from __future__ import annotations

from collections.abc import Callable
from typing import Tuple


def checker(
    f: Callable[[], Tuple[bool, str]]
) -> Callable[[], Tuple[bool, str]]:
    return f


def fixer(f: Callable[[], Tuple[bool, str]]) -> Callable[[], Tuple[bool, str]]:
    return f
