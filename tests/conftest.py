from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    os.environ["CI"] = "1"
    os.environ["SHELL"] = "/bin/bash"
