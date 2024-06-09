from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from devenv import bootstrap
from devenv import doctor
from devenv import fetch
from devenv import pin_gha
from devenv import sync
from devenv.constants import home
from devenv.lib.config import read_config
from devenv.lib.context import Context
from devenv.lib.fs import gitroot
from devenv.lib.modules import DevModuleInfo
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

    modinfo_list: Sequence[DevModuleInfo] = [
        module.module_info
        for module in [bootstrap, fetch, doctor, pin_gha, sync]
        if hasattr(module, "module_info")
    ]

    # TODO: Search for modules in work repo

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(
        title=argparse.SUPPRESS,
        metavar="command",
        dest="command",
        required=True,
    )

    for info in modinfo_list:
        # Argparse stuff
        subparser.add_parser(info.command, help=info.help)

    args, remainder = parser.parse_known_args(argv[1:])

    # context for subcommands
    context: Context = {
        "config_path": config_path,
        "code_root": code_root,
        "repo": Repository(current_root) if current_root else None,
    }

    command_actions = {info.command: info.action for info in modinfo_list}
    action = command_actions.get(args.command)
    assert action is not None
    return action(context, remainder)


def main() -> ExitCode:
    import os
    import sys

    script_logfile = os.environ.get("SCRIPT")

    if not script_logfile:
        import tempfile

        _, fp  = tempfile.mkstemp()
        # script runs the subcommand with a tty, and tees the output to a file
        # available on macos + linux
        # the -F is important since otherwise some output isn't flushed by the time
        # we send a sentry event, as this is a reexec wrapper and not a shell script
        # this way we can very easily capture all output from devenv and send it
        # to sentry as an attachment if an error occurs
        cmd = ("/usr/bin/script", "-qeF", fp, *sys.argv)
        os.execv(cmd[0], cmd)

    import sentry_sdk

    sentry_sdk.init(
        # https://sentry.sentry.io/settings/projects/sentry-dev-env/keys/
        dsn="https://9bdb053cb8274ea69231834d1edeec4c@o1.ingest.sentry.io/5723503",
        # enable performance monitoring
        enable_tracing=True,
    )

    with sentry_sdk.configure_scope() as scope:
        scope.add_attachment(path=script_logfile)

    # the only way this is going to work is for script to exit, then send the event
    # i guess i could do that in python land still, just with subprocess

    return devenv(sys.argv, f"{home}/.config/sentry-devenv/config.ini")


if __name__ == "__main__":
    raise SystemExit(main())
