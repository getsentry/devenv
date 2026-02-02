from __future__ import annotations

import subprocess


def dpkg_is_installed(pkg: str) -> bool:
    try:
        out = subprocess.check_output(
            ["dpkg-query", "-W", "-f=${Status}", pkg],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return False

    # <want> <error> <status>
    return out == "install ok installed"


def dpkgs_not_installed(pkgs: list[str]) -> list[str]:
    return [pkg for pkg in pkgs if not dpkg_is_installed(pkg)]
