from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Sequence
from typing import TypeAlias

from devenv.constants import CI
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.lib import brew
from devenv.lib import direnv
from devenv.lib import github
from devenv.lib import proc
from devenv.lib.config import Config
from devenv.lib.config import DEFAULT_CONFIG
from devenv.lib.config import initialize_config

help = "Bootstraps the development environment."
ExitCode: TypeAlias = "str | int | None"


def main(
    config_path: str, coderoot: str, argv: Sequence[str] | None = None
) -> ExitCode:
    parser = argparse.ArgumentParser(description=help)
    parser.parse_args(argv)

    default_config: Config = {**DEFAULT_CONFIG}
    default_config["devenv"].update({"coderoot": coderoot})
    initialize_config(config_path, default_config)

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

    print(
        """
All done! Please close this terminal window and start a fresh one.

Afterward, start working on your project using the devenv fetch command
e.g., devenv fetch sentry or devenv fetch ops
"""
    )

    return 0
