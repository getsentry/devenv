from __future__ import annotations

import argparse
import os
from typing import Sequence

from devenv import doctor
from devenv.lib import gitroot


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(
            f"""commands:
doctor - {doctor.help}
"""
        )
        raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = CustomArgumentParser()
    parser.add_argument("pwd")
    parser.add_argument(
        "command",
        choices={
            "doctor",
        },
    )
    args, remainder = parser.parse_known_args(argv)

    # self_update()

    # TODO: read a well-known json for preferences
    coderoot = "dev"

    # Future home of bootstrap-sentry, and then bootstrap-*.

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
