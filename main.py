from __future__ import annotations

import argparse
import os
import subprocess
import time
from collections.abc import Sequence
from typing import NoReturn

from devenv import doctor
from devenv import pin_gha
from devenv import sync
from devenv.constants import root
from devenv.constants import src_root
from devenv.lib.fs import gitroot


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


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
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
    parser.add_argument(
        "--nocoderoot", action="store_true", help="Do not require being in coderoot."
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
    if not args.nocoderoot and not args.pwd.startswith(os.path.expanduser(f"~/{coderoot}")):
        print(
            f"You aren't in your code root (~/{coderoot})!"
            "To ignore, use devenv --nocoderoot [COMMAND]"
        )
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
