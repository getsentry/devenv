from __future__ import annotations

import os
import pathlib
from collections.abc import Iterator


def sorted_os_walk(
    path: pathlib.Path,
) -> Iterator[tuple[str, list[str], list[str]]]:
    for a, b, c in sorted(os.walk(path)):
        b.sort()
        c.sort()
        yield a, b, c
