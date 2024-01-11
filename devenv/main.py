from __future__ import annotations

import argparse
import configparser
import os
from collections.abc import Sequence
from typing import cast
from typing import Optional

from typing_extensions import TypeAlias

from devenv import bootstrap
from devenv import doctor
from devenv import pin_gha
from devenv import sync
from devenv.constants import CI
from devenv.constants import config_root
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


def initialize_config(config_path: str, defaults: Config) -> None:
    if os.path.exists(config_path):
        # todo: query for any config options not in  the existing config file
        return

    config = configparser.ConfigParser(allow_no_value=True)
    config.read_dict(defaults)

    if not CI:
        for section, values in config.items():
            for var, _val in values.items():
                if section == "devenv" and var == "coderoot":
                    # this is a special case used to make the transition from existing
                    # dev environments easier as we can guess the desired coderoot if
                    # devenv is run inside of a git repo
                    try:
                        reporoot = gitroot()
                    except RuntimeError:
                        pass
                    else:
                        coderoot = os.path.abspath(f"{reporoot}/..")
                        print(f"\nWe autodetected a coderoot: {coderoot}")
                        config.set(section, var, coderoot)
                        continue

                # typshed doesn't account for `allow_no_value`
                val = cast(Optional[str], _val)
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
        choices=("bootstrap", "doctor", "sync", "pin-gha"),
        metavar="COMMAND",
        help=f"""\
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

    import sentry_sdk

    sentry_sdk.init(
        # https://sentry.sentry.io/settings/projects/sentry-dev-env/keys/
        dsn="https://9bdb053cb8274ea69231834d1edeec4c@o1.ingest.sentry.io/5723503",
        # enable performance monitoring
        enable_tracing=True,
    )

    return devenv(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
