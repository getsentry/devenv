from __future__ import annotations

import configparser
import functools
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from devenv.constants import CI
from devenv.constants import MACHINE


@dataclass(frozen=True)
class ConfigOpt:
    name: str
    prompt: str
    formatter: Callable[[str], str] | None = None
    default: Callable[[], str] = lambda: ""


def _path_formatter(path: str) -> str:
    return os.path.normpath(os.path.expanduser(path))


CONFIG_OPTS = {
    "coderoot": ConfigOpt(
        "coderoot",
        "# please enter the root directory you want to work in",
        _path_formatter,
        lambda: "~/code",
    )
}

Config: TypeAlias = "dict[str, dict[str, str | None]]"


def initialize_config(config_path: str, defaults: Config) -> None:
    config = configparser.ConfigParser()

    # Read existing configuration, if present
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    for section, values in defaults.items():
        if not config.has_section(section):
            config.add_section(section)

        for var, _val in values.items():
            opts = CONFIG_OPTS.get(var)

            val: str = config.get(
                section,
                var,
                fallback=(opts.default() if opts else "")
                if _val is None
                else _val,
            )

            if not CI:
                try:
                    if opts:
                        print(opts.prompt)
                    else:
                        print(f"{var}?")

                    val = input(f" [{val}]: ") or val
                except EOFError:
                    # noninterative, use the defaults
                    print()
            config.set(
                section,
                var,
                opts.formatter(val) if opts and opts.formatter else val,
            )

    print("Thank you. Saving answers.")

    with open(config_path, "w") as f:
        config.write(f)
    print(f"If you made a mistake, you can edit {config_path}.")


def read_config(path: str) -> configparser.ConfigParser:
    """Reads a configuration file from disk, with no caching"""
    config = configparser.ConfigParser()
    config.read(path)
    return config


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
