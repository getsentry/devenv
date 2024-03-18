from __future__ import annotations

import contextlib
import os
import pathlib
from collections.abc import Generator


# TODO: replace with contextlib.chdir when we can use python3.11
@contextlib.contextmanager
def chdir(d: str | pathlib.Path) -> Generator[None, None, None]:
    curdir = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(curdir)
