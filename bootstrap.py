from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from devenv.constants import CI
from devenv.lib import github
from devenv.lib import proc


help = "Bootstraps the development environment."


def main(coderoot: str, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument(
        "repo", type=str, nargs="?", default="sentry", choices=("sentry", "getsentry")
    )
    args = parser.parse_args(argv)

    if args.repo == "getsentry":
        # Setting up sentry means we're setting up both repos.
        args.repo = "sentry"

    if args.repo not in {
        "sentry",
    }:
        print(f"repo {args.repo} not supported yet!")
        return 1

    # xcode-select --install will take a while,
    # and involves elevated permissions with a GUI,
    # so best to just let the user go through that separately then retrying,
    # rather than waiting for it.
    # There is a way to perform a headless install but it's more complex
    # (refer to how homebrew does it).
    try:
        xcode_git = proc.run(("/usr/bin/xcrun", "-f", "git"))
    except RuntimeError:
        print("Run xcode-select --install, then come back to bootstrap when done.")
        return 1

    github.add_to_known_hosts()

    if not github.check_ssh_access(xcode_git):
        pubkey = github.generate_and_configure_ssh_keypair()
        input(
            f"""
Failed to authenticate with an ssh key to GitHub.
We've generated and configured one for you at ~/.ssh/sentry-github.
Visit https://github.com/settings/ssh/new and add the following Authentication key:

{pubkey}

Then, you need to go to https://github.com/settings/keys, find your key,
and click Configure SSO, for the getsentry organization.

When done, hit ENTER to continue.
"""
        )
        while not github.check_ssh_access(xcode_git):
            input("Still failing to authenticate to GitHub. ENTER to retry, otherwise ^C to quit.")

    os.makedirs(coderoot, exist_ok=True)

    if args.repo == "sentry":
        if not os.path.exists(f"{coderoot}/sentry"):
            # git@ clones forces the use of cloning through SSH which is what we want,
            # though CI must clone open source repos via https (no git authentication)
            additional_flags = (
                ("--depth", "1", "https://github.com/getsentry/sentry")
                if CI
                else ("git@github.com:getsentry/sentry",)
            )
            proc.run_stream_output(
                (
                    xcode_git,
                    "-C",
                    coderoot,
                    "clone",
                    # https://github.blog/2020-12-21-get-up-to-speed-with-partial-clone-and-shallow-clone/
                    "--filter=blob:none",
                    *additional_flags,
                ),
                exit=True,
            )
        if not CI and not os.path.exists(f"{coderoot}/getsentry"):
            proc.run_stream_output(
                (
                    xcode_git,
                    "-C",
                    coderoot,
                    "clone",
                    "--filter=blob:none",
                    "git@github.com:getsentry/getsentry",
                ),
                exit=True,
            )

    # TODO: install brew

    if args.repo == "sentry":
        pass
        # TODO: sentry's Brewfile

    # TODO: install volta
    # TODO: install direnv

    return 0
