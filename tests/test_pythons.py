from __future__ import annotations

from unittest.mock import patch

from devenv import pythons
from devenv.constants import root


def test_get() -> None:
    with patch("devenv.lib.archive.download"), patch(
        "devenv.lib.archive.unpack"
    ), patch("os.path.exists", side_effect=[False, True]):
        path = pythons.get("3.12.0", "foo", "bar")
        assert path == f"{root}/pythons/3.12.0/python/bin/python3"
