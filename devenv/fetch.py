from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Sequence

from devenv import constants
from devenv.lib import proc
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import ExitCode


def main(context: Context, argv: Sequence[str] | None = None) -> ExitCode:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "repo", type=str, help="the repository to fetch e.g., getsentry/sentry"
    )

    args = parser.parse_args(argv)
    code_root = context["code_root"]

    if args.repo in ["ops", "getsentry/ops"]:
        fetch(code_root, "getsentry/ops")
        fetch(code_root, "getsentry/terraform-modules", sync=False)
    elif args.repo in [
        "sentry",
        "getsentry",
        "getsentry/sentry",
        "getsentry/getsentry",
    ]:
        fetch(
            code_root, "getsentry/sentry", auth=constants.CI is None, sync=False
        )

        proc.run(
            (sys.executable, "-P", "-m", "devenv", "sync"),
            cwd=f"{code_root}/sentry",
        )

        if not constants.CI and not constants.EXTERNAL_CONTRIBUTOR:
            fetch(code_root, "getsentry/getsentry")

        print(
            f"""

    All done! Please close this terminal window and start a fresh one.
    Sentry has been set up in {code_root}/sentry.
    cd into it and you should be able to run `sentry devserver`.

"""
        )
    else:
        fetch(code_root, args.repo)

    return 0


def fetch(
    coderoot: str, repo: str, auth: bool = True, sync: bool = True
) -> None:
    org, slug = repo.split("/")

    reporoot = f"{coderoot}/{slug}"

    if os.path.exists(reporoot):
        print(f"{reporoot} already exists")
        return

    print(f"fetching {repo} into {reporoot}")

    additional_args = (
        # git@ clones forces the use of cloning through SSH which is what we want,
        # though CI must clone open source repos via https (no git authentication)
        (f"git@github.com:{repo}",)
        if auth
        else (
            "--depth",
            "1",
            "--single-branch",
            f"--branch={os.environ['DEVENV_FETCH_BRANCH']}",
            f"https://github.com/{repo}",
        )
    )

    proc.run(("git", "-C", coderoot, "clone", *additional_args), exit=True)

    context_post_fetch = {
        "reporoot": reporoot,
        "repo": slug,
        "coderoot": coderoot,
    }

    # optional post-fetch, meant for recommended but not required defaults
    fp = f"{reporoot}/devenv/post_fetch.py"
    if os.path.exists(fp):
        spec = importlib.util.spec_from_file_location("post_fetch", fp)

        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore

        rc = module.main(context_post_fetch)
        if rc != 0:
            print(f"warning! failed running {fp} (code {rc})")

    if sync:
        proc.run((sys.executable, "-P", "-m", "devenv", "sync"), cwd=reporoot)


module_info = DevModuleInfo(
    action=main, name=__name__, command="fetch", help="Fetches a repository"
)
