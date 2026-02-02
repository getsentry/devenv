from __future__ import annotations

import pytest

from devenv import constants
from devenv.lib.apt import dpkg_is_installed


pytestmark = pytest.mark.skipif(
    not constants.LINUX, reason="apt tests only run on Linux"
)


def test_dpkg_is_installed() -> None:
    assert dpkg_is_installed("bash") is True
    assert dpkg_is_installed("nonexistent-package-xyz-123") is False
