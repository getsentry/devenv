from __future__ import annotations

from collections.abc import Generator
from unittest import mock

import pytest

from devenv import constants
from devenv.lib import colima

# /proc/cpuinfo in colima 0.8.1's VM (Linux 6.8.0-50-generic) on an M4 Pro
M4_BUGGY_FEATURES = (
    "fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid "
    "asimdrdm jscvt fcma lrcpc dcpop sha3 asimddp sha512 asimdfhm dit uscat "
    "ilrcpc flagm sb paca pacg dcpodp sve2 flagm2 frint svei8mm svebf16 i8mm "
    "bf16 bti afp sme smei16i64 smef64f64 smei8i32 smef16f32 smeb16f32 "
    "smef32f32 sme2 smei16i32 smebi32i32"
)
# ... and after upgrading it to Linux 6.8.0-147-generic
M4_FIXED_FEATURES = (
    "fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid "
    "asimdrdm jscvt fcma lrcpc dcpop sha3 asimddp sha512 asimdfhm dit uscat "
    "ilrcpc flagm sb paca pacg dcpodp flagm2 frint i8mm bf16 bti afp"
)

BUGGY_KERNEL = "6.8.0-50-generic"
FIXED_KERNEL = "6.8.0-147-generic"

SYSCTL_SME = ("/usr/sbin/sysctl", "-n", "hw.optional.arm.FEAT_SME")
APT_UPDATE = ("colima", "ssh", "--", *colima._APT_GET, "update")
APT_INSTALL = (
    "colima",
    "ssh",
    "--",
    *colima._APT_GET,
    "install",
    "-y",
    "linux-image-virtual",
)


class FakeVM:
    """Answers the commands devenv runs on the host and in colima's VM."""

    def __init__(
        self,
        *,
        running: str = BUGGY_KERNEL,
        available: str = FIXED_KERNEL,
        buggy: frozenset[str] = frozenset((BUGGY_KERNEL,)),
        host_sme: bool = True,
        apt_works: bool = True,
        boots_newest: bool = True,
    ) -> None:
        self.running = running
        self.installed = {running}
        self.available = available
        self.buggy = buggy
        self.host_sme = host_sme
        self.apt_works = apt_works
        self.boots_newest = boots_newest
        self.cmds: list[tuple[str, ...]] = []
        self.restarts = 0

    def run(
        self,
        cmd: tuple[str, ...],
        *,
        pathprepend: str = "",
        stdout: bool = False,
    ) -> str | None:
        self.cmds.append(cmd)
        if cmd == SYSCTL_SME:
            if not self.host_sme:
                raise RuntimeError("sysctl: unknown oid")
            return "1"
        if cmd == ("colima", "stop"):
            return None
        if cmd in (APT_UPDATE, APT_INSTALL):
            if not self.apt_works:
                raise RuntimeError("Command `apt-get` failed! (code 100)")
            if cmd == APT_INSTALL:
                self.installed.add(self.available)
            return None

        assert cmd[:3] == ("colima", "ssh", "--"), cmd
        vm_cmd = cmd[3:]
        if vm_cmd == ("grep", "-m1", "^Features", "/proc/cpuinfo"):
            if self.running in self.buggy:
                return f"Features\t: {M4_BUGGY_FEATURES}"
            return f"Features\t: {M4_FIXED_FEATURES}"
        if vm_cmd == ("uname", "-r"):
            return self.running
        if vm_cmd == ("linux-version", "list"):
            return "\n".join(sorted(self.installed))
        if vm_cmd == ("sync",):
            return None
        raise AssertionError(f"unexpected command: {cmd}")

    def start(self, restart: bool) -> colima.ColimaStatus:
        """Stands in for colima._start, which is already covered elsewhere."""
        if restart:
            self.restarts += 1
            if self.boots_newest:
                self.running = max(
                    self.installed, key=colima._kernel_version_key
                )
        return colima.ColimaStatus.UP

    def ran(self, cmd: tuple[str, ...]) -> bool:
        return cmd in self.cmds


@pytest.fixture
def m4_mac() -> Generator[None]:
    with (
        mock.patch.object(constants, "DARWIN", True),
        mock.patch.object(constants, "MACHINE", "arm64"),
    ):
        yield


