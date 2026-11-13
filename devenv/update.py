from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import urllib.request
from collections.abc import Sequence

from devenv import constants
from devenv.lib import brew
from devenv.lib import colima
from devenv.lib import direnv
from devenv.lib import docker
from devenv.lib import limactl
from devenv.lib import mise
from devenv.lib import proc
from devenv.lib import sentry_cli
from devenv.lib import uv
from devenv.lib.context import Context
from devenv.lib.modules import DevModuleInfo

module_help = "Updates global devenv and tools."

installer_url = (
    "https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh"
)


def reinstall_if_python_changed() -> bool:
    # pip can't change the python of the global devenv venv, and when a new release needs a newer python it quietly installs the newest release that fits the old one instead, so rerun install-devenv.sh to rebuild the venv when its python pin changes
    with urllib.request.urlopen(installer_url) as resp:
        script = resp.read().decode()

    m = re.search(r"SNTY_DEVENV_PY_VERSION:-([0-9.]+)", script)
    if m is None:
        return False
    want = m.group(1)

    have = proc.run(
        (
            f"{constants.root}/venv/bin/python",
            "-c",
            "import platform; print(platform.python_version())",
        ),
        stdout=True,
    ).strip()
    if have == want:
        return False

    print(f"Global devenv uses python {have} but needs {want}, reinstalling.")
    with tempfile.TemporaryDirectory() as tmpd:
        # the installer only runs when it's named install-devenv.sh
        path = f"{tmpd}/install-devenv.sh"
        with open(path, "w") as f:
            f.write(script)
        proc.run(("bash", path))
    return True


def main(context: Context, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", type=str, nargs="?")
    parser.add_argument(
        "--post-update", action="store_true", help="Internal, do not use."
    )

    args = parser.parse_args(argv)

    # This is so that people don't have to run update twice.
    if args.post_update:
        # Mirror this in bootstrap.py.
        print(f"""\
Updating global tools (at {constants.root}/bin).
""")
        os.makedirs(f"{constants.root}/bin", exist_ok=True)

        if constants.DARWIN:
            # we only install brew and colima-related stuff on macos
            brew.install()
            docker.install_global()
            colima.install_global()
            limactl.install_global()

        direnv.install()
        mise.install()
        sentry_cli.install()

        return 0

    is_global_devenv = sys.executable.startswith(
        f"{constants.root}/venv/bin/python"
    )

    global_devenv_exists = os.path.exists(f"{constants.root}/bin/devenv")

    # even if we aren't the global devenv, we want to update
    # the global devenv (but only if it exists) out of convenience
    if (is_global_devenv or global_devenv_exists) and not (
        args.version is None and reinstall_if_python_changed()
    ):
        if args.version is None:
            version = "sentry-devenv"
        else:
            version = f"sentry-devenv=={args.version}"

        proc.run(
            (
                uv.find(),
                "pip",
                "install",
                "--python",
                f"{constants.root}/venv/bin/python",
                "--upgrade",
                version,
            )
        )

        print(f"""\

Global devenv at {constants.root}/bin/devenv updated.
""")

    # install-devenv.sh originally creates this symlink
    # but we should make sure it exists no matter what
    # in case it's accidentally deleted by the user
    if not global_devenv_exists:
        os.symlink(
            f"{constants.root}/venv/bin/devenv", f"{constants.root}/bin/devenv"
        )

    proc.run((sys.executable, "-P", "-m", "devenv", "update", "--post-update"))

    if not is_global_devenv:
        print("""\
To update the local devenv, you'll want to run `devenv sync`.
""")

    return 0


module_info = DevModuleInfo(
    action=main, name=__name__, command="update", help=module_help
)
