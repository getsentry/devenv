from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from devenv.constants import CI
from devenv.constants import shell
from devenv.constants import venv_root
from devenv.lib import brew
from devenv.lib import direnv
from devenv.lib import github
from devenv.lib import proc
from devenv.lib import volta

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
        proc.run(("/usr/bin/xcrun", "-f", "git"))
    except RuntimeError:
        print("Failed to find git. Run xcode-select --install, then re-run bootstrap when done.")
        return 1

    github.add_to_known_hosts()

    if not github.check_ssh_access():
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
        while not github.check_ssh_access():
            input("Still failing to authenticate to GitHub. ENTER to retry, otherwise ^C to quit.")

    brew.install()
    volta.install()
    direnv.install()

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
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    *additional_flags,
                ),
                exit=True,
            )
        if not CI and not os.path.exists(f"{coderoot}/getsentry"):
            proc.run_stream_output(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    "git@github.com:getsentry/getsentry",
                ),
                exit=True,
            )

        # we don't want colima in CI, it'll be removed soon anyways
        # note: -i '' is BSD sed
        proc.run(("/usr/bin/sed", "-i", "''", "'/colima/d'", f"{coderoot}/sentry/Brewfile"))

        print("Installing sentry's brew dependencies...")
        proc.run_stream_output(("brew", "bundle"), cwd=f"{coderoot}/sentry")

        # this'll create the virtualenv if it doesn't exist
        proc.run_stream_output(("devenv", "sync"), cwd=f"{coderoot}/sentry")

        # make bootstrap should be ported over to devenv sync,
        # as it applies new migrations as well and so would need to ensure
        # the appropriate devservices are running
        proc.run_stream_output(
            (
                shell,
                "-i",
                "-euo",
                "pipefail",
                "-c",
                f"""
source {venv_root}/sentry/bin/activate
make bootstrap
cd ../getsentry
make bootstrap
""",
            ),
            cwd=f"{coderoot}/sentry",
        )

    # need to tell people to cd into sentry and start devserver
    print("All done! Please close this terminal window and start a fresh one.")
    return 0