def _start(vm: FakeVM, restart: bool = False) -> colima.ColimaStatus:
    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
        mock.patch.object(colima, "_start", side_effect=vm.start),
    ):
        return colima.start(restart)


@pytest.mark.parametrize(
    ("features", "expected"),
    (
        # M4 and newer with an unfixed kernel
        (M4_BUGGY_FEATURES, True),
        (M4_FIXED_FEATURES, False),
        # e.g. AWS Graviton 3, which really has SVE
        ("fp asimd sve sve2 svei8mm svebf16 i8mm bf16", False),
        # M1-M3, no SVE or SME
        ("fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics", False),
    ),
)
def test_misreports_sve(features: str, expected: bool) -> None:
    assert colima._misreports_sve(features.split()) is expected


def test_kernel_version_key_sorts_abi_numerically() -> None:
    newest = max(
        ("6.8.0-50-generic", "6.8.0-147-generic", "6.8.0-64-generic"),
        key=colima._kernel_version_key,
    )
    assert newest == "6.8.0-147-generic"


@pytest.mark.parametrize(
    ("darwin", "machine"),
    ((False, "x86_64"), (False, "aarch64"), (True, "x86_64")),
)
def test_vm_isnt_probed_on_linux_or_intel_macs(
    darwin: bool, machine: str
) -> None:
    vm = FakeVM()
    with (
        mock.patch.object(constants, "DARWIN", darwin),
        mock.patch.object(constants, "MACHINE", machine),
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
    ):
        assert colima.vm_misreports_sve() is False
    assert vm.cmds == []


@pytest.mark.usefixtures("m4_mac")
def test_vm_isnt_probed_on_macs_without_sme() -> None:
    vm = FakeVM(host_sme=False)
    with mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run):
        assert colima.vm_misreports_sve() is False
    assert vm.cmds == [SYSCTL_SME]


@pytest.mark.usefixtures("m4_mac")
def test_start_leaves_a_fixed_vm_alone() -> None:
    vm = FakeVM(running=FIXED_KERNEL)

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.restarts == 0
    assert not vm.ran(APT_INSTALL)


@pytest.mark.usefixtures("m4_mac")
def test_start_upgrades_the_kernel_and_restarts_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM()

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.ran(APT_UPDATE)
    assert vm.ran(APT_INSTALL)
    # the new kernel has to be on disk before the vm is stopped
    assert vm.cmds.index(("colima", "ssh", "--", "sync")) < vm.cmds.index(
        ("colima", "stop")
    )
    assert vm.restarts == 1
    assert vm.running == FIXED_KERNEL
    assert f"colima's VM is now running Linux {FIXED_KERNEL}." in (
        capsys.readouterr().out
    )

    # and a second start has nothing left to do
    vm.cmds.clear()
    assert _start(vm) == colima.ColimaStatus.UP
    assert vm.restarts == 1
    assert not vm.ran(APT_INSTALL)


@pytest.mark.usefixtures("m4_mac")
def test_start_restarts_only_once_if_the_new_kernel_doesnt_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM(buggy=frozenset((BUGGY_KERNEL, FIXED_KERNEL)))

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.restarts == 1
    assert vm.cmds.count(APT_INSTALL) == 1
    assert "still misreports SVE support" in capsys.readouterr().out

    # the newest kernel's running, but there's nothing newer to upgrade to
    vm.cmds.clear()
    assert _start(vm) == colima.ColimaStatus.UP
    assert vm.restarts == 1
    assert f"no kernel newer than Linux {FIXED_KERNEL}" in (
        capsys.readouterr().out
    )


