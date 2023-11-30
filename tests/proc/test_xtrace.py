from __future__ import annotations

from pytest import CaptureFixture

from devenv.lib.proc import xtrace


# Sanity check
def test_xtrace(capfd: CaptureFixture[str]) -> None:
    cmd = ("echo", "Hello, World!")
    expected_output = "+ \x1b[36m$\x1b[m \x1b[1mecho 'Hello, World!'\x1b[m\n"
    xtrace(cmd)
    captured = capfd.readouterr()
    assert captured.out == expected_output
