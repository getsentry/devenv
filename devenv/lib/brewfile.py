from __future__ import annotations

import os
import re

# Mapping of Homebrew packages to Ubuntu apt equivalents
# Packages not in this mapping are skipped (e.g., docker - we don't install it)
BREW_TO_APT: dict[str, str] = {
    "qemu": "qemu-system-x86",
    "jq": "jq",
    "git": "git",
    "curl": "curl",
    "wget": "wget",
    "make": "make",
    "cmake": "cmake",
    "pkg-config": "pkg-config",
    "openssl": "libssl-dev",
    "readline": "libreadline-dev",
    "zlib": "zlib1g-dev",
    "libffi": "libffi-dev",
    "bzip2": "libbz2-dev",
    "xz": "liblzma-dev",
    "sqlite": "libsqlite3-dev",
    "libpq": "libpq-dev",
    "imagemagick": "imagemagick",
    "ffmpeg": "ffmpeg",
    "librdkafka": "librdkafka-dev",
    "libmaxminddb": "libmaxminddb-dev",
}

# Packages we intentionally skip (user provides their own or we handle separately)
SKIP_PACKAGES = {
    "docker",
    "docker-buildx",
    "colima",
    "lima",
}


def parse_brewfile(path: str) -> list[str]:
    """Parse a Brewfile and return list of brew package names."""
    if not os.path.exists(path):
        return []

    packages = []
    # Match: brew "package" or brew 'package' or brew "package", options
    brew_pattern = re.compile(r'^brew\s+["\']([^"\']+)["\']')

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = brew_pattern.match(line)
            if match:
                packages.append(match.group(1))

    return packages


def get_apt_equivalents(brew_packages: list[str]) -> tuple[list[str], list[str]]:
    """Convert brew package names to apt package names.

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
    return apt_packages, unmapped
