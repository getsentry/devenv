from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from devenv.constants import CI
from devenv.constants import DARWIN
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.constants import homebrew_bin
from devenv.lib import proc
from devenv.lib.context import Context
from devenv.lib.modules import argument
from devenv.lib.modules import command
from devenv.lib.modules import ExitCode
from devenv.lib.modules import ModuleDef


@command("fetch", "Fetches a repository")
@argument("repo", help="the repository to fetch")
def main(context: Context, argv: Sequence[str] | None = None) -> ExitCode:
    args = context["args"]
    code_root = context["code_root"]

    if args.repo in ["ops", "getsentry/ops"]:
        fetch(code_root, "getsentry/ops")
        fetch(code_root, "getsentry/terraform-modules", sync=False)

        print(
            f"""
    All done! Please close this terminal window and start a fresh one.

    ops repo is at: {code_root}/ops
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
        fetch(code_root, "getsentry/sentry", auth=CI is None, sync=False)

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
                (f"{homebrew_bin}/brew", "bundle"), cwd=f"{code_root}/sentry"
            )

        proc.run(
            (sys.executable, "-P", "-m", "devenv", "sync"),
            cwd=f"{code_root}/sentry",
        )

        if not CI and not EXTERNAL_CONTRIBUTOR:
            fetch(code_root, "getsentry/getsentry")

        print(
            f"""
    All done! Please close this terminal window and start a fresh one.

    Sentry has been set up in {code_root}/sentry. cd into it and you should
    be able to run `sentry devserver`.
    """
        )

    else:
        if "/" not in args.repo:
            print("Repository names must be in the form of <owner>/<repo>")
            return 1
        fetch(code_root, args.repo)

    return 0


def fetch(
    code_root: str, repo: str, auth: bool = True, sync: bool = True
) -> None:
    org, slug = repo.split("/")

    codepath = f"{code_root}/{slug}"

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
            code_root,
            "clone",
            "--filter=blob:none",
            *additional_args,
        ),
        exit=True,
    )

    if sync:
        proc.run((sys.executable, "-P", "-m", "devenv", "sync"), cwd=codepath)


module_info = ModuleDef(
    module_name=__name__, name="fetch", help="Fetches a repository"
)
