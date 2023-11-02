from __future__ import annotations

import os
import platform
import pwd
import sys
import typing

CI = os.getenv("CI")
DARWIN = sys.platform == "darwin"
MACHINE = platform.machine()
INTEL_MAC = DARWIN and (MACHINE == "x86_64")
SHELL_UNSET = "(SHELL unset)"
DEBUG = os.getenv("SNTY_DEVENV_DEBUG", os.getenv("DEBUG", ""))

struct_passwd = pwd.getpwuid(os.getuid())
shell_path = os.getenv("SHELL", struct_passwd.pw_shell)
shell = shell_path.rsplit("/", 1)[-1]
user = struct_passwd.pw_name
home = struct_passwd.pw_dir

# the *original* user's environment, readonly
user_environ: typing.Mapping[str, str] = os.environ.copy()

cache_root = f"{home}/.cache/sentry-devenv"
config_root = f"{home}/.config/sentry-devenv"
root = f"{home}/.local/share/sentry-devenv"
src_root = f"{root}/devenv"
pythons_root = f"{root}/pythons"
venv_root = f"{root}/virtualenvs"


if INTEL_MAC:
    homebrew_repo = "/usr/local/Homebrew"
    homebrew_bin = "/usr/local/bin"
else:  # FIXME: elif ARM_MAC
    homebrew_repo = "/opt/homebrew"
    homebrew_bin = f"{homebrew_repo}/bin"
# FIXME: elif linux: "/home/linuxbrew/.linuxbrew
# TODO: instead, symlink to /opt/homebrew in all cases, for consistency

VOLTA_HOME = f"{root}/volta"
