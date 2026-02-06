#!/bin/bash
exec </dev/null  # no interactive input
exec >&2  # helps keeps stdout/stderr outputs in order with each other
set -euxo pipefail

# we don't have permissions to clone getsentry which is a good thing
# eventually we should move this bootstrap testing over to getsentry repo
# in the meantime, mock it so that pip install -e has something to chew on
mkdir -p "$HOME/code/getsentry"
cat <<EOF > "$HOME/code/getsentry/pyproject.toml"
[project]
name = "getsentry-mock"
version = "0.0.0"
EOF

# devenv should ignore npm's prefix even if it's changed via config
cat <<EOF > "$HOME/.npmrc"
prefix = ${HOME}/.local/lib/nodejs
EOF

: PATH: "$PATH"

# doesn't functionally do anything, just exercises
devenv update

cd "$HOME"
# note: colima will be used and is necessary for a docker runtime on
#       macos GitHub runners
devenv bootstrap
devenv fetch sentry

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
export PATH="${HOME}/code/sentry/.devenv/bin:${HOME}/code/sentry/node_modules/.bin:${HOME}/.local/share/sentry-devenv/bin:${PATH}"
export VIRTUAL_ENV="${HOME}/code/sentry/.venv"

# overwrite sentry's devenv config and resync
# so we don't break when upstream config is updated
cat <<EOF > "devenv/config.ini"
[devenv]
minimum_version = 1.22.1

[node]
# upstream (https://nodejs.org/dist/) is not reliable enough
# ask someone in team-devinfra to upload for you
darwin_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v22.16.0-darwin-x64.tar.xz
darwin_x86_64_sha256 = 5c34638f2c0e3f3aaa7b3a94b58304765a169730da1896ebba8515ea4d987a9c
darwin_arm64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v22.16.0-darwin-arm64.tar.xz
darwin_arm64_sha256 = aaf7fc3c936f1b359bc312b63638e41f258689ac2303966ad932cda18c54ea00
linux_x86_64 = https://storage.googleapis.com/sentry-dev-infra-assets/node/node-v22.16.0-linux-x64.tar.xz
linux_x86_64_sha256 = f4cb75bb036f0d0eddf6b79d9596df1aaab9ddccd6a20bf489be5abe9467e84e
# used for autoupdate
version = v22.16.0
EOF

devenv sync

expected="${HOME}/code/sentry/.devenv/bin/node"
got=$(command -v node)
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node location ${got}, expected ${expected}"
    exit 1
fi

# devenv-bootstrap.sh overrides sentry devenv config.ini with this version
expected="v22.16.0"
# more rigorous check than node --version
got=$(node -e 'console.log(process.version);')
if [[ "$got" != "$expected" ]]; then
    echo "unexpected node version ${got}, expected ${expected}"
    exit 1
fi
