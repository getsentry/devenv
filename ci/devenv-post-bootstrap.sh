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

#  ~/.local/share/sentry-devenv/bin/ nedes to be on path...
# we need to execute this via login shell

expected="${HOME}/.local/share/sentry-devenv/bin/direnv"
got=$(command -v direnv)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected direnv location ${got}, expected ${expected}"
    exit 1
fi

direnv allow

exit 0

expected="${HOME}/.devenv/bin/node"
got=$(command -v node)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node location ${got}, expected ${expected}"
    exit 1
fi

expected="${HOME}/.devenv/bin/yarn"
got=$(command -v yarn)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected yarn location ${got}, expected ${expected}"
    exit 1
fi

# devenv-bootstrap.sh overrides sentry devenv config.ini with this version
expected="v20.13.1"
# more rigorous check than node --version
got=$(node -e 'console.log(process.version);')
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node version ${got}, expected ${expected}"
    exit 1
fi

# devenv-bootstrap.sh overrides sentry devenv config.ini with this version
expected="1.22.22"
got=$(yarn --version)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected yarn version ${got}, expected ${expected}"
    exit 1
fi
