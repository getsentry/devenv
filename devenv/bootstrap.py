from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Sequence
from typing import TypeAlias

from devenv.constants import CI
from devenv.constants import DARWIN
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.constants import homebrew_bin
from devenv.lib import brew
from devenv.lib import direnv
from devenv.lib import github
from devenv.lib import proc

help = "Bootstraps the development environment."
ExitCode: TypeAlias = "str | int | None"


def main(coderoot: str, argv: Sequence[str] | None = None) -> ExitCode:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument(
        "repo", type=str, nargs="?", default="sentry", choices=("sentry", "ops")
    )
    args = parser.parse_args(argv)

    if not CI and shutil.which("xcrun"):
        # xcode-select --install will take a while,
        # and involves elevated permissions with a GUI,
        # so best to just let the user go through that separately then retrying,
        # rather than waiting for it.
        # There is a way to perform a headless install but it's more complex
        # (refer to how homebrew does it).
        try:
            _ = proc.run(("xcrun", "-f", "git"), stdout=True)
        except RuntimeError:
            return "Failed to find git. Run xcode-select --install, then re-run bootstrap when done."

    github.add_to_known_hosts()

    if not EXTERNAL_CONTRIBUTOR and not github.check_ssh_access():
        is_employee = (
            False
            if CI
            else input("Are you a Sentry employee? (Y/n): ").lower()
            in {"y", "yes", ""}
        )
        if not CI and not is_employee:
            print(
                "Please set the SENTRY_EXTERNAL_CONTRIBUTOR environment variable and re-run bootstrap."
            )
            return 1
        pubkey = github.generate_and_configure_ssh_keypair()
        if not CI:
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
            input(
                "Still failing to authenticate to GitHub. ENTER to retry, otherwise ^C to quit."
            )

    brew.install()
    direnv.install()

    os.makedirs(coderoot, exist_ok=True)

    if args.repo == "ops":
        if not os.path.exists(f"{coderoot}/ops"):
            proc.run(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    "--filter=blob:none",
                    "git@github.com:getsentry/ops",
                ),
                exit=True,
            )
        if not os.path.exists(f"{coderoot}/terraform-modules"):
            proc.run(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    "--filter=blob:none",
                    "git@github.com:getsentry/terraform-modules",
                ),
                exit=True,
            )
        proc.run(("devenv", "sync"), cwd=f"{coderoot}/ops")
        print(
            f"""
    All done! Please close this terminal window and start a fresh one.

    ops repo is at: {coderoot}/ops
    """
        )
    elif args.repo == "sentry":
        if not os.path.exists(f"{coderoot}/sentry"):
            # git@ clones forces the use of cloning through SSH which is what we want,
            # though CI must clone open source repos via https (no git authentication)
            additional_flags = (
                (
                    "--depth",
                    "1",
                    "--single-branch",
                    f"--branch={os.environ['SENTRY_BRANCH']}",
                    "https://github.com/getsentry/sentry",
                )
                if CI
                else ("git@github.com:getsentry/sentry",)
            )
            proc.run(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    # Download all reachable commits and trees while fetching blobs on-demand
                    # https://github.blog/2020-12-21-get-up-to-speed-with-partial-clone-and-shallow-clone/
                    "--filter=blob:none",
                    *additional_flags,
                ),
                exit=True,
            )

        bootstrap_getsentry = not CI and not EXTERNAL_CONTRIBUTOR
        if bootstrap_getsentry and not os.path.exists(f"{coderoot}/getsentry"):
            proc.run(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    "--filter=blob:none",
                    "git@github.com:getsentry/getsentry",
                ),
                exit=True,
            )

        print("Installing sentry's brew dependencies...")
        if CI:
            if DARWIN:
                # Installing everything from brew takes too much time,
                # and chromedriver cask flakes occasionally. Really all we need to
                # set up the devenv is colima and docker-cli.
                # This is also required for arm64 macOS GHA runners.
                # We manage colima, so just need to install docker + qemu here.
                proc.run(("brew", "install", "docker", "qemu"))
        else:
            proc.run(
                (f"{homebrew_bin}/brew", "bundle"), cwd=f"{coderoot}/sentry"
            )

        # this'll create the virtualenv if it doesn't exist
        proc.run(
            (sys.executable, "-P", "-m", "devenv", "sync"),
            cwd=f"{coderoot}/sentry",
        )

        # make bootstrap should be ported over to devenv sync,
        # as it applies new migrations as well and so would need to ensure
        # the appropriate devservices are running
        proc.run(
            ("make", "bootstrap"),
            env={"VIRTUAL_ENV": f"{coderoot}/sentry/.venv"},
            pathprepend=f"{coderoot}/sentry/.devenv/bin:{coderoot}/sentry/.venv/bin",
            cwd=f"{coderoot}/sentry",
        )

        if bootstrap_getsentry:
            # this'll create the virtualenv if it doesn't exist
            proc.run(
                (sys.executable, "-P", "-m", "devenv", "sync"),
                cwd=f"{coderoot}/getsentry",
            )

            # we don't have permissions to clone getsentry which is a good thing
            # eventually we should move this bootstrap testing over to getsentry repo
            proc.run(
                ("make", "bootstrap"),
                env={"VIRTUAL_ENV": f"{coderoot}/getsentry/.venv"},
                pathprepend=f"{coderoot}/getsentry/.devenv/bin:{coderoot}/getsentry/.venv/bin",
                cwd=f"{coderoot}/getsentry",
            )

        print(
            f"""
    All done! Please close this terminal window and start a fresh one.

    Sentry has been set up in {coderoot}/sentry. cd into it and you should
    be able to run `sentry devserver`.
    """
        )

    return 0
