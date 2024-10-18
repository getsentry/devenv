from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Sequence

from devenv.constants import CI
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.lib import brew
from devenv.lib import direnv
from devenv.lib import github
from devenv.lib import proc
from devenv.lib import rosetta
from devenv.lib.config import Config
from devenv.lib.config import initialize_config
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo
from devenv.lib.modules import ExitCode


def main(context: Context, argv: Sequence[str] | None = None) -> ExitCode:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--default-config",
        action="append",
        help="Provide a default config value. e.g., -d coderoot:path/to/root",
    )

    args = parser.parse_args(argv)

    configs = {
        k: v for k, v in [i.split(":", 1) for i in args.default_config or []]
    }

    if "coderoot" not in configs and "code_root" in context:
        configs["coderoot"] = context["code_root"]

    default_config: Config = {"devenv": configs}
    initialize_config(context["config_path"], default_config)

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

    # even though this is called before colima starts,
    # better to try and potentially (although unlikely) fail earlier rather than later
    rosetta.ensure()

    github.add_to_known_hosts()

    if not EXTERNAL_CONTRIBUTOR and not github.check_ssh_access(
        # silence the error the first time since it's expected to happen
        silent=True
    ):
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

    os.makedirs(context["code_root"], exist_ok=True)

    print(
        """
All done! Please close this terminal window and start a fresh one.

Afterward, start working on your project using the devenv fetch command
e.g., devenv fetch sentry or devenv fetch ops
"""
    )

    return 0


module_info = DevModuleInfo(
    action=main,
    name=__name__,
    command="bootstrap",
    help="Bootstraps the development environment.",
)
