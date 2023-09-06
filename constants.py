from __future__ import annotations

import os

cache_root = os.path.expanduser("~/.cache/sentry-devenv")
root = os.path.expanduser("~/.local/share/sentry-devenv")
src_root = f"{root}/devenv"
pythons_root = f"{root}/pythons"
venv_root = f"{root}/virtualenvs"
