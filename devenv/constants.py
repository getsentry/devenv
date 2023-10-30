from __future__ import annotations

import os
import platform
import sys

CI = os.environ.get("CI")
DARWIN = sys.platform == "darwin"
MACHINE = platform.machine()
INTEL_MAC = DARWIN and (MACHINE == "x86_64")
SHELL_UNSET = "(SHELL unset)"

home = os.path.expanduser("~")
cache_root = f"{home}/.cache/sentry-devenv"
config_root = f"{home}/.config/sentry-devenv"
root = f"{home}/.local/share/sentry-devenv"
src_root = f"{root}/devenv"
pythons_root = f"{root}/pythons"
venv_root = f"{root}/virtualenvs"
shell_path = os.environ.get("SHELL", SHELL_UNSET)
shell = shell_path.rsplit("/", 1)[-1]


if INTEL_MAC:
    homebrew_repo = "/usr/local/Homebrew"
    homebrew_bin = "/usr/local/bin"
else:  # FIXME: elif ARM_MAC
    homebrew_repo = "/opt/homebrew"
    homebrew_bin = f"{homebrew_repo}/bin"
# FIXME: elif linux: "/home/linuxbrew/.linuxbrew
# TODO: instead, symlink to /opt/homebrew in all cases, for consistency

VOLTA_HOME = f"{root}/volta"
