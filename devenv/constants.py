from __future__ import annotations

import os
import platform
import pwd
import typing

CI = os.getenv("CI")
SYSTEM = platform.system().lower()
MACHINE = platform.machine()
DARWIN = SYSTEM == "darwin"
INTEL_MAC = DARWIN and (MACHINE == "x86_64")
SHELL_UNSET = "(SHELL unset)"
DEBUG = os.getenv("SNTY_DEVENV_DEBUG", os.getenv("DEBUG", ""))
EXTERNAL_CONTRIBUTOR = os.getenv("SENTRY_EXTERNAL_CONTRIBUTOR", "")

# for matching to download urls in repo config
SYSTEM_MACHINE = f"{SYSTEM}_{MACHINE}"

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
bin_root = f"{root}/bin"
src_root = f"{root}/devenv"
pythons_root = f"{root}/pythons"

homebrew_repo = "/opt/homebrew"
homebrew_bin = f"{homebrew_repo}/bin"
if INTEL_MAC:
    homebrew_repo = "/usr/local/Homebrew"
    homebrew_bin = "/usr/local/bin"

VOLTA_HOME = f"{root}/volta"
