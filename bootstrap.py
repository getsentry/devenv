from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from devenv.lib import proc


help = "Bootstraps the development environment."


def check_github_ssh_access() -> bool:
    try:
        # The remote returns code 1 when successfully authenticated.
        proc.run(("ssh", "-T", "git@github.com"), exit=False)
    except RuntimeError as e:
        # https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection
        if "You've successfully authenticated" in f"{e}":
            return True
        print(f"{e}")
    return False


def add_github_to_known_hosts() -> None:
    fp = os.path.expanduser("~/.ssh/known_hosts")
    # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
    fingerprints = """
github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=
github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=
"""
    if not os.path.exists(fp):
        with open(fp, "w") as f:
            f.write(fingerprints)
            return
    with open(fp, "r+") as f:
        contents = f.read()
        if "AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" not in contents:
            f.write(fingerprints)


def main(coderoot: str, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=help)
    parser.add_argument("repo", type=str, nargs="?", default="sentry")
    args = parser.parse_args(argv)

    # xcode-select --install will take a while,
    # and involves elevated permissions with a GUI,
    # so best to just let the user go through that separately then retrying,
    # rather than waiting for it.
    # There is a way to perform a headless install but it's more complex
    # (refer to how homebrew does it).
    try:
        xcode_git = proc.run(("/usr/bin/xcrun", "-f", "git"), exit=False)
    except RuntimeError:
        print("Run xcode-select --install, then come back to bootstrap when done.")
        return 1

    add_github_to_known_hosts()

    if not check_github_ssh_access():
        print("Failed to authenticate with an ssh key to GitHub.")

    # TODO: setup github access

    # TODO: make coderoot and clone sentry and getsentry

    # TODO: install brew and Brewfile

    # TODO: install volta and direnv

    if args.repo == "getsentry":
        # Setting up sentry means we're setting up both repos.
        args.repo = "sentry"

    if args.repo not in {
        "sentry",
    }:
        print(f"repo {args.repo} not supported yet!")
        return 1

    return 0
