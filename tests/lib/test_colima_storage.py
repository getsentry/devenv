from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pytest

from devenv.lib import colima
from devenv.lib import colima_config


def _profile(
    tmp_path: Path, config: str = "disk: 512\nruntime: docker\ndocker: {}\n"
) -> tuple[Path, Path]:
    home = tmp_path / "home"
    instance = home / ".colima/_lima/colima"
    instance.mkdir(parents=True)
    config_path = home / ".colima/default/colima.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config)
    return home, config_path


def _prepare(
    tmp_path: Path,
    status: colima.ColimaStatus,
    config: str = "disk: 512\nruntime: docker\ndocker: {}\n",
    *,
    disk: str = "",
    store: str | None = None,
    docker_info: str = "",
    docker_error: str | None = None,
) -> tuple[Path, Path, mock.Mock]:
    home, config_path = _profile(tmp_path, config)
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    store_path = home / ".colima/_store/colima.json"
    if store is not None:
        store_path.parent.mkdir(parents=True)
        store_path.write_text(store)

    commands: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        commands.append(command)
        if command[0] == "docker":
            if docker_error:
                raise RuntimeError(docker_error)
            return docker_info
        if command[0].endswith("limactl"):
            return disk
        raise AssertionError(command)

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
    ):
        existing = colima._prepare_docker_store(status)

    return (
        config_path,
        store_path,
        mock.Mock(policy=existing, commands=commands),
    )


def test_missing_vm_does_not_add_legacy_override(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".colima/default").mkdir(parents=True)
    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)
    run.assert_not_called()
    assert policy.existing_instance is False
    assert policy.expected_snapshotter is None


@pytest.mark.parametrize("instance_kind", ("symlink", "file"))
def test_unexpected_instance_path_blocks_migration(
    tmp_path: Path, instance_kind: str
) -> None:
    home = tmp_path / "home"
    instance = home / ".colima/_lima/colima"
    instance.parent.mkdir(parents=True)
    if instance_kind == "symlink":
        target = tmp_path / "independent-vm"
        target.mkdir()
        instance.symlink_to(target)
    else:
        instance.write_text("not a VM directory")

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    run.assert_not_called()


@pytest.mark.parametrize("snapshotter", (True, False))
def test_explicit_user_store_choice_is_not_overwritten(
    tmp_path: Path, snapshotter: bool
) -> None:
    config_path = (
        "disk: 512\nruntime: docker\ndocker:\n  features:\n"
        f"    containerd-snapshotter: {str(snapshotter).lower()}\n"
    )
    home, path = _profile(tmp_path, config_path)
    original = path.read_bytes()
    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)
    run.assert_not_called()
    assert policy.existing_instance is True
    assert policy.expected_snapshotter is None
    assert path.read_bytes() == original


def test_stopped_legacy_vm_sets_overlay2_before_start(tmp_path: Path) -> None:
    config_path, store_path, result = _prepare(
        tmp_path, colima.ColimaStatus.DOWN
    )

    assert result.policy.existing_instance is True
    assert result.policy.expected_snapshotter is False
    assert "containerd-snapshotter: false" in config_path.read_text()
    assert not store_path.exists()
    assert result.commands == [
        (
            str(tmp_path / "sentry-devenv/bin/limactl"),
            "disk",
            "list",
            "--json",
            "colima",
        )
    ]


def test_legacy_upgrade_keeps_docker_objects_visible(tmp_path: Path) -> None:
    config_path, _, _ = _prepare(tmp_path, colima.ColimaStatus.DOWN)
    config = colima_config.read(str(config_path))
    snapshotter = config.snapshotter
    if snapshotter is None:
        snapshotter = True

    @dataclass
    class DockerStore:
        images: dict[str, tuple[str, ...]]
        containers: dict[str, tuple[str, str]]
        volumes: dict[str, bytes]

    stores = {
        "overlay2": DockerStore(
            images={"sha256:image-1": ("service:latest",)},
            containers={"container-1": ("service", "running")},
            volumes={"database": b"sentinel database contents"},
        ),
        "containerd": DockerStore(images={}, containers={}, volumes={}),
    }
    selected_store = "containerd" if snapshotter else "overlay2"
    visible = stores[selected_store]

    assert selected_store == "overlay2"
    assert visible.images == {"sha256:image-1": ("service:latest",)}
    assert visible.containers == {"container-1": ("service", "running")}
    assert visible.volumes == {"database": b"sentinel database contents"}


def test_running_overlay2_vm_is_probed_through_colima_context(
    tmp_path: Path,
) -> None:
    custom = (
        "disk: 512\nruntime: docker\ndocker:\n"
        "  log-driver: json-file\n  features:\n    buildkit: false\n"
    )
    config_path, _, result = _prepare(
        tmp_path, colima.ColimaStatus.UP, custom, docker_info="overlay2|[]"
    )

    assert "containerd-snapshotter: false" in config_path.read_text()
    assert result.policy.expected_snapshotter is False
    assert "log-driver: json-file" in config_path.read_text()
    assert "buildkit: false" in config_path.read_text()
    assert result.commands == [
        (
            "docker",
            "--context=colima",
            "info",
            "--format",
            "{{.Driver}}|{{json .DriverStatus}}",
        )
    ]


