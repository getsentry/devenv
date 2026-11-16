from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from devenv import update

UV_PYTHON_MISMATCH = """\
Command `uv pip install` failed! (code 1)
combined out:
error: No solution found when resolving dependencies
  cause: Because the current Python version (3.11.4) does not satisfy Python>=3.13 and sentry-devenv==1.40.0 depends on Python>=3.13, we can conclude that sentry-devenv==1.40.0 cannot be used.
         And because only sentry-devenv==1.40.0 is available and you require sentry-devenv==1.40.0, we can conclude that your requirements are unsatisfiable.
"""


def test_reinstalls_when_python_pin_changes() -> None:
    script = b'SNTY_DEVENV_PY_VERSION="${SNTY_DEVENV_PY_VERSION:-3.13.18}"\n'
    with (
        patch("urllib.request.urlopen", return_value=io.BytesIO(script)),
        patch("devenv.update.proc.run", return_value="3.11.4\n") as run,
    ):
        assert update.reinstall_if_python_changed()
    assert run.call_args.args[0][0] == "bash"


def test_versioned_update_reinstalls_before_installing() -> None:
    with (
        patch(
            "devenv.update.reinstall_if_python_changed", return_value=True
        ) as reinstall,
        patch("devenv.update.install_sentry_devenv") as install,
    ):
        assert update.upgrade_global_devenv("1.40.0")
    reinstall.assert_called_once_with()
    install.assert_called_once_with("1.40.0")


def test_unversioned_reinstall_skips_package_install() -> None:
    with (
        patch("devenv.update.reinstall_if_python_changed", return_value=True),
        patch("devenv.update.install_sentry_devenv") as install,
    ):
        assert not update.upgrade_global_devenv(None)
    install.assert_not_called()


def test_install_reports_python_mismatch() -> None:
    with (
        patch("devenv.update.uv.find", return_value="uv"),
        patch(
            "devenv.update.proc.run",
            side_effect=[RuntimeError(UV_PYTHON_MISMATCH), "3.11.4"],
        ),
        pytest.raises(SystemExit, match="install-devenv.sh") as raised,
    ):
        update.install_sentry_devenv("1.40.0")
    message = str(raised.value)
    assert "does not satisfy Python>=3.13" in message
    assert "newer Python than Python 3.11.4" in message


def test_install_reraises_other_failures() -> None:
    with (
        patch("devenv.update.uv.find", return_value="uv"),
        patch(
            "devenv.update.proc.run", side_effect=RuntimeError("network down")
        ),
        pytest.raises(RuntimeError, match="network down"),
    ):
        update.install_sentry_devenv(None)
