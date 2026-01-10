from __future__ import annotations

import subprocess

from devenv.constants import LINUX


def check_packages_installed(packages: list[str]) -> list[str]:
    """Check which packages are not installed. Returns list of missing packages."""
    if not LINUX:
        return []

    missing = []
    for pkg in packages:
        try:
            subprocess.run(
                ("dpkg", "-s", pkg),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            missing.append(pkg)
    return missing


def print_install_command(packages: list[str]) -> None:
    """Print the apt install command for the user to run."""
    if not packages:
        return

    pkg_list = " ".join(packages)
    print(f"\nMissing apt packages: {pkg_list}")
    print(f"Please run: sudo apt-get update && sudo apt-get install -y {pkg_list}")
    print("Then re-run the devenv command.\n")
