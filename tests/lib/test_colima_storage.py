from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from devenv import constants
from devenv.lib import colima
from devenv.lib import colima_config


@pytest.fixture(autouse=True)
def _default_lima_home() -> Iterator[None]:
    with mock.patch.dict(constants.user_environ, {"LIMA_HOME": ""}):
        yield


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
    assert policy.expected_snapshotter is True


def test_new_vm_persists_containerd_choice_in_existing_config(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    config_path = home / ".colima/default/colima.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "disk: 512\nruntime: docker\ndocker:\n  log-driver: local\n"
    )

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    run.assert_not_called()
    assert policy == colima._StoragePolicy(
        existing_instance=False, expected_snapshotter=True
    )
    assert "log-driver: local" in config_path.read_text()
    assert "containerd-snapshotter: true" in config_path.read_text()


@pytest.mark.parametrize("snapshotter", (True, False))
def test_new_vm_preserves_explicit_store_choice(
    tmp_path: Path, snapshotter: bool
) -> None:
    home = tmp_path / "home"
    config_path = home / ".colima/default/colima.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "disk: 512\nruntime: docker\ndocker:\n  features:\n"
        f"    containerd-snapshotter: {str(snapshotter).lower()}\n"
    )
    original = config_path.read_bytes()

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    run.assert_not_called()
    assert policy == colima._StoragePolicy(
        existing_instance=False, expected_snapshotter=snapshotter
    )
    assert config_path.read_bytes() == original


@pytest.mark.parametrize("snapshotter", (True, False))
def test_new_vm_preserves_explicit_template_store_choice(
    tmp_path: Path, snapshotter: bool
) -> None:
    home = tmp_path / "home"
    template_path = home / ".colima/_templates/default.yaml"
    template_path.parent.mkdir(parents=True)
    template_path.write_text(
        "runtime: docker\ndocker:\n  features:\n"
        f"    containerd-snapshotter: {str(snapshotter).lower()}\n"
    )
    original = template_path.read_bytes()

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    run.assert_not_called()
    assert policy == colima._StoragePolicy(
        existing_instance=False, expected_snapshotter=snapshotter
    )
    assert template_path.read_bytes() == original


def test_new_vm_rejects_storage_choice_colima_would_ignore(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    config_path = home / ".colima/default/colima.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "docker:\n  features:\n    containerd-snapshotter: false\n"
    )

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch("devenv.lib.colima.proc.run") as run,
        pytest.raises(colima_config.StorageMigrationBlocked, match="runtime"),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    run.assert_not_called()


def test_fresh_vm_containerd_store_survives_stop_and_start(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    root = tmp_path / "sentry-devenv"
    instance = home / ".colima/_lima/colima"
    config_path = home / ".colima/default/colima.yaml"
    statuses = iter(
        (
            colima.ColimaStatus.DOWN,
            colima.ColimaStatus.DOWN,
            colima.ColimaStatus.DOWN,
        )
    )
    starts: list[tuple[colima._StartMode, bool]] = []
    commands: list[tuple[str, ...]] = []

    def start_vm(
        mode: colima._StartMode,
        status: colima.ColimaStatus | None = None,
        *,
        existing_instance: bool = False,
    ) -> colima.ColimaStatus:
        starts.append((mode, existing_instance))
        if not instance.exists():
            instance.mkdir(parents=True)
            config_path.parent.mkdir(parents=True)
            config_path.write_text("disk: 512\nruntime: docker\ndocker: {}\n")
        return colima.ColimaStatus.UP

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        commands.append(command)
        return 'overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]'

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch.object(colima, "check", side_effect=lambda: next(statuses)),
        mock.patch.object(colima, "_start", side_effect=start_vm),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
    ):
        assert colima.start() == colima.ColimaStatus.UP
        first_config = config_path.read_bytes()
        assert "containerd-snapshotter: true" in first_config.decode()

        assert colima.stop() == colima.ColimaStatus.DOWN
        assert colima.start() == colima.ColimaStatus.UP

    assert starts == [
        (colima._StartMode.ENSURE_RUNNING, False),
        (colima._StartMode.ENSURE_RUNNING, True),
    ]
    assert sum(command[0] == "docker" for command in commands) == 2
    assert ("colima", "stop") in commands
    assert config_path.read_bytes() == first_config


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
    assert policy.expected_snapshotter is snapshotter
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


