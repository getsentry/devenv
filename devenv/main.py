from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from types import ModuleType
from typing import List

import sentry_sdk

from devenv.constants import home
from devenv.lib import modules
from devenv.lib.config import read_config
from devenv.lib.context import Context
from devenv.lib.fs import gitroot
from devenv.lib.modules import CommandInfo
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import ExitCode
from devenv.lib.modules import module_info
from devenv.lib.repository import Repository


def generate_parser(
    modinfo_list: Sequence[DevModuleInfo],
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(
        title=argparse.SUPPRESS,
        metavar="command",
        dest="command",
        required=True,
    )

    for info in modinfo_list:
        # don't show modules with no actions defined
        if not info.commands:
            continue

        module_def = info.module_def
        child = subparser.add_parser(module_def.name, help=module_def.help)

        if len(info.commands) == 1 and (
            info.commands[0].name == module_def.name
        ):
            # single command, matching name case; i.e., module == command
            command = info.commands[0]
            for fn in command.arguments:
                fn(child)
            continue

        subsubparser = child.add_subparsers(
            title="subcommands",
            metavar="subcommand",
            dest="subcommand",
            required=True,
        )

        for command in info.commands:
            if command.name == module_def.name:
                # module has a default command, subcommand not required
                subsubparser.required = False
                for fn in command.arguments:
                    fn(child)
            else:
                grandchild = subsubparser.add_parser(
                    command.name, help=command.help
                )
                for fn in command.arguments:
                    fn(grandchild)
    return parser


def load_modules(path: str, package: ModuleType) -> List[DevModuleInfo]:
    if not os.path.exists(path):
        return []
    if path not in package.__path__:
        package.__path__.append(path)
    return [
        module_info(module)
        for module in modules.load_modules(path, package.__name__)
        if hasattr(module, "module_info")
    ]


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

    import devenv.commands
    import devenv.usercommands

    modinfo_list = load_modules(devenv.commands.__path__[0], devenv.commands)

    if current_root:
        user_path = f"{Repository(current_root).config_path}/usercommands"
        modinfo_list.extend(load_modules(user_path, devenv.usercommands))

    parser = generate_parser(modinfo_list)
    args, remainder = parser.parse_known_args(argv[1:])

    # context for subcommands
    context: Context = {
        "config_path": config_path,
        "code_root": code_root,
        "repo": Repository(current_root) if current_root else None,
        "args": args,
    }

    modinfo = next(
        module
        for module in modinfo_list
        if module.module_def.name == args.command
    )

    commands: dict[str, CommandInfo] = {
        command.name: command for command in modinfo.commands
    }
    command_name = getattr(args, "subcommand") or args.command
    command = commands.get(command_name)

    assert command is not None

    return command.action(context, remainder)


def main() -> ExitCode:
    import sys

    sentry_sdk.init(
        # https://sentry.sentry.io/settings/projects/sentry-dev-env/keys/
        dsn="https://9bdb053cb8274ea69231834d1edeec4c@o1.ingest.sentry.io/5723503",
        # enable performance monitoring
        enable_tracing=True,
    )

    return devenv(sys.argv, f"{home}/.config/sentry-devenv/config.ini")


if __name__ == "__main__":
    raise SystemExit(main())