@pytest.mark.usefixtures("m4_mac")
def test_start_doesnt_keep_restarting_into_an_old_kernel(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # e.g. grub pinned to an older kernel
    vm = FakeVM(boots_newest=False)

    assert _start(vm) == colima.ColimaStatus.UP
    assert vm.restarts == 1
    assert vm.running == BUGGY_KERNEL
    assert "still misreports SVE support" in capsys.readouterr().out

    for _ in range(2):
        vm.cmds.clear()
        assert _start(vm) == colima.ColimaStatus.UP
        assert vm.restarts == 1
        assert not vm.ran(APT_INSTALL)
        assert "Run `devenv colima restart` to boot it" in (
            capsys.readouterr().out
        )


@pytest.mark.usefixtures("m4_mac")
def test_start_boots_an_installed_kernel_on_restart() -> None:
    # e.g. an earlier upgrade was interrupted before colima restarted
    vm = FakeVM()
    vm.installed.add(FIXED_KERNEL)

    assert _start(vm, restart=True) == colima.ColimaStatus.UP

    assert vm.running == FIXED_KERNEL
    assert vm.restarts == 1
    assert not vm.ran(APT_INSTALL)


@pytest.mark.usefixtures("m4_mac")
def test_start_carries_on_if_apt_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM(apt_works=False)

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.restarts == 0
    assert "failed to upgrade colima's VM kernel" in capsys.readouterr().out


@pytest.mark.usefixtures("m4_mac")
def test_start_carries_on_if_the_vm_cant_be_probed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def run(cmd: tuple[str, ...], **kwargs: object) -> str:
        if cmd == SYSCTL_SME:
            return "1"
        raise RuntimeError("Command `colima ssh` failed! (code 1)")

    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
        mock.patch.object(
            colima, "_start", return_value=colima.ColimaStatus.UP
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UP

    assert "failed to check colima's VM kernel" in capsys.readouterr().out


@pytest.mark.usefixtures("m4_mac")
def test_start_doesnt_probe_an_unhealthy_vm() -> None:
    vm = FakeVM()
    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
        mock.patch.object(
            colima, "_start", return_value=colima.ColimaStatus.UNHEALTHY
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UNHEALTHY

    assert vm.cmds == []


@pytest.mark.usefixtures("m4_mac")
def test_start_warns_if_colima_doesnt_come_back_after_the_upgrade(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM()
    statuses = iter((colima.ColimaStatus.UP, colima.ColimaStatus.UNHEALTHY))

    def start(restart: bool) -> colima.ColimaStatus:
        vm.start(restart)
        return next(statuses)

    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
        mock.patch.object(colima, "_start", side_effect=start),
    ):
        assert colima.start() == colima.ColimaStatus.UNHEALTHY

    assert "isn't healthy after restarting" in capsys.readouterr().out


def test_start_only_selects_colima_context_when_up() -> None:
    with (
        mock.patch(
            "devenv.lib.colima.check", return_value=colima.ColimaStatus.UP
        ),
        mock.patch("devenv.lib.colima.proc.run") as mock_run,
        mock.patch(
            "devenv.lib.colima._upgrade_kernel_if_sve_misreported",
            return_value=False,
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UP

    # no restart, but a previously interrupted start may have left docker
    # on the "default" context
    mock_run.assert_called_once_with(("docker", "context", "use", "colima"))


def test_start_switches_context_around_starting() -> None:
    with (
        mock.patch(
            "devenv.lib.colima.check",
            side_effect=[colima.ColimaStatus.DOWN, colima.ColimaStatus.UP],
        ),
        mock.patch("devenv.lib.colima.rosetta.ensure"),
        mock.patch("devenv.lib.colima.proc.run") as mock_run,
        mock.patch(
            "devenv.lib.colima._upgrade_kernel_if_sve_misreported",
            return_value=False,
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UP

    cmds = [c.args[0][:3] for c in mock_run.call_args_list]
    assert cmds == [
        ("docker", "context", "use"),
        ("colima", "stop", "-f"),
        ("colima", "start", "--verbose"),
        ("docker", "context", "use"),
    ]
    assert mock_run.call_args_list[0].args[0][3] == "default"
    assert mock_run.call_args_list[-1].args[0][3] == "colima"


def test_restart_when_up() -> None:
    with (
        mock.patch(
            "devenv.lib.colima.check",
            side_effect=[colima.ColimaStatus.UP, colima.ColimaStatus.UP],
        ),
        mock.patch("devenv.lib.colima.rosetta.ensure"),
        mock.patch("devenv.lib.colima.proc.run") as mock_run,
        mock.patch(
            "devenv.lib.colima._upgrade_kernel_if_sve_misreported",
            return_value=False,
        ),
    ):
        assert colima.restart() == colima.ColimaStatus.UP

    cmds = [c.args[0][:2] for c in mock_run.call_args_list]
    assert ("colima", "stop") in cmds
    assert ("colima", "start") in cmds
