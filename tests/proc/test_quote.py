from __future__ import annotations

from devenv.lib.proc import quote


# Sanity check
def test_quote() -> None:
    cmd = ("ls", "-l", "/path/with spaces")
    expected = "ls -l '/path/with spaces'"
    assert quote(cmd) == expected
