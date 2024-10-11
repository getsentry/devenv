from __future__ import annotations

import importlib
import os.path
from configparser import ConfigParser

from devenv import constants
from devenv.lib.config import get_config
from devenv.lib.fs import ensure_binroot


class Repository:
    def __init__(self, root: str) -> None:
        self.path = root
        self.name = os.path.basename(root)

        # .devenv may exist but not be config_path because .devenv/bin is hard-coded, so we check for config.ini
        if os.path.exists(f"{root}/.devenv/config.ini"):
            self.config_path = f"{root}/.devenv"
        # devenv _may_ exist but not be config_path because devenv has a devenv module, so we check for config.ini
        elif os.path.exists(f"{root}/devenv/config.ini"):
            self.config_path = f"{root}/devenv"
        else:
            # new default config_path is .devenv
            self.config_path = f"{root}/.devenv"

    def __repr__(self) -> str:
        return f"Repository: {self.name}"

    def ensure_binroot(self) -> None:
        ensure_binroot(self.path)

    def config(self) -> ConfigParser:
        return get_config(f"{self.config_path}/config.ini")

    def check_minimum_version(self) -> None:
        version = importlib.metadata.version("sentry-devenv")

        cfg = self.config()
        try:
            minimum_version = cfg["devenv"]["minimum_version"]
        except KeyError:
            return

        parsed_version = tuple(map(int, version.split(".")))
        parsed_minimum_version = tuple(map(int, minimum_version.split(".")))

        if parsed_version < parsed_minimum_version:
            raise SystemExit(
                f"""
Your devenv version ({version}) doesn't meet the
minimum version ({minimum_version}) defined in the repo config.

Run the following to update your global devenv to the minimum,
and use it to run this repo's sync.

{constants.root}/bin/devenv update {minimum_version}
{constants.root}/bin/devenv sync
"""
            )
