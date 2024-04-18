from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from typing import cast
from typing import Optional
from typing import TypeAlias

from devenv import bootstrap
from devenv import doctor
from devenv import fetch
from devenv import pin_gha
from devenv import sync
from devenv.constants import home
from devenv.lib.config import read_config
from devenv.lib.fs import gitroot
ExitCode: TypeAlias = "str | int | None"
Config: TypeAlias = "dict[str, dict[str, str | None]]"
class CustomHelpFormat(
    argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=CustomHelpFormat)
    parser.add_argument(
        "command",
        choices=("bootstrap", "fetch", "doctor", "sync", "pin-gha"),
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
    args, remainder = parser().parse_known_args(argv[1:])

    # generic/standalone tools that do not care about devenv configuration
    if args.command == "pin-gha":
        return pin_gha.main(remainder)


    # determine current repo, if applicable
    fake_reporoot = os.getenv("CI_DEVENV_INTEGRATION_FAKE_REPOROOT")
    if fake_reporoot:
        current_root = fake_reporoot
    else:
        try:
            current_root = gitroot()
        except RuntimeError:
            current_root = None

    # This may or may not exist
    config = read_config(config_path)

    # Guessing temporary code root
    code_root = config.get("devenv", "coderoot", fallback=None) or (
        os.path.abspath(f"{current_root}/..")
        if current_root
        else os.path.expanduser("~/code")
    )

    if args.command == "bootstrap":
        return bootstrap.main(coderoot, remainder)

    if args.command == "fetch":
        return fetch.main(coderoot, remainder)

    if not args.nocoderoot and not os.getcwd().startswith(coderoot):
        print(
            f"You aren't in your code root ({coderoot})!\n"
            "To ignore, use devenv --nocoderoot [COMMAND]\n"
            f"To change your code root, you can edit {config_path}.\n"
        )
        return 1

    # the remaining tools are repo-specific
    reporoot = gitroot()

    fake_reporoot = os.getenv("CI_DEVENV_INTEGRATION_FAKE_REPOROOT")
    if fake_reporoot:
        reporoot = fake_reporoot

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

    return devenv(sys.argv, f"{home}/.config/sentry-devenv/config.ini")


if __name__ == "__main__":
    raise SystemExit(main())
