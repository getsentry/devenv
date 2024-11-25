from __future__ import annotations

import importlib.metadata
import os
import platform
import pwd
import typing

troubleshooting_help = """\
===============
Troubleshooting
===============

Problem? First try running `devenv doctor`.
If that doesn't help, then proceed:

Internal living doc (more up-to-date):
https://www.notion.so/sentry/devenv-troubleshooting-1448b10e4b5d8080ba04f452e33de48d

Public doc:
https://develop.sentry.dev/development-infrastructure/environment/#troubleshooting
"""

version = importlib.metadata.version("sentry_devenv")

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

# the *original* user's environment, readonly
user_environ: typing.Mapping[str, str] = os.environ.copy()

home = user_environ["HOME"] if CI else struct_passwd.pw_dir
root = f"{home}/.local/share/sentry-devenv"

homebrew_repo = "/opt/homebrew"
homebrew_bin = f"{homebrew_repo}/bin"
if INTEL_MAC:
    homebrew_repo = "/usr/local/Homebrew"
    homebrew_bin = "/usr/local/bin"
