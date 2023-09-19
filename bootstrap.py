from __future__ import annotations

import argparse
from collections.abc import Sequence

from devenv.lib import proc


help = "Bootstraps the development environment."


def main(coderoot: str, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument("repo", type=str, nargs="?", default="sentry")
    args = parser.parse_args(argv)

    # xcode-select --install will take a while,
    # and involves elevated permissions with a GUI,
    # so best to just let the user go through that separately then retrying,
    # rather than waiting for it.
    # There is a way to perform a headless install but it's more complex
    # (refer to how homebrew does it).

    try:
        xcode_git = proc.run(("/usr/bin/xcrun", "-f", "git"), exit=False)
    except RuntimeError:
        print("Run xcode-select --install, then come back to bootstrap when done.")
        return 1

    proc.run((xcode_git,))

    # TODO: setup github access

    # TODO: make coderoot and clone sentry and getsentry

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
