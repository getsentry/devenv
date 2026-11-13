from __future__ import annotations

import os
import tempfile

from devenv.constants import MACHINE
from devenv.constants import SYSTEM
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import proc

_version = "2026.11.8"

_sha256 = {
    "macos-arm64": "3e390ecbcf7f03e91e72c920a248a0f149f00d77ae95d37ea1736a1c7b42fee6",
    "macos-x64": "efedda14eb491af096dc27daaccfd5c57caaf77f1b79c5e387b8a091b8938f66",
    "linux-arm64": "0de1450dcc3f838e372e05e8c5231423760ad3f22d14275ef340bc0a250303ce",
    "linux-x64": "32b6abe844efa43d37d7ac4ed21d2ec41e9479d66feb19b0db8d2c548cd6e36d",
}

# the project-level config files mise reads from a directory
# https://mise.jdx.dev/configuration.html
CONFIG_FILES = (
    "mise.toml",
    ".mise.toml",
    "mise/config.toml",
    ".mise/config.toml",
    ".config/mise.toml",
    ".config/mise/config.toml",
)

mise_path = f"{root}/bin/mise"


def configured(reporoot: str) -> bool:
    return any(os.path.exists(f"{reporoot}/{fp}") for fp in CONFIG_FILES)


def _installed_version() -> str:
    try:
        stdout = proc.run((mise_path, "--version"), stdout=True)
    except RuntimeError:
        return ""
    # 2026.11.8 macos-arm64 (2026-11-13)
    return stdout.split()[0]


def install() -> None:
    if _installed_version() == _version:
        return

    system = "macos" if SYSTEM == "darwin" else SYSTEM
    machine = "arm64" if MACHINE in ("arm64", "aarch64") else "x64"
    name = f"mise-v{_version}-{system}-{machine}"
    url = f"https://github.com/jdx/mise/releases/download/v{_version}/{name}"

    print(f"installing mise {_version}...")
    bindir = os.path.dirname(mise_path)
    os.makedirs(bindir, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=bindir) as tmpd:
        tmp = archive.download(
            url, _sha256[f"{system}-{machine}"], dest=f"{tmpd}/mise"
        )
        os.chmod(tmp, 0o775)
        # tmpd is in bindir so this atomically replaces an older mise
        os.replace(tmp, mise_path)

    if _installed_version() != _version:
        raise SystemExit(f"failed to install mise {_version}!")


def _has_task(reporoot: str, task: str) -> bool:
    try:
        proc.run((mise_path, "tasks", "info", task), cwd=reporoot, stdout=True)
    except RuntimeError:
        return False
    return True


def sync(reporoot: str) -> int:
    """
    Installs the tools in reporoot's mise config, then runs its `sync` task
    if it has one. Returns the exit code to report from devenv sync.

    mise install and mise run trust the repo's config on their own, unless
    the user turned on mise's paranoid mode.
    """
    install()

    try:
        proc.run((mise_path, "install"), cwd=reporoot)
        if _has_task(reporoot, "sync"):
            proc.run((mise_path, "run", "sync"), cwd=reporoot)
    except RuntimeError as e:
        print(e)
        return 1
    return 0
