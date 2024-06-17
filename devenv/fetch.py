from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Sequence

from devenv.constants import CI
from devenv.constants import DARWIN
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.constants import homebrew_bin
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
    else:
        fetch(code_root, args.repo)

    repo = context["repo"]
    assert repo is not None

    # optional post-bootstrap, meant for recommended but not required defaults
    if os.path.exists(f"{repo.config_path}/post_bootstrap.py"):
        spec = importlib.util.spec_from_file_location(
            "post_bootstrap", f"{repo.config_path}/post_bootstrap.py"
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore

    if not os.path.exists(f"{repo.config_path}/sync.py"):
        print(f"{repo.config_path}/sync.py not found!")
        return 1

    spec = importlib.util.spec_from_file_location(
        "sync", f"{repo.config_path}/sync.py"
    )

    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)  # type: ignore

    context_compat = {
        "reporoot": repo.path,
        "repo": repo.name,
        "coderoot": context.get("code_root"),
    }

    rc = module.main(context_compat)
    if rc != 0:
        return 1

    print(
        f"""
{repo.name} has been set up in {repo.path}!

Please close this terminal window and start a fresh one.
    """
    )
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

    proc.run(("git", "-C", coderoot, "clone", *additional_args), exit=True)

    if sync:
        proc.run((sys.executable, "-P", "-m", "devenv", "sync"), cwd=codepath)


module_info = DevModuleInfo(
    action=main, name=__name__, command="fetch", help="Fetches a respository"
)
