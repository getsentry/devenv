from __future__ import annotations

import os
import re

# Mapping of Homebrew packages to Ubuntu apt equivalents
# Packages not in this mapping will be reported as unmapped
BREW_TO_APT: dict[str, str] = {
    # Common CLI tools
    "jq": "jq",
    "git": "git",
    "curl": "curl",
    "wget": "wget",
    "make": "make",
    "cmake": "cmake",
    "pkg-config": "pkg-config",
    # Development libraries
    "openssl": "libssl-dev",
    "readline": "libreadline-dev",
    "zlib": "zlib1g-dev",
    "libffi": "libffi-dev",
    "bzip2": "libbz2-dev",
    "xz": "liblzma-dev",
    "sqlite": "libsqlite3-dev",
    "libpq": "libpq-dev",
    "librdkafka": "librdkafka-dev",
    "libmaxminddb": "libmaxminddb-dev",
    # Media tools
    "imagemagick": "imagemagick",
    "ffmpeg": "ffmpeg",
    # Virtualization
    "qemu": "qemu-system-x86",
    # File watching
    "watchman": "watchman",
}

# Mapping of Homebrew casks to Ubuntu apt equivalents
CASK_TO_APT: dict[str, str] = {"chromedriver": "chromium-chromedriver"}

# Packages we intentionally skip (user provides their own or we handle separately)
SKIP_PACKAGES = {"docker", "docker-buildx", "colima", "lima"}


def parse_brewfile(path: str) -> tuple[list[str], list[str]]:
    """Parse a Brewfile and return lists of brew and cask package names.

    Returns:
        Tuple of (brew_packages, cask_packages)
    """
    if not os.path.exists(path):
        return [], []

    brew_packages = []
    cask_packages = []
    # Match: brew "package" or brew 'package' or brew "package", options
    brew_pattern = re.compile(r'^brew\s+["\']([^"\']+)["\']')
    cask_pattern = re.compile(r'^cask\s+["\']([^"\']+)["\']')

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = brew_pattern.match(line)
            if match:
                brew_packages.append(match.group(1))
                continue
            match = cask_pattern.match(line)
            if match:
                cask_packages.append(match.group(1))

    return brew_packages, cask_packages


def get_apt_equivalents(
    brew_packages: list[str], cask_packages: list[str] | None = None
) -> tuple[list[str], list[str]]:
    """Convert brew/cask package names to apt package names.

    Returns:
        Tuple of (apt_packages, unmapped_packages)
    """
    apt_packages = []
    unmapped = []

    for pkg in brew_packages:
        if pkg in SKIP_PACKAGES:
            continue
        if pkg in BREW_TO_APT:
            apt_packages.append(BREW_TO_APT[pkg])
        else:
            unmapped.append(pkg)

    for pkg in cask_packages or []:
        if pkg in SKIP_PACKAGES:
            continue
        if pkg in CASK_TO_APT:
            apt_packages.append(CASK_TO_APT[pkg])
        else:
            unmapped.append(f"{pkg} (cask)")

    return apt_packages, unmapped
