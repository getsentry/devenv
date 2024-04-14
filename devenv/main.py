from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from typing import cast

from devenv import bootstrap
from devenv import doctor
from devenv import fetch
from devenv import pin_gha
from devenv import sync
from devenv.constants import home
from devenv.lib.config import read_config
from devenv.lib.context import Context
from devenv.lib.fs import gitroot
from devenv.lib.modules import ExitCode
from devenv.lib.repository import Repository


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

    # This may or may not exist
    config = read_config(config_path)

    # Guessing temporary code root
    code_root = config.get("devenv", "coderoot", fallback=None) or (
        os.path.abspath(f"{current_root}/..")
        if current_root
        else os.path.expanduser("~/code")
    )

    modinfo_list = [
        (module.__name__, module.module_info)
        for module in [bootstrap, fetch, doctor, pin_gha, sync]
        if hasattr(module, "module_info")
    ]

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(
        title=argparse.SUPPRESS, metavar="command", dest="module", required=True
    )

    for name, info in modinfo_list:
        # Argparse stuff
        child = subparser.add_parser(info.command, help=info.help)
        child.add_argument(
            "--xixax",
            dest="_module_exec",
            default=info.action,
            required=False,
            help=argparse.SUPPRESS,
        )

    args, remainder = parser.parse_known_args(argv[1:])

    # context for subcommands
    context: Context = {
        "config_path": config_path,
        "code_root": code_root,
        "repo": Repository(current_root) if current_root else None,
    }

    return cast(ExitCode, args._module_exec(context, remainder))


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
