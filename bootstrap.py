from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Sequence

from devenv.lib import fs
from devenv.lib import proc


help = "Bootstraps the development environment."

CI = os.environ.get("CI")


def check_github_ssh_access(git: str) -> bool:
    if CI:
        return True
    try:
        # The remote returns code 1 when successfully authenticated.
        proc.run(("ssh", "-T", "git@github.com"))
    except RuntimeError as e:
        # https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection
        if "You've successfully authenticated" not in f"{e}":
            return False
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            proc.run(
                (git, "-C", tmpdir, "clone", "--depth=1", "git@github.com:getsentry/private.git")
            )
            return True
    except RuntimeError as e:
        # Failing to clone private repos under getsentry
        # means that SSO isn't configured for the ssh key.
        print(f"{e}")
    return False


def add_github_to_known_hosts() -> None:
    # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
    fingerprints = """
github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=
github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=
"""  # noqa
    fs.idempotent_add(os.path.expanduser("~/.ssh/known_hosts"), fingerprints)


def generate_and_configure_ssh_keypair() -> str:
    fs.idempotent_add(
        os.path.expanduser("~/.ssh/config"),
        """Host github.com
  User git
  Hostname github.com
  PreferredAuthentications publickey
  IdentityFile ~/.ssh/sentry-github""",
    )
    private_key_path = os.path.expanduser("~/.ssh/sentry-github")
    if not os.path.exists(private_key_path):
        proc.run(
            (
                "ssh-keygen",
                "-t",
                "ed25519",
                "-a",
                "100",
                "-N",
                "",
                "-f",
                private_key_path,
            ),
            exit=True,
        )
    with open(f"{private_key_path}.pub") as f:
        return f.read().strip()


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
        xcode_git = proc.run(("/usr/bin/xcrun", "-f", "git"))
    except RuntimeError:
        print("Run xcode-select --install, then come back to bootstrap when done.")
        return 1

    add_github_to_known_hosts()

    if not check_github_ssh_access(xcode_git):
        pubkey = generate_and_configure_ssh_keypair()
        input(
            f"""
Failed to authenticate with an ssh key to GitHub.
We've generated and configured one for you at ~/.ssh/sentry-github.
Visit https://github.com/settings/ssh/new and add the following Authentication key:

{pubkey}

Then, you need to go to https://github.com/settings/keys, find your key,
and click Configure SSO, for the getsentry organization.

When done, hit ENTER to continue.
"""
        )
        while not check_github_ssh_access(xcode_git):
            input("Still failing to authenticate to GitHub. ENTER to retry, otherwise ^C to quit.")

    os.makedirs(coderoot, exist_ok=True)

    # https://github.blog/2020-12-21-get-up-to-speed-with-partial-clone-and-shallow-clone/
    if not os.path.exists(f"{coderoot}/sentry"):
        additional_flags = ("--depth", "1") if CI else ()
        proc.run_stream_output(
            (
                xcode_git,
                "-C",
                coderoot,
                "clone",
                "--filter=blob:none",
                *additional_flags,
                "git@github.com:getsentry/sentry",
            ),
            exit=True,
        )
    if not CI and not os.path.exists(f"{coderoot}/getsentry"):
        proc.run_stream_output(
            (
                xcode_git,
                "-C",
                coderoot,
                "clone",
                "--filter=blob:none",
                "git@github.com:getsentry/getsentry",
            ),
            exit=True,
        )

    # TODO: install brew and sentry's Brewfile

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
