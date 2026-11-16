from __future__ import annotations

from devenv import constants

installer_url = (
    "https://raw.githubusercontent.com/getsentry/devenv/main/install-devenv.sh"
)


def instructions() -> str:
    return f"""\
curl {installer_url} > install-devenv.sh
bash install-devenv.sh
{constants.root}/bin/devenv sync"""
