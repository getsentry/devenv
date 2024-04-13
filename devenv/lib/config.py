from __future__ import annotations

import configparser
import functools
import os
import sys
from typing import TypeAlias

from devenv.constants import CI
from devenv.constants import MACHINE
from devenv.context import Path

CONFIG_PROMPTS = {
    "coderoot": "# please enter the root directory you want to work in"
}
# comments are used as input prompts for initial config
DEFAULT_CONFIG: Config = dict(devenv={"coderoot": "~/code"})

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
            val = config.get(section, var, fallback=_val)
            if not CI:
                try:
                    print(CONFIG_PROMPTS.get(var, f"{var}?"))
                    val = input(f" [{val}]: ") or val
                except EOFError:
                    # noninterative, use the defaults
                    print()
            config.set(section, var, val)

    print("Thank you. Saving answers.")

    with open(config_path, "w") as f:
        config.write(f)
    print(f"If you made a mistake, you can edit {config_path}.")


@functools.lru_cache(maxsize=None)
def get_config(path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(path)
    return config


@functools.lru_cache(maxsize=None)
def get_repo(reporoot: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(f"{reporoot}/devenv/config.ini")
    return config


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
