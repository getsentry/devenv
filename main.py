from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Sequence

from devenv import doctor
from devenv import pin_gha
from devenv import sync
from devenv.constants import src_root
from devenv.lib import gitroot


def self_update(force: bool = False) -> int:
    # should check a well-known last-update file and check for updates daily
    print("Updating devenv tool...")
    # We don't have any dependencies. If we do end up adding some,
    # we should vendor to avoid pip calls to keep it lean and simple.
    return subprocess.call(("git", "-C", src_root, "pull", "--ff-only", "origin", "main"))


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(
            f"""commands:
update  - force updates devenv (autoupdated on a daily basis)
doctor  - {doctor.help}
sync    - {sync.help}
pin-gha - {pin_gha.help}
"""
        )
        raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = CustomArgumentParser(add_help=False)
    parser.add_argument("pwd")
    parser.add_argument(
        "command",
        choices={
            "update",
            "doctor",
            "pin-gha",
            "sync",
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

    if args.command == "doctor":
        return doctor.main(context, remainder)
    if args.command == "sync":
        return sync.main(context, remainder)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
