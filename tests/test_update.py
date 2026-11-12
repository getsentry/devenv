from __future__ import annotations

import io
from unittest.mock import patch

from devenv import update


def test_reinstalls_when_python_pin_changes() -> None:
    script = b'SNTY_DEVENV_PY_VERSION="${SNTY_DEVENV_PY_VERSION:-3.13.18}"\n'
    with (
        patch("urllib.request.urlopen", return_value=io.BytesIO(script)),
        patch("devenv.update.proc.run", return_value="3.11.4\n") as run,
    ):
        assert update.reinstall_if_python_changed()
    assert run.call_args.args[0][0] == "bash"