def test_unhealthy_legacy_vm_uses_positive_disk_evidence(
    tmp_path: Path,
) -> None:
    config_path, _, result = _prepare(
        tmp_path,
        colima.ColimaStatus.UNHEALTHY,
        docker_error="daemon unavailable",
    )

    assert "containerd-snapshotter: false" in config_path.read_text()
    assert result.policy.expected_snapshotter is False
    assert result.commands == [
        (
            "docker",
            "--context=colima",
            "info",
            "--format",
            "{{.Driver}}|{{json .DriverStatus}}",
        ),
        (
            str(tmp_path / "sentry-devenv/bin/limactl"),
            "disk",
            "list",
            "--json",
            "colima",
        ),
    ]


def test_unhealthy_vm_with_data_disk_blocks_without_backend_probe(
    tmp_path: Path,
) -> None:
    home, config_path = _profile(tmp_path)
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    original = config_path.read_bytes()

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        if command[0] == "docker":
            raise RuntimeError("daemon unavailable")
        return '{"name":"colima"}'

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.UNHEALTHY)

    assert config_path.read_bytes() == original


def test_running_containerd_vm_is_preserved(tmp_path: Path) -> None:
    config_path, _, _ = _prepare(
        tmp_path,
        colima.ColimaStatus.UP,
        docker_info='overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]',
    )

    assert "containerd-snapshotter: true" in config_path.read_text()


def test_running_overlay2_vm_with_empty_driver_status_is_preserved(
    tmp_path: Path,
) -> None:
    config_path, _, result = _prepare(
        tmp_path, colima.ColimaStatus.UP, docker_info="overlay2|null"
    )

    assert "containerd-snapshotter: false" in config_path.read_text()
    assert result.policy.expected_snapshotter is False


def test_started_migration_verifies_the_colima_docker_backend() -> None:
    policy = colima._StoragePolicy(
        existing_instance=True, expected_snapshotter=False
    )
    with mock.patch(
        "devenv.lib.colima.proc.run", return_value="overlay2|[]"
    ) as run:
        assert (
            colima._verify_storage_after_start(
                colima.ColimaStatus.UP, policy, vm_was_started=True
            )
            == colima.ColimaStatus.UP
        )

    assert run.call_args.args[0][:3] == ("docker", "--context=colima", "info")


def test_started_migration_blocks_if_colima_selected_another_backend(
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy = colima._StoragePolicy(
        existing_instance=True, expected_snapshotter=False
    )
    with mock.patch(
        "devenv.lib.colima.proc.run",
        return_value='overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]',
    ) as run:
        assert (
            colima._verify_storage_after_start(
                colima.ColimaStatus.UP, policy, vm_was_started=True
            )
            == colima.ColimaStatus.UNHEALTHY
        )

    assert run.call_args.args[0][:3] == ("docker", "--context=colima", "info")
    assert "Images and containers may be hidden" in capsys.readouterr().out


def test_healthy_start_skips_redundant_backend_probe() -> None:
    policy = colima._StoragePolicy(
        existing_instance=True, expected_snapshotter=False
    )
    with mock.patch("devenv.lib.colima.proc.run") as run:
        assert (
            colima._verify_storage_after_start(
                colima.ColimaStatus.UP, policy, vm_was_started=False
            )
            == colima.ColimaStatus.UP
        )
    run.assert_not_called()


@pytest.mark.parametrize(
    ("store", "disk", "config"),
    (
        (
            '{"disk_formatted":true,"disk_runtime":"docker"}',
            '{"name":"colima"}',
            "disk: 512\nruntime: docker\ndocker: {}\n",
        ),
        (
            '{"disk_formatted":false,"disk_runtime":""}',
            '{"name":"colima"}',
            "disk: 512\nruntime: docker\ndocker: {}\n",
        ),
        (
            '{"disk_formatted":false,"disk_runtime":""}',
            '{"name":""}',
            "disk: 512\nrootDisk: 20\nruntime: docker\ndocker: {}\n",
        ),
        (
            '{"disk_formatted":false,"disk_runtime":""}',
            '{"name":""}',
            "disk: 100\nruntime: docker\ndocker: {}\n",
        ),
    ),
)
def test_stopped_ambiguous_vm_blocks_without_rewriting(
    tmp_path: Path, store: str, disk: str, config: str
) -> None:
    home, config_path = _profile(tmp_path, config)
    store_path = home / ".colima/_store/colima.json"
    store_path.parent.mkdir(parents=True)
    store_path.write_text(store)
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    original = config_path.read_bytes()

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        return disk

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    assert config_path.read_bytes() == original


def test_corrupt_store_metadata_blocks_without_rewriting(
    tmp_path: Path,
) -> None:
    home, config_path = _profile(tmp_path)
    store_path = home / ".colima/_store/colima.json"
    store_path.parent.mkdir(parents=True)
    store_path.write_text("not json")
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    original = config_path.read_bytes()
    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.DOWN)
    assert config_path.read_bytes() == original


def test_failed_running_backend_probe_blocks_without_rewriting(
    tmp_path: Path,
) -> None:
    home, config_path = _profile(tmp_path)
    original = config_path.read_bytes()
    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch(
            "devenv.lib.colima.proc.run",
            side_effect=RuntimeError("daemon unavailable"),
        ),
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.UP)
    assert config_path.read_bytes() == original


def test_invalid_disk_json_blocks_without_rewriting(tmp_path: Path) -> None:
    home, config_path = _profile(tmp_path)
    original = config_path.read_bytes()
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", return_value="invalid"),
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.DOWN)
    assert config_path.read_bytes() == original
