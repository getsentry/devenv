from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import TypeAlias

from devenv.constants import CI
from devenv.constants import DARWIN
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.constants import homebrew_bin
from devenv.lib import proc

help = "Fetches a respository"
ExitCode: TypeAlias = "str | int | None"


def main(coderoot: str, argv: Sequence[str] | None = None) -> ExitCode:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument(
        "repo",
        type=str,
        nargs="?",
        default="sentry",
        help="the repository to fetch e.g., getsentry/sentry",
    )

    args = parser.parse_args(argv)

    if args.repo in ["ops", "getsentry/ops"]:
        fetch(coderoot, "getsentry/ops")
        fetch(coderoot, "getsentry/terraform-modules", sync=False)

        print(
            f"""
    All done! Please close this terminal window and start a fresh one.

    ops repo is at: {coderoot}/ops
    """
        )
    elif args.repo in [
        "sentry",
        "getsentry",
        "getsentry/sentry",
        "getsentry/getsentry",
    ]:
        # git@ clones forces the use of cloning through SSH which is what we want,
        # though CI must clone open source repos via https (no git authentication)
        fetch(coderoot, "getsentry/sentry", auth=CI is None, sync=False)

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

        proc.run(
            (sys.executable, "-P", "-m", "devenv", "sync"),
            cwd=f"{coderoot}/sentry",
        )

        if not CI and not EXTERNAL_CONTRIBUTOR:
            fetch(coderoot, "getsentry/getsentry")

        print(
            f"""
    All done! Please close this terminal window and start a fresh one.

    Sentry has been set up in {coderoot}/sentry. cd into it and you should
    be able to run `sentry devserver`.
    """
        )

    else:
        fetch(coderoot, args.repo)

    return 0


def fetch(
    coderoot: str, repo: str, auth: bool = True, sync: bool = True
) -> None:
    org, slug = repo.split("/")

    codepath = f"{coderoot}/{slug}"

    if os.path.exists(codepath):
        print(f"{codepath} already exists")
        return

    print(f"fetching {repo} into {codepath}")

    additional_args = (
        (f"git@github.com:{repo}",)
        if auth
        else (
            "--depth",
            "1",
            "--single-branch",
            f"--branch={os.environ['SENTRY_BRANCH']}",
            f"https://github.com/{repo}",
        )
    )

    proc.run(
        (
            "git",
            "-C",
            coderoot,
            "clone",
            "--filter=blob:none",
            *additional_args,
        ),
        exit=True,
    )

    if sync:
        proc.run((sys.executable, "-P", "-m", "devenv", "sync"), cwd=codepath)