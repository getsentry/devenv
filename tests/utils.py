from __future__ import annotations

import os
import pathlib
from collections.abc import Iterator


# slightly modded from os.walk
def sorted_walk(
    top: pathlib.Path, topdown: bool = True, followlinks: bool = False
) -> Iterator[tuple[str, list[str], list[str]]]:
    names = sorted(os.listdir(top))

    dirs: list[str] = []
    nondirs: list[str] = []

    for name in names:
        if os.path.isdir(os.path.join(top, name)):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield f"{top}", sorted(dirs), sorted(nondirs)
    for name in dirs:
        new_path = top / name
        if followlinks or not os.path.islink(new_path):
            for x in sorted_walk(new_path, topdown, followlinks):
                yield x
    if not topdown:
        yield f"{top}", sorted(dirs), sorted(nondirs)
