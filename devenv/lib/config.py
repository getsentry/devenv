from __future__ import annotations

import configparser
import functools
import sys

from devenv.constants import MACHINE


@functools.lru_cache(maxsize=None)
def get_repo(reporoot: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(f"{reporoot}/devenv/config.ini")
    return config


def get_python(reporoot: str, python_version: str) -> tuple[str, str]:
    cfg = get_repo(reporoot)

    # TODO: need to support multiple python versions
    #       because we support multiple virtualenvs
    #       which shouldn't be constrained to the same
    #       python version
    url = cfg["python"][f"{sys.platform}_{MACHINE}"]
    sha256 = cfg["python"][f"{sys.platform}_{MACHINE}_sha256"]
    return url, sha256
