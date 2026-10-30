from __future__ import annotations

import json
import os
import pathlib
import shutil
import tarfile
from collections.abc import Generator
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from devenv.lib import archive
from devenv.lib import node
from devenv.lib.repository import Repository

version = "v0.0.0"
sha256 = "fakesha256"

# A stand-in for npm: the real one would `npm install -g pnpm@X` into
# $NPM_CONFIG_PREFIX, so this fake one does the same.
fake_npm = """#!/bin/sh
mkdir -p "$NPM_CONFIG_PREFIX/bin"
printf '#!/bin/sh\\necho %s\\n' "${3#pnpm@}" > "$NPM_CONFIG_PREFIX/bin/pnpm"
chmod +x "$NPM_CONFIG_PREFIX/bin/pnpm"
"""


def _write_executable(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, 0o755)


@pytest.fixture
def node_tarball(tmp_path: pathlib.Path) -> str:
    """A node release tarball with executables that actually run."""
    src = f"{tmp_path}/tarball-src/node-{version}-darwin-arm64"
    _write_executable(f"{src}/bin/node", f"#!/bin/sh\necho {version}\n")
    _write_executable(f"{src}/bin/npm", fake_npm)
    _write_executable(f"{src}/bin/npx", "#!/bin/sh\n")
    _write_executable(f"{src}/bin/corepack", "#!/bin/sh\n")

    path = f"{tmp_path}/node.tar.xz"
    with tarfile.open(path, "w:xz") as tarf:
        tarf.add(src, arcname=os.path.basename(src))
    return path


@pytest.fixture
def root(tmp_path: pathlib.Path) -> Generator[str, None, None]:
    root = f"{tmp_path}/root"
    with patch("devenv.lib.node.root", root):
        yield root


@pytest.fixture
def download(node_tarball: str) -> Generator[MagicMock, None, None]:
    def fake_download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(node_tarball, dest)
        return dest

    with patch(
        "devenv.lib.node.archive.download", side_effect=fake_download
    ) as mock:
        yield mock


def _checkout(tmp_path: pathlib.Path, name: str) -> str:
    reporoot = Repository(f"{tmp_path}/{name}").path
    os.makedirs(reporoot)
    with open(f"{reporoot}/package.json", "w") as f:
        json.dump({"packageManager": "pnpm@1.2.3"}, f)
    return reporoot


@pytest.mark.usefixtures("download")
def test_install_fresh(tmp_path: pathlib.Path, root: str) -> None:
    reporoot = _checkout(tmp_path, "repo")
    binroot = f"{reporoot}/.devenv/bin"

    node.install(version, "url", sha256, reporoot)

    shared = f"{root}/node/{sha256}"
    assert os.path.isfile(f"{shared}/bin/node")
    for name in ("node", "npm", "npx", "corepack"):
        assert (
            os.readlink(f"{binroot}/node-env/bin/{name}")
            == f"{shared}/bin/{name}"
        )
    # only the shared install is left in its parent, no temp dirs
    assert os.listdir(f"{root}/node") == [sha256]

    with open(f"{binroot}/npm", "r") as f:
        text = f.read()
        assert (
            text
            == f"""#!/bin/sh
export PATH={binroot}/node-env/bin:"${{PATH}}"
export NPM_CONFIG_PREFIX={binroot}/node-env
exec {binroot}/node-env/bin/npm "$@"
"""
        )

    assert node.installed(version, binroot)


def test_install_second_checkout_reuses_shared(
    tmp_path: pathlib.Path, root: str, download: MagicMock
) -> None:
    first = _checkout(tmp_path, "first")
    second = _checkout(tmp_path, "second")

    node.install(version, "url", sha256, first)
    node.install(version, "url", sha256, second)

    assert download.call_count == 1
    for reporoot in (first, second):
        binroot = f"{reporoot}/.devenv/bin"
        assert (
            os.readlink(f"{binroot}/node-env/bin/node")
            == f"{root}/node/{sha256}/bin/node"
        )
        assert node.installed(version, binroot)


@pytest.mark.usefixtures("download")
def test_install_replaces_per_checkout_install(
    tmp_path: pathlib.Path, root: str, capsys: pytest.CaptureFixture[str]
) -> None:
    reporoot = _checkout(tmp_path, "repo")
    binroot = f"{reporoot}/.devenv/bin"

    # what older devenvs installed: a full copy of node in the checkout,
    # with the same shims and pnpm installed into it
    _write_executable(
        f"{binroot}/node-env/bin/node", f"#!/bin/sh\necho {version}\n"
    )
    _write_executable(f"{binroot}/node-env/lib/node_modules/npm/x", "")
    _write_executable(f"{binroot}/node-env/bin/pnpm", "#!/bin/sh\n")
    _write_executable(
        f"{binroot}/node",
        f"""#!/bin/sh
exec {binroot}/node-env/bin/node "$@"
""",
    )

    assert not node.installed(version, binroot)
    assert "per-checkout node detected" in capsys.readouterr().out

    node.install(version, "url", sha256, reporoot)

    assert os.path.islink(f"{binroot}/node-env/bin/node")
    assert not os.path.exists(f"{binroot}/node-env/lib/node_modules/npm")
    assert not os.path.exists(f"{binroot}/node-env/bin/pnpm")
    assert node.installed(version, binroot)


@pytest.mark.usefixtures("download")
def test_installed_shared_install_removed(
    tmp_path: pathlib.Path, root: str
) -> None:
    reporoot = _checkout(tmp_path, "repo")
    binroot = f"{reporoot}/.devenv/bin"
    node.install(version, "url", sha256, reporoot)

    shutil.rmtree(f"{root}/node/{sha256}")

    assert not node.installed(version, binroot)
    node.install(version, "url", sha256, reporoot)
    assert node.installed(version, binroot)


def test_installed_volta(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    binroot = f"{tmp_path}/.devenv/bin"
    _write_executable(f"{binroot}/node-env/bin/node", "")
    _write_executable(
        f"{binroot}/node",
        """#!/bin/sh
export VOLTA_HOME=whatever
""",
    )

    assert not node.installed(version, binroot)
    assert "volta-based node detected" in capsys.readouterr().out


def test_install_concurrent(
    tmp_path: pathlib.Path, root: str, download: MagicMock
) -> None:
    unpack = archive.unpack

    def unpack_then_lose_race(*args: object, **kwargs: object) -> None:
        unpack(*args, **kwargs)  # type: ignore[arg-type]
        # another checkout's sync finishes installing first
        _write_executable(f"{root}/node/{sha256}/bin/node", "winner")

    with patch(
        "devenv.lib.node.archive.unpack", side_effect=unpack_then_lose_race
    ):
        shared = node._install("url", sha256, f"{root}/node")

    assert shared == f"{root}/node/{sha256}"
    with open(f"{shared}/bin/node") as f:
        assert f.read() == "winner"
    assert os.listdir(f"{root}/node") == [sha256]


@pytest.mark.usefixtures("download")
def test_install_pnpm(tmp_path: pathlib.Path, root: str) -> None:
    reporoot = _checkout(tmp_path, "repo")
    binroot = f"{reporoot}/.devenv/bin"

    node.install(version, "url", sha256, reporoot)
    node.install_pnpm(reporoot)

    # pnpm goes into the checkout's npm prefix, never the shared install
    assert os.path.isfile(f"{binroot}/node-env/bin/pnpm")
    assert not os.path.exists(f"{root}/node/{sha256}/bin/pnpm")
    assert node.installed_pnpm("1.2.3", binroot)
