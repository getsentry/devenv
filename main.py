from __future__ import annotations

import argparse
import os
from typing import Sequence

from devenv import doctor, pin_gha
from devenv.lib import gitroot


def self_update(force: bool = False) -> int:
    # should check a well-known last-update file and check for updates daily
    print("updated!")
    return 0


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(
            f"""commands:
update  - force updates devenv (autoupdated on a daily basis)
doctor  - {doctor.help}
pin-gha - {pin_gha.help}
"""
        )
        raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = CustomArgumentParser()
    parser.add_argument("pwd")
    parser.add_argument(
        "command",
        choices={
            "update",
            "doctor",
            "pin-gha",
        },
    )
    args, remainder = parser.parse_known_args(argv)

    if args.command == "update":
        return self_update(force=True)

    self_update()

    os.chdir(args.pwd)

    # generic/standalone tools
    if args.command == "pin-gha":
        return pin_gha.main(remainder)
    # Future home of bootstrap-sentry, and then bootstrap-*.

    # the remaining tools are repo-specific

    # TODO: read a well-known json for preferences
    coderoot = "dev"
    if not args.pwd.startswith(os.path.expanduser(f"~/{coderoot}")):
        print(f"You aren't in your code root (~/{coderoot})!")
        return 1

    reporoot = gitroot(args.pwd)
    repo = reporoot.split("/")[-1]

    context = {
        "repo": repo,
        "reporoot": reporoot,
    }

    # TODO: sync - will bring the project's venv up to date and make
    #       sure it's using the desired python version, otherwise
    #       it should recreate using a prebuilt python
    #       let's make sure it's in the sanctioned venv location so
    #       people can stop using the existing .venvs

    if args.command == "doctor":
        return doctor.main(context, remainder)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
