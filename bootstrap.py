from __future__ import annotations

import argparse
from collections.abc import Sequence


help = "Bootstraps the development environment."


def main(coderoot: str, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument("repo", type=str, nargs="?", default="sentry")
    args = parser.parse_args(argv)

    # TODO: install xcode

    # TODO: setup github access

    # TODO: clone sentry and getsentry

    # TODO: install brew and Brewfile

    # TODO: install volta and direnv

    if args.repo == "getsentry":
        # Setting up sentry means we're setting up both repos.
        args.repo = "sentry"

    if args.repo not in {
        "sentry",
    }:
        print(f"repo {args.repo} not supported yet!")
        return 1

    return 0
