from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from devenv.lib import colima_config


def _write_config(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.mark.parametrize("snapshotter", (True, False))
def test_explicit_snapshotter_choice_is_preserved(
    tmp_path: Path, snapshotter: bool
) -> None:
    config_path = tmp_path / "colima.yaml"
    value = str(snapshotter).lower()
    _write_config(
        config_path,
        f"docker:\n  features:\n    buildkit: false\n    "
        f"containerd-snapshotter: {value}\n",
    )
    original = config_path.read_bytes()

    parsed = colima_config.read(str(config_path))

    assert parsed.snapshotter is snapshotter
    assert (
        colima_config.set_snapshotter(str(config_path), not snapshotter)
        is False
    )
    assert config_path.read_bytes() == original


def test_adds_legacy_setting_without_rewriting_custom_docker_fields(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "colima.yaml"
    original = (
        "disk: 512\n"
        "runtime: docker\n"
        "mountInotify: true\n"
        "docker:\n"
        "  insecure-registries:\n"
        "    - registry.example.com\n"
        "  features:\n"
        "    buildkit: false\n"
        "network:\n"
        "  dns: [8.8.8.8]\n"
    )
    _write_config(config_path, original)

    assert colima_config.set_snapshotter(str(config_path), False) is True

    updated = config_path.read_text()
    assert "insecure-registries:\n    - registry.example.com" in updated
    assert "buildkit: false" in updated
    assert "containerd-snapshotter: false" in updated
    assert "dns: [8.8.8.8]" in updated
    assert "mountInotify: true" in updated
    assert colima_config.set_snapshotter(str(config_path), False) is False


@pytest.mark.parametrize(
    ("docker", "expected"),
    (
        ("docker: {}\n", "docker:\n  features:\n"),
        ("docker:\n  log-level: warn\n", "  log-level: warn\n  features:\n"),
        ("runtime: docker\n", "docker:\n  features:\n"),
    ),
)
def test_adds_feature_mapping_to_common_generated_shapes(
    tmp_path: Path, docker: str, expected: str
) -> None:
    config_path = tmp_path / "colima.yaml"
    _write_config(config_path, docker)

    colima_config.set_snapshotter(str(config_path), False)

    updated = config_path.read_text()
    assert expected in updated
    assert "buildkit: true" in updated
    assert "containerd-snapshotter: false" in updated


@pytest.mark.parametrize("text", ("docker:", "docker:\n  features:"))
def test_adds_feature_mapping_when_file_has_no_final_newline(
    tmp_path: Path, text: str
) -> None:
    config_path = tmp_path / "colima.yaml"
    _write_config(config_path, text)

    colima_config.set_snapshotter(str(config_path), False)

    updated = config_path.read_text()
    assert "docker:\n" in updated
    assert "  features:\n" in updated
    assert "    containerd-snapshotter: false\n" in updated


@pytest.mark.parametrize(
    "text",
    (
        "docker:\n  features: {buildkit: true}\n",
        "docker:\n  features:\n    containerd-snapshotter: maybe\n",
        "docker:\n  features:\n    buildkit: true\n    buildkit: false\n",
        'docker:\n  features:\n    "containerd-snapshotter": true\n',
        "docker:\n  features:\n      containerd-snapshotter: false\n",
        "docker : {}\n",
        "\ufeffdocker: {}\n",
        "{docker: {}}\n",
        "---\ndocker: {}\n",
        "docker: null\n",
        "docker:\n  features:\n\tbuildkit: true\n",
    ),
)
def test_unsupported_config_is_not_rewritten(tmp_path: Path, text: str) -> None:
    config_path = tmp_path / "colima.yaml"
    _write_config(config_path, text)
    original = config_path.read_bytes()

    with pytest.raises(colima_config.StorageMigrationBlocked):
        colima_config.set_snapshotter(str(config_path), False)

    assert config_path.read_bytes() == original


def test_config_symlink_is_not_replaced(tmp_path: Path) -> None:
    target = tmp_path / "source.yaml"
    link = tmp_path / "colima.yaml"
    _write_config(target, "docker: {}\n")
    link.symlink_to(target)

    with pytest.raises(colima_config.StorageMigrationBlocked):
        colima_config.set_snapshotter(str(link), False)

    assert link.is_symlink()
    assert target.read_text() == "docker: {}\n"


def test_non_regular_config_is_not_read(tmp_path: Path) -> None:
    config_path = tmp_path / "colima.yaml"
    os.mkfifo(config_path)

    with pytest.raises(
        colima_config.StorageMigrationBlocked, match="not a regular file"
    ):
        colima_config.set_snapshotter(str(config_path), False)


def test_atomic_write_preserves_mode_and_original_on_replace_failure(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "colima.yaml"
    original = "docker: {}\n"
    _write_config(config_path, original)
    config_path.chmod(0o640)

    with mock.patch(
        "devenv.lib.colima_config.os.replace",
        side_effect=OSError("rename failed"),
    ):
        with pytest.raises(colima_config.StorageMigrationBlocked):
            colima_config.set_snapshotter(str(config_path), False)

    assert config_path.read_text() == original
    assert os.stat(config_path).st_mode & 0o777 == 0o640
    assert list(tmp_path.iterdir()) == [config_path]


def test_atomic_write_preserves_mode_on_success(tmp_path: Path) -> None:
    config_path = tmp_path / "colima.yaml"
    _write_config(config_path, "docker: {}\n")
    config_path.chmod(0o640)

    colima_config.set_snapshotter(str(config_path), False)

    assert os.stat(config_path).st_mode & 0o777 == 0o640
