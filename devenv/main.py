from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from typing import TypeAlias

from devenv import bootstrap
from devenv import doctor
from devenv import fetch
from devenv import pin_gha
from devenv import sync
from devenv.constants import home
from devenv.context import Context
from devenv.lib.config import get_config
from devenv.lib.fs import gitroot

ExitCode: TypeAlias = "str | int | None"


class CustomHelpFormat(
    argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=CustomHelpFormat)
    parser.add_argument(
        "command",
        choices=("bootstrap", "fetch", "doctor", "sync", "pin-gha", "whereami"),
        metavar="COMMAND",
        help=f"""\
bootstrap - {bootstrap.help}
fetch     - {fetch.help}
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


def devenv(argv: Sequence[str], config_path: str) -> ExitCode:
    # determine current repo, if applicable
    fake_reporoot = os.getenv("CI_DEVENV_INTEGRATION_FAKE_REPOROOT")
    if fake_reporoot:
        current_root = fake_reporoot
    else:
        try:
            current_root = gitroot()
        except RuntimeError:
            current_root = None

    current_repo = current_root.split("/")[-1] if current_root else None

    # Guessing temporary code root based on current location
    code_root = (
        os.path.abspath(f"{current_root}/..") if current_root else os.getcwd()
    )

    # context for subcommands
    context: Context = {"config_path": config_path, "code_root": code_root}

    if current_repo is not None:
        context["repo_name"] = current_repo

    if current_root is not None:
        context["repo_root"] = current_root

    args, remainder = parser().parse_known_args(argv[1:])

    # Bootstrap runs before configuration loading -- because it's a bootstrap
    if args.command == "bootstrap":
        return bootstrap.main(context, remainder)

    config = get_config(context["config_path"])

    code_root = context["code_root"] = os.path.expanduser(
        config["devenv"]["coderoot"]
    )

    # generic/standalone tools that do not care about devenv configuration
    if args.command == "pin-gha":
        return pin_gha.main(context, remainder)

    if args.command == "fetch":
        return fetch.main(context, remainder)

    if not args.nocoderoot and not os.getcwd().startswith(code_root):
        print(
            f"You aren't in your code root ({code_root})!\n"
            "To ignore, use devenv --nocoderoot [COMMAND]\n"
            f"To change your code root, you can edit {config_path}.\n"
        )
        return 1

    if args.command == "doctor":
        return doctor.main(context, remainder)
    if args.command == "sync":
        return sync.main(context, remainder)
    if args.command == "whereami":
        print(context)
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

    return devenv(sys.argv, f"{home}/.config/sentry-devenv/config.ini")


if __name__ == "__main__":
    raise SystemExit(main())
