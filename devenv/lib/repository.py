from __future__ import annotations

import os.path
from configparser import ConfigParser

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
