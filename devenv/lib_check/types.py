from __future__ import annotations

from collections.abc import Callable


def checker(
    f: Callable[[], tuple[bool, str]]
) -> Callable[[], tuple[bool, str]]:
    return f


def fixer(f: Callable[[], tuple[bool, str]]) -> Callable[[], tuple[bool, str]]:
    return f
