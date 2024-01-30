from __future__ import annotations

import configparser
import functools


@functools.lru_cache(maxsize=None)
def repo_config(reporoot: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(f"{reporoot}/devenv/config.ini")
    return config
