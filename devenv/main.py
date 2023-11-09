from __future__ import annotations

import argparse
import configparser
import os
import subprocess
import time
from collections.abc import Sequence
from typing import cast

from typing_extensions import TypeAlias

from devenv import bootstrap
from devenv import doctor
from devenv import pin_gha
from devenv import sync
from devenv.constants import config_root
from devenv.constants import root
from devenv.lib.fs import gitroot

ExitCode: TypeAlias = "str | int | None"

# comments are used as input prompts for initial config
Config: TypeAlias = "dict[str, dict[str, str | None]]"
DEFAULT_CONFIG = dict(
    devenv={
        "# please enter the root directory you want to work in": None,
        "coderoot": "~/code",
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
    rc = subprocess.call(
        (
            f"{root}/venv/bin/python",
            "-m",
            "pip",
            "install",
            "-U",
            "git+https://github.com/getsentry/devenv.git@main",
        )
    )
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
        for var, _val in values.items():
            # typshed doesn't account for `allow_no_value`
            val = cast(str | None, _val)
            if val is None:
                print(var.strip("# "), end="")
            else:
                try:
                    val = input(f" [{val}]: ") or val
                except EOFError:
                    # noninterative, use the defaults
                    print()
                config.set(section, var, val)
    print("Thank you. Saving answers.")
    os.makedirs(config_root, exist_ok=True)
    with open(config_path, "w") as f:
        config.write(f)
    print(f"If you made a mistake, you can edit {config_path}.")


class CustomHelpFormat(
    argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=CustomHelpFormat)
    parser.add_argument(
        "command",
        choices=("update", "bootstrap", "doctor", "sync", "pin-gha"),
        metavar="COMMAND",
        help=f"""\
update    - force updates devenv (autoupdated on a daily basis)
bootstrap - {bootstrap.help}
doctor    - {doctor.help}
sync      - {sync.help}
pin-gha   - {pin_gha.help}
""",
    )
    parser.add_argument(
        "--nocoderoot",
        action="store_true",
        help="Do not require being in coderoot.",
    )
    return parser


def devenv(argv: Sequence[str]) -> ExitCode:
    args, remainder = parser().parse_known_args(argv[1:])

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

    if not args.nocoderoot and not os.getcwd().startswith(coderoot):
        print(
            f"You aren't in your code root ({coderoot})!\n"
            "To ignore, use devenv --nocoderoot [COMMAND]\n"
            f"To change your code root, you can edit {config_path}.\n"
        )
        return 1

    # the remaining tools are repo-specific
    reporoot = gitroot()
    repo = reporoot.split("/")[-1]

    context = {"repo": repo, "reporoot": reporoot}

    if args.command == "doctor":
        return doctor.main(context, remainder)
    if args.command == "sync":
        return sync.main(context, remainder)

    return 1


def main() -> ExitCode:
    import sys

    return devenv(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
