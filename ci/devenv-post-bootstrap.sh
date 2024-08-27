#!/bin/bash
exec </dev/null  # no interactive input
exec >&2  # helps keeps stdout/stderr outputs in order with each other
set -euxo pipefail

# After bootstrap+fetch we tell people to open a new terminal,
# so the following emulates that.

if ! shopt -q login_shell; then
    # ~/.local/share/sentry-devenv/bin needs to be on PATH.
    echo "Needs to be a login shell."
    exit 1
fi

cd "$HOME/code/sentry"

# check that sentry's post_fetch ran
grep -Fxq 'ignorerevsfile = .git-blame-ignore-revs' .git/config

expected="${HOME}/.local/share/sentry-devenv/bin/direnv"
got=$(command -v direnv)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected direnv location ${got}, expected ${expected}"
    exit 1
fi

# XXX: direnv allow/reload weirdly just exits 0 in GHA after writing
# the allow file, and using delve (gdb for go binaries) with action-tmate
# is painful because you get logged out for no reason after a few minutes,
# strace also doesn't reveal anything obvious

# so instead, just do here the essentials that sentry's .envrc does
export PATH="${HOME}/code/sentry/.devenv/bin:${HOME}/.local/share/sentry-devenv/bin:${PATH}"
export VIRTUAL_ENV="${HOME}/code/sentry/.venv"
