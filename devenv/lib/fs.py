from __future__ import annotations

import os
import shlex
import subprocess
from typing import Optional

from devenv.constants import home
from devenv.constants import shell
from devenv.lib import proc


def zdotdir() -> str:
    # Note that we can't simply check os.environ; the most common way of setting
    # this value, via ~/.zshenv, results in a shell variable, not an env var.
    return subprocess.run(
        [shell, "-c", "echo $ZDOTDIR"], text=True, capture_output=True
    ).stdout.strip()


def shellrc() -> str:
    if shell == "zsh":
        # The user's .zshrc may not be in ~/ if they set ZDOTDIR. See man zsh(1)
        # for more details.
        dotfile = f"{home}/.zshrc"
        if not os.path.isfile(dotfile):
            dotdir = zdotdir()
            if dotdir != "":
                dotfile = f"{dotdir}/.zshrc"
        return dotfile
    if shell == "bash":
        return f"{home}/.bashrc"
    if shell == "fish":
        return f"{home}/.config/fish/config.fish"
    raise NotImplementedError(f"unsupported shell: {shell}")


def gitroot(cd: str = "") -> str:
    from os.path import normpath, join

    if not cd:
        cd = os.getcwd()

    stdout = proc.run(
        ("git", "-C", cd, "rev-parse", "--show-cdup"), stdout=True
    )
    return normpath(join(cd, stdout))


def idempotent_add(filepath: str, text: str) -> None:
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(f"\n{text}\n")
            return
    with open(filepath, "r+") as f:
        contents = f.read()
        if text not in contents:
            f.write(f"\n{text}\n")


def write_script(
    filepath: str, text: str, shell_escape: Optional[dict[str, str]] = None
) -> None:
    if shell_escape:
        shell_escaped = {k: shlex.quote(v) for k, v in shell_escape.items()}
        text = text.format(**shell_escaped)
    with open(filepath, "w") as f:
        f.write(text)
    os.chmod(filepath, 0o775)


def ensure_binroot(reporoot: str) -> str:
    binroot = f"{reporoot}/.devenv/bin"
    os.makedirs(binroot, exist_ok=True)
    if not os.path.exists(f"{binroot}/.gitignore"):
        with open(f"{binroot}/.gitignore", "w") as f:
            f.write(
                """*
# automatically written by devenv ensure_binroot! feel free to modify.
"""
            )
    return binroot


def ensure_symlink(expected_src: str, dest: str) -> None:
    try:
        src = os.readlink(dest)
        if src != expected_src:
            print(f"WARNING: {dest} unexpectedly points to {src}")
            return
    except FileNotFoundError:
        os.symlink(expected_src, dest)
    except OSError as e:
        if e.errno == 22:
            print(f"WARNING: {dest} exists and isn't a symlink")
            return
