from __future__ import annotations

import configparser
import functools
import sys

from devenv.constants import MACHINE


@functools.lru_cache(maxsize=None)
def get_config(path: str) -> configparser.ConfigParser:
    """Reads a configuration file from disk, with caching"""
    config = configparser.ConfigParser()
    config.read(path)
    return config


def get_repo(reporoot: str) -> configparser.ConfigParser:
    """Deprecated"""
    from devenv.lib.repository import Repository

    return Repository(reporoot).config()


def get_python(reporoot: str, python_version: str) -> tuple[str, str]:
    cfg = get_repo(reporoot)
    url = cfg[f"python{python_version}"][f"{sys.platform}_{MACHINE}"]
    sha256 = cfg[f"python{python_version}"][f"{sys.platform}_{MACHINE}_sha256"]
    return url, sha256


# only used for sentry/getsentry
def get_python_legacy(reporoot: str, python_version: str) -> tuple[str, str]:
    cfg = get_repo(reporoot)
    url = cfg["python"][f"{sys.platform}_{MACHINE}"]
    sha256 = cfg["python"][f"{sys.platform}_{MACHINE}_sha256"]
    return url, sha256
