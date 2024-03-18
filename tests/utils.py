from __future__ import annotations

import contextlib
import importlib
import os
import pathlib
from collections.abc import Generator
from types import ModuleType


# TODO: replace with contextlib.chdir when we can use python3.11
@contextlib.contextmanager
def chdir(d: str | pathlib.Path) -> Generator[None, None, None]:
    curdir = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(curdir)


def import_module_from_file(fp: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, fp)
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore
    return module
