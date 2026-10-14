from __future__ import annotations

import sys
from unittest.mock import patch

from devenv import pythons
from devenv.constants import root


def test_get() -> None:
    with (
        patch("devenv.lib.archive.download"),
        patch("devenv.lib.archive.unpack"),
        patch("os.path.exists", side_effect=[False, True]),
    ):
        path = pythons.get("3.12.0", "foo", "bar")
        assert path == f"{root}/pythons/3.12.0/python/bin/python3"


def test_get_system() -> None:
    v = sys.version_info
    python_version = f"{v.major}.{v.minor}.{max(v.micro - 1, 0)}"

    with patch("devenv.pythons.FORCE_PY", False):
        path = pythons.get(python_version, "foo", "bar")
        assert path == sys.executable
