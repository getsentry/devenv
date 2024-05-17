from __future__ import annotations

import os
import sys

from devenv.constants import CI
from devenv.constants import root
from devenv.lib import archive


# Forces download of the python interpreter even if the system interpreter is
# compatible with the requested version. By default, devenv uses system python
# on CI.
FORCE_PY = os.getenv("SENTRY_FORCE_PY", "").lower() in ("1", "true")


def _is_sys_compatible(version: str) -> bool:
    """Returns ``True`` if the current python interpreter is semver-compatible
    with the given version."""

    expected = tuple(int(i) for i in version.split("."))

    return (
        sys.version_info[:2] == expected[:2]
        and sys.version_info[2] >= expected[2]
    )


def get(python_version: str, url: str, sha256: str) -> str:
    unpack_into = f"{root}/pythons/{python_version}"

    if os.path.exists(f"{unpack_into}/python/bin/python3"):
        return f"{unpack_into}/python/bin/python3"

    if CI and not FORCE_PY and _is_sys_compatible(python_version):
        return sys.executable

    archive_file = archive.download(url, sha256)
    archive.unpack(archive_file, unpack_into)

    assert os.path.exists(f"{unpack_into}/python/bin/python3")
    return f"{unpack_into}/python/bin/python3"
