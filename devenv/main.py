from __future__ import annotations

import argparse
import configparser
import os
import subprocess
import time
from collections.abc import Sequence
from typing import NoReturn

from typing_extensions import TypeAlias

from devenv import bootstrap
from devenv import doctor
from devenv import pin_gha
from devenv import sync
from devenv.constants import config_root
from devenv.constants import root
from devenv.constants import src_root
from devenv.lib.fs import gitroot

# comments are used as input prompts for initial config
Config: TypeAlias = "dict[str, dict[str, str | None]]"
DEFAULT_CONFIG = dict(
    devenv={
        "# Where do you usually run `git clone`?": None,
        "coderoot": "~/repo",
    }
)


def self_update(force: bool = False) -> int:
    fn = f"{root}/last-update"
    if not os.path.exists(fn):
        open(fn, mode="a").close()

    if not force:
        update_age = time.time() - os.path.getmtime(fn)
        if update_age < 82800:  # 23 hours
            return 0

    print("Updating devenv tool...")
    # We don't have any dependencies. If we do end up adding some,
    # we should vendor to avoid pip calls to keep it lean and simple.
    rc = subprocess.call(("git", "-C", src_root, "pull", "--ff-only", "origin", "main"))
    if rc == 0:
        os.utime(fn)
    return rc


def initialize_config(config_path: str, defaults: Config) -> None:
    if os.path.exists(config_path):
        # todo: query for any config options not in  the existing config file
        return

    config = configparser.ConfigParser(allow_no_value=True)
    config.read_dict(defaults)
    for section, values in config.items():
        for var, val in values.items():
            if val is None:
                print(var.strip("# "), end="")
            else:
                values[var] = input(f" [{val}]: ") or val
    print("Thank you. Saving answsers...")
    os.makedirs(config_root, exist_ok=True)
    with open(config_path, "w") as f:
        config.write(f)
    print(f"If you made a mistake, you can edit {config_path}.")


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(
            f"""commands:
update    - force updates devenv (autoupdated on a daily basis)
bootstrap - {bootstrap.help}
doctor    - {doctor.help}
sync      - {sync.help}
pin-gha   - {pin_gha.help}
"""
        )
        raise SystemExit(1)


def devenv(argv: Sequence[str] | None = None) -> int:
    parser = CustomArgumentParser(add_help=False)
    parser.add_argument(
        "command",
        choices={
            "bootstrap",
            "update",
            "doctor",
            "pin-gha",
            "sync",
        },
    )
    parser.add_argument(
        "--nocoderoot", action="store_true", help="Do not require being in coderoot."
    )
    args, remainder = parser.parse_known_args(argv)

    if args.command == "update":
        return self_update(force=True)

    self_update()

    # generic/standalone tools that do not care about devenv configuration
    if args.command == "pin-gha":
        return pin_gha.main(remainder)

    config_path = f"{config_root}/config.ini"
    initialize_config(config_path, DEFAULT_CONFIG)

    config = configparser.ConfigParser(allow_no_value=True)
    config.read(config_path)
    coderoot = os.path.expanduser(config["devenv"]["coderoot"])
    os.makedirs(coderoot, exist_ok=True)

    if args.command == "bootstrap":
        return bootstrap.main(coderoot, remainder)

    # the remaining tools are repo-specific
    reporoot = gitroot()
    repo = reporoot.split("/")[-1]

    context = {
        "repo": repo,
        "reporoot": reporoot,
    }

    if args.command == "doctor":
        return doctor.main(context, remainder)
    if args.command == "sync":
        return sync.main(context, remainder)

    return 1


def main() -> int:
    import sys

    return devenv(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())