def test_stopped_legacy_vm_ignores_standalone_lima_disk(tmp_path: Path) -> None:
    home, config_path = _profile(tmp_path)
    standalone_disk = home / ".lima/_disks/colima"
    standalone_disk.mkdir(parents=True)
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    probe_environments: list[object | None] = []

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        if command[0].endswith("limactl"):
            env = kwargs.get("env")
            probe_environments.append(env if isinstance(env, dict) else None)
            lima_home = (
                env.get("LIMA_HOME", f"{home}/.lima")
                if isinstance(env, dict)
                else f"{home}/.lima"
            )
            return '{"name":"colima"}' if lima_home == f"{home}/.lima" else ""
        raise AssertionError(command)

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    assert policy.expected_snapshotter is False
    assert "containerd-snapshotter: false" in config_path.read_text()
    assert probe_environments == [{"LIMA_HOME": f"{home}/.colima/_lima"}]


def test_stopped_modern_vm_disk_prevents_overlay2_override(
    tmp_path: Path,
) -> None:
    home, config_path = _profile(tmp_path)
    original = config_path.read_bytes()
    modern_disk = home / ".colima/_lima/_disks/colima"
    modern_disk.parent.mkdir(parents=True)
    modern_disk.touch()
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    probe_environments: list[object | None] = []

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        if command[0].endswith("limactl"):
            env = kwargs.get("env")
            probe_environments.append(env if isinstance(env, dict) else None)
            lima_home = (
                env.get("LIMA_HOME", f"{home}/.lima")
                if isinstance(env, dict)
                else f"{home}/.lima"
            )
            return (
                '{"name":"colima"}'
                if lima_home == f"{home}/.colima/_lima"
                else ""
            )
        raise AssertionError(command)

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
        pytest.raises(colima_config.StorageMigrationBlocked),
    ):
        colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    assert config_path.read_bytes() == original
    assert probe_environments == [{"LIMA_HOME": f"{home}/.colima/_lima"}]


def test_explicit_lima_home_is_used_for_colima_instance_and_disk_probe(
    tmp_path: Path,
) -> None:
    home, config_path = _profile(tmp_path)
    default_instance = home / ".colima/_lima/colima"
    default_instance.rmdir()
    explicit_lima_home = tmp_path / "custom-lima-home"
    (explicit_lima_home / "colima").mkdir(parents=True)
    root = tmp_path / "sentry-devenv"
    limactl = root / "bin/limactl"
    limactl.parent.mkdir(parents=True)
    limactl.touch()
    probe_environments: list[object | None] = []

    def run(command: tuple[str, ...], **kwargs: object) -> str:
        if command[0].endswith("limactl"):
            env = kwargs.get("env")
            probe_environments.append(env if isinstance(env, dict) else None)
            return ""
        raise AssertionError(command)

    with (
        mock.patch.dict(
            constants.user_environ, {"LIMA_HOME": str(explicit_lima_home)}
        ),
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(root)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
    ):
        policy = colima._prepare_docker_store(colima.ColimaStatus.DOWN)

    assert policy.expected_snapshotter is False
    assert "containerd-snapshotter: false" in config_path.read_text()
    assert probe_environments == [{"LIMA_HOME": str(explicit_lima_home)}]


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


def test_saved_overlay2_choice_is_verified_after_restart(
    tmp_path: Path,
) -> None:
    config = (
        "disk: 512\nruntime: docker\ndocker:\n  features:\n"
        "    containerd-snapshotter: false\n"
    )
    config_path, _, result = _prepare(
        tmp_path, colima.ColimaStatus.DOWN, config
    )

    assert result.policy.expected_snapshotter is False
    with mock.patch(
        "devenv.lib.colima.proc.run", return_value="overlay2|[]"
    ) as run:
        assert (
            colima._verify_storage_after_start(
                colima.ColimaStatus.UP, result.policy, vm_was_started=True
            )
            == colima.ColimaStatus.UP
        )

    assert "containerd-snapshotter: false" in config_path.read_text()
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
