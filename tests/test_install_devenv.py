from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "install-devenv.sh"


def _run(
    tmp_path: Path, *, noninteractive: bool, stdin: str = ""
) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".zshrc").write_text("# existing\n")
    show_log = tmp_path / "show.log"
    probe = f"""
set -euo pipefail
source {shlex.quote(str(INSTALLER))}
constants
export HOME={shlex.quote(str(home))}
export XDG_CONFIG_HOME={shlex.quote(str(tmp_path / "xdg"))}
show() {{ printf '%s\\n' "$*" > {shlex.quote(str(show_log))}; }}
configure_shell "$HOME/devenv-bin"
"""
    env = os.environ.copy()
    env.pop("CI", None)
    env.pop("DEBUG", None)
    env.pop("SNTY_DEVENV_DEBUG", None)
    env["HOME"] = str(home)
    env["SHELL"] = "/bin/bash"
    if noninteractive:
        env["SNTY_DEVENV_NONINTERACTIVE"] = "1"
    else:
        env.pop("SNTY_DEVENV_NONINTERACTIVE", None)
    return subprocess.run(
        ["bash", "-c", probe],
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_noninteractive_skips_prompt_and_login_shell(tmp_path: Path) -> None:
    result = _run(tmp_path, noninteractive=True)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "show.log").exists()
    assert (tmp_path / "home" / ".zshrc").read_text() == "# existing\n"
    assert not (tmp_path / "xdg").exists()
    assert "Skipped shell startup edits" in result.stderr


def test_interactive_install_still_opens_a_login_shell(tmp_path: Path) -> None:
    result = _run(tmp_path, noninteractive=False, stdin="n\n")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "show.log").read_text().strip() == "/bin/bash -l"
    assert (tmp_path / "home" / ".zshrc").read_text() == "# existing\n"
    assert not (tmp_path / "xdg").exists()
