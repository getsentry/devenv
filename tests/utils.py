from __future__ import annotations

import os
import pathlib
from collections.abc import Iterator


def sorted_walk(
    path: pathlib.Path,
) -> Iterator[tuple[str, list[str], list[str]]]:
    for dirpath, dirnames, filenames in os.walk(path):
        yield dirpath, sorted(dirnames), sorted(filenames)